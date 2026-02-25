from __future__ import annotations

import logging
from typing import Any, Optional, cast

import aiohttp
import async_timeout

from ..const import (
    DEFAULT_TIMEOUT,
    HW_G1_LED_IDS,
    LED_BLUE_INTERNAL_NAME,
    LED_INTENSITY_INTERNAL_NAME,
    LED_KELVIN_INTERNAL_NAME,
    LED_MANUAL_DURATION_INTERNAL_NAME,
    LED_MOON_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
    LEDS_CONV,
    LEDS_INTENSITY_COMPENSATION,
    VIRTUAL_LED,
)
from .api import ReefBeatAPI

_LOGGER = logging.getLogger(__name__)


def _interp(x: float, xs: list[float], ys: list[float]) -> float:
    """Piecewise-linear interpolation with clamping.

    Assumes xs is sorted ascending and len(xs) == len(ys) >= 2.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    for i in range(1, len(xs)):
        if x <= xs[i]:
            x0 = xs[i - 1]
            x1 = xs[i]
            y0 = ys[i - 1]
            y1 = ys[i]
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    return ys[-1]


def _make_interpolator(xs_in: list[float], ys_in: list[float]):
    """Build an interpolation callable from raw x/y lists."""
    pairs = sorted(zip(xs_in, ys_in), key=lambda p: p[0])
    xs = [float(x) for x, _y in pairs]
    ys = [float(y) for _x, y in pairs]

    def _f(x: Any) -> float:
        try:
            xf = float(x)
        except Exception:
            xf = xs[-1]
        return float(_interp(xf, xs, ys))

    return _f


# =============================================================================
# Classes
# =============================================================================


class ReefLedAPI(ReefBeatAPI):
    """ReefLED API wrapper (G1/G2, RSLED90 patch, kelvin/intensity conversion)."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
        hw: Any,
        intensity_compensation: bool = False,
    ) -> None:
        """Create a ReefLedAPI instance.

        Args:
            ip: Device IP/host.
            live_config_update: Whether the base API performs live config updates.
            hw: Hardware/model identifier reported by the device.
            intensity_compensation: Whether to apply model-specific intensity correction.

        Notes:
            - Some older firmwares require runtime source patching (RSLED90).
            - G1 devices report white/blue; kelvin/intensity are derived and cached.
        """
        super().__init__(ip, live_config_update, session)

        # patch for old RSLED
        self._rsled90_patch = False
        # /preset_name source behavior is determined at runtime
        self._preset_name_is_single = False

        self.data["local"] = {
            "use_cloud_api": None,
            "status": False,
            "manual_duration": 0,
            "moonphase": {"moon_day": 1},
            "manual_trick": {"kelvin": None, "intensity": None},
            "acclimation": {
                "duration": 50,
                "start_intensity_factor": 50,
                "current_day": 1,
            },
            "leds_conv": LEDS_CONV,
            "leds_intensity_compensation": LEDS_INTENSITY_COMPENSATION,
        }

        self._model = hw
        self._g1 = self._model in HW_G1_LED_IDS
        if self._model != VIRTUAL_LED:
            _LOGGER.info("G1 protocol: %s", self._g1)

        # Conversion callables (numpy.poly1d or similar); keep as Any to silence Pylance.
        self._kelvin_to_wb: Any | None = None
        self._wb_to_kelvin: Any | None = None

        # intensity compensation
        self._must_compensate_intensity = intensity_compensation
        _LOGGER.debug("Intensity compensation: %s", self._must_compensate_intensity)
        self._intensity_compensation: Any | None = None
        self._intensity_compensation_reference: float | None = None

    async def _probe_path(self, path: str) -> int:
        """Probe an endpoint and return its HTTP status code.

        Used to detect firmware/source variants at runtime.
        Returns 0 on any exception.
        """
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT):
                async with self._session.get(
                    self._base_url + path,
                    ssl=False,
                    allow_redirects=True,
                ) as resp:
                    return int(resp.status)
        except Exception:
            return 0

    async def _apply_runtime_source_patches(self) -> None:
        """Patch sources to match the detected firmware variant.

        - If `/dashboard` is missing, treat it as RSLED90 and use `/` for device-info.
        - If `/preset_name` exists as a single endpoint, use it; otherwise use per-day endpoints.
        Always ensures required sources for manual, acclimation, schedules, and clouds exist.
        """
        # RSLED90 patch: /dashboard not available -> use "/" as device-info
        dash_status = await self._probe_path("/dashboard")
        if dash_status != 200:
            self._rsled90_patch = True
            _LOGGER.info("USE patch version for RSLED90")
            self.remove_source("/dashboard")
            self.add_source("/", "device-info", "")

        # preset_name can be single endpoint or per-day endpoints
        preset_status = await self._probe_path("/preset_name")
        if preset_status == 200:
            self._preset_name_is_single = True
            self.add_source("/preset_name", "config", "")
        else:
            self._preset_name_is_single = False
            for day in range(1, 8):
                self.add_source(f"/preset_name/{day}", "config", "")

        # Additional required sources
        self.add_source("/manual", "data", "")
        self.add_source("/acclimation", "config", "")
        self.add_source("/moonphase", "config", "")
        for day in range(1, 8):
            self.add_source(f"/auto/{day}", "config", "")
            self.add_source(f"/clouds/{day}", "config", "")

    def update_acclimation(self) -> None:
        """Copy acclimation configuration into local state (best effort)."""
        accli = self.get_data(
            "$.sources[?(@.name=='/acclimation')].data", is_None_possible=True
        )
        if not isinstance(accli, dict):
            return
        for var in ("duration", "start_intensity_factor"):
            if var in accli:
                self.data["local"]["acclimation"][var] = accli[var]

    async def get_initial_data(self) -> dict[str, Any]:
        """Fetch initial device data and initialize conversion functions.

        After the initial fetch, computes conversion functions for:
        - kelvin -> white/blue ratio (wb)
        - wb -> kelvin
        And optionally an intensity compensation function, if enabled.
        """
        await self._apply_runtime_source_patches()
        data = await super().get_initial_data()

        def _as_str_any_dict(obj: Any) -> Optional[dict[str, Any]]:
            if isinstance(obj, dict):
                return cast(dict[str, Any], obj)
            return None

        def _find_model_params(table: Any) -> Optional[dict[str, Any]]:
            # Accept either list-of-dicts with {"name": ...} or dict keyed by model
            if isinstance(table, list):
                items = cast(list[Any], table)
                for it in items:
                    d = _as_str_any_dict(it)
                    if d is not None and d.get("name") == self._model:
                        return d
                return None
            dtable = _as_str_any_dict(table)
            if dtable is not None:
                return _as_str_any_dict(dtable.get(self._model))
            return None

        # Kelvin conversion (legacy-compatible)
        try:
            conv = self.get_data("$.local.leds_conv", is_None_possible=True)
            model_params = _find_model_params(conv)
            if model_params is not None:
                kelvins_any = model_params.get("kelvin")
                wb_any = model_params.get("white_blue")
                if wb_any is None:
                    wb_any = model_params.get("wb")

                if isinstance(kelvins_any, list) and isinstance(wb_any, list):
                    kelvins_list = cast(list[Any], kelvins_any)
                    wb_list = cast(list[Any], wb_any)
                    kelvins = [v for v in kelvins_list if isinstance(v, (int, float))]
                    wb_vals = [v for v in wb_list if isinstance(v, (int, float))]
                    if len(kelvins) == len(wb_vals) and len(kelvins) >= 2:
                        self._kelvin_to_wb = _make_interpolator(
                            [float(v) for v in kelvins], [float(v) for v in wb_vals]
                        )
                        self._wb_to_kelvin = _make_interpolator(
                            [float(v) for v in wb_vals], [float(v) for v in kelvins]
                        )
        except Exception as e:
            _LOGGER.debug("LED conversion init failed: %s", e)

        # Intensity compensation (legacy-compatible)
        if self._must_compensate_intensity:
            try:
                comp = self.get_data(
                    "$.local.leds_intensity_compensation", is_None_possible=True
                )
                model_params = _find_model_params(comp)
                if model_params is not None:
                    wb_any = model_params.get("white_blue")
                    intensity_any = model_params.get("intensity")

                    # Accept alternate key names while keeping the same algorithm
                    if wb_any is None:
                        wb_any = model_params.get("wb")
                    if intensity_any is None:
                        intensity_any = model_params.get("factor")

                    if isinstance(wb_any, list) and isinstance(intensity_any, list):
                        wb_list = cast(list[Any], wb_any)
                        intensity_list = cast(list[Any], intensity_any)
                        wb_vals = [v for v in wb_list if isinstance(v, (int, float))]
                        intensities = [
                            v for v in intensity_list if isinstance(v, (int, float))
                        ]
                        if len(wb_vals) == len(intensities) and len(wb_vals) >= 2:
                            self._intensity_compensation = _make_interpolator(
                                [float(v) for v in wb_vals],
                                [float(v) for v in intensities],
                            )
                            min_blue = float(self._intensity_compensation(0))
                            min_white = float(self._intensity_compensation(125))
                            self._intensity_compensation_reference = (
                                min_white if min_blue > min_white else min_blue
                            )
            except Exception as e:
                _LOGGER.debug("LED intensity compensation init failed: %s", e)

        return data

    def _wb(self, value: float) -> tuple[float, float]:
        """Convert a wb value (0..200) to (white, blue) percentages.

        Notes:
            - Values are clamped to [0..200] before conversion.
            - wb >= 100 means white is saturated at 100 and blue decreases.
            - wb < 100 means blue is saturated at 100 and white increases.
        """
        # Clamp to the valid [0..200] wb range to avoid crazy results from extrapolation
        value = max(0.0, min(200.0, float(value)))
        if value >= 100.0:
            white = 100.0
            blue = 200.0 - value
        else:
            blue = 100.0
            white = value
        return white, blue

    def kelvin_to_white_and_blue(
        self, kelvin: Any, intensity: int = 100
    ) -> dict[str, Any]:
        """Convert kelvin/intensity into white/blue (and preserve moon).

        Uses the precomputed kelvin->wb polynomial when available; otherwise falls back.
        Applies optional intensity compensation for high-kelvin values (legacy behavior).
        """
        # Protect against missing kelvin->wb conversion function
        if self._kelvin_to_wb is None:
            _LOGGER.debug("No kelvin->wb conversion available, using fallback wb value")
            wb = 200.0
        else:
            wb = float(self._kelvin_to_wb(kelvin))

        _LOGGER.debug("kelvin to wb %s", wb)
        white, blue = self._wb(wb)
        _LOGGER.debug("white: %s, blue: %s", white, blue)

        if (
            self._intensity_compensation is not None
            and self._intensity_compensation_reference is not None
            and isinstance(kelvin, (int, float))
            and kelvin >= 12000
        ):
            denom = float(self._intensity_compensation(wb))
            if denom != 0:
                intensity_compensation_factor = (
                    self._intensity_compensation_reference / denom
                )
            else:
                intensity_compensation_factor = 1.0
            _LOGGER.debug("Intensity factor %s", intensity_compensation_factor)
        else:
            intensity_compensation_factor = 1.0

        white = white * intensity / 100.0 * intensity_compensation_factor
        blue = blue * intensity / 100.0 * intensity_compensation_factor

        moon = self.get_data(LED_MOON_INTERNAL_NAME, is_None_possible=True)
        res: dict[str, Any] = {
            "kelvin": int(kelvin) if isinstance(kelvin, (int, float, str)) else 9000,
            "intensity": int(intensity),
            "white": int(white),
            "blue": int(blue),
            "moon": moon,
        }
        _LOGGER.debug(
            "Kelvin to white and blue: %s (wb=%s) with compensation %s",
            res,
            wb,
            intensity_compensation_factor,
        )
        return res

    def white_and_blue_to_kelvin(self, white: Any, blue: Any) -> dict[str, Any]:
        """Convert white/blue into derived kelvin/intensity (and preserve moon).

        For G1 devices, white/blue is the native manual payload, so this is used to
        populate/correct kelvin and intensity values cached in local state.
        """
        w = float(white) if isinstance(white, (int, float)) else 0.0
        b = float(blue) if isinstance(blue, (int, float)) else 0.0

        if w != 0.0 or b != 0.0:
            if w >= b:
                intensity = w
                if intensity == 0:
                    wb = 200.0
                else:
                    wb = 200.0 - b * 100.0 / intensity
            else:
                intensity = b
                if intensity == 0:
                    wb = 0.0
                else:
                    wb = w * 100.0 / intensity

            wb = max(0.0, min(200.0, wb))

            # Safely compute kelvin
            kelvin: float | int | None
            if self._wb_to_kelvin is not None:
                try:
                    kelvin = float(self._wb_to_kelvin(wb))
                except Exception:
                    kelvin = None
            else:
                kelvin = self.get_data(LED_KELVIN_INTERNAL_NAME, is_None_possible=True)

            if kelvin is None:
                kelvin = 9000

            moon = self.get_data(LED_MOON_INTERNAL_NAME, is_None_possible=True)

            if (
                self._intensity_compensation is not None
                and self._intensity_compensation_reference is not None
                and kelvin >= 12000
            ):
                denom = float(self._intensity_compensation(wb))
                if denom != 0:
                    intensity_compensation_factor = (
                        self._intensity_compensation_reference / denom
                    )
                else:
                    intensity_compensation_factor = 1.0
                _LOGGER.debug("Intensity factor %s", intensity_compensation_factor)
            else:
                intensity_compensation_factor = 1.0

            intensity = (
                intensity / intensity_compensation_factor
                if intensity_compensation_factor != 0
                else intensity
            )

            res: dict[str, Any] = {
                "kelvin": int(kelvin),
                "intensity": int(intensity),
                "white": int(w),
                "blue": int(b),
                "moon": moon,
            }
        else:
            moon = self.get_data(LED_MOON_INTERNAL_NAME, is_None_possible=True)
            kelvin = self.get_data(LED_KELVIN_INTERNAL_NAME, is_None_possible=True)
            if kelvin is None or kelvin < 8000:
                kelvin = 9000
            res = {
                "kelvin": int(kelvin),
                "intensity": 0,
                "white": 0,
                "blue": 0,
                "moon": moon,
            }
        return res

    def update_light_wb(self) -> None:
        """For G1 devices, compute kelvin/intensity from the /manual white/blue payload."""
        data = self.get_data(
            '$.sources[?(@.name=="/manual")].data', is_None_possible=True
        )
        if not isinstance(data, dict):
            return
        data = cast(dict[str, Any], data)

        if "white" not in data or "blue" not in data:
            return

        new_data = self.white_and_blue_to_kelvin(data["white"], data["blue"])
        _LOGGER.debug("reefbeat.update_light_wb %s => %s", data, new_data)

        data["kelvin"] = new_data.get("kelvin")
        data["intensity"] = new_data.get("intensity")

        # Must copy this data because virtual led can request KI before available in "/manual"
        self.data["local"]["manual_trick"]["kelvin"] = new_data.get("kelvin")
        self.data["local"]["manual_trick"]["intensity"] = new_data.get("intensity")

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        """Get data, with G1-only overrides for kelvin/intensity.

        On G1 devices, kelvin/intensity are not exposed by the device, so they are served
        from the locally-derived `manual_trick` cache.
        """
        if self._g1 and name == LED_KELVIN_INTERNAL_NAME:
            return self.data["local"]["manual_trick"]["kelvin"]
        if self._g1 and name == LED_INTENSITY_INTERNAL_NAME:
            return self.data["local"]["manual_trick"]["intensity"]
        return super().get_data(name, is_None_possible)

    def update_light_ki(self) -> None:
        """For G2 (and virtual), derive white/blue from kelvin/intensity into /manual payload."""
        manual = self.get_data(
            '$.sources[?(@.name=="/manual")].data', is_None_possible=True
        )
        if not isinstance(manual, dict):
            return

        kelvin = self.get_data(LED_KELVIN_INTERNAL_NAME, is_None_possible=True)
        intensity = self.get_data(LED_INTENSITY_INTERNAL_NAME, is_None_possible=True)

        if kelvin is None or intensity is None:
            return

        try:
            k_i = {"kelvin": int(kelvin), "intensity": int(intensity)}
        except (TypeError, ValueError):
            return

        _LOGGER.debug("Update KI: %s", k_i)
        new_data = self.kelvin_to_white_and_blue(k_i["kelvin"], k_i["intensity"])

        # Only set keys that exist in result (defensive)
        if "white" in new_data:
            manual["white"] = new_data["white"]
        if "blue" in new_data:
            manual["blue"] = new_data["blue"]
        if "moon" in new_data and "moon" in manual:
            manual["moon"] = new_data["moon"]

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch device sources, then update derived state (acclimation/status and wb/ki)."""
        data = await super().fetch_data()
        if self._g1:
            self.update_light_wb()
        self.update_acclimation()
        self.force_status_update()
        return data

    async def push_values(self, source: str, method: str = "post") -> None:
        """Push the current payload for a source to the device.

        Notes:
            - Special-cases `/mode` in `timer` mode to post to `/timer`.
            - RSLED90 manual payload is reduced to white/blue/moon only.
        """
        if (
            source == "/mode"
            and self.get_data('$.sources[?(@.name=="/mode")].data.mode') == "timer"
        ):
            await self.post_specific("/timer")
            return

        payload = self.get_data(
            "$.sources[?(@.name=='" + source + "')].data", is_None_possible=True
        )
        if payload is None:
            _LOGGER.error("push_values: no payload found for source=%s", source)
            return

        if self._rsled90_patch and source == "/manual":
            # RSLED90 expects only wb+moon keys
            payload = {
                "white": int(payload["white"]),
                "blue": int(payload["blue"]),
                "moon": int(payload["moon"]),
            }

        _LOGGER.debug("PUSH VALUE: %s", payload)
        await self._http_send(self._base_url + source, payload, method)

    async def post_specific(self, source: str) -> None:
        """Post special-case endpoints that require custom payload building (e.g. /timer)."""
        if source == "/timer":
            payload = self.get_data(
                '$.sources[?(@.name=="/manual")].data', is_None_possible=True
            )
            if not isinstance(payload, dict):
                return
            payload = cast(dict[str, Any], payload)

            if self._rsled90_patch:
                payload = {
                    "white": int(payload.get("white", 0)),
                    "blue": int(payload.get("blue", 0)),
                    "moon": int(payload.get("moon", 0)),
                }

            duration = (
                self.get_data(LED_MANUAL_DURATION_INTERNAL_NAME, is_None_possible=True)
                or 0
            )
            if duration > 0:
                payload["duration"] = duration
                await self._http_send(self._base_url + source, payload, "post")
            else:
                source = "/manual"

            await self._http_send(self._base_url + source, payload, "post")
        else:
            payload_name = "$.local." + source[1:]
            payload = self.get_data(payload_name, is_None_possible=True)
            if payload is None:
                return
            await self._http_send(self._base_url + source, payload, "post")

    def force_status_update(self, state: bool = False) -> None:
        """Update local `status` based on current manual channels, or force on."""
        if state:
            self.data["local"]["status"] = True
            return

        white = self.get_data(LED_WHITE_INTERNAL_NAME, is_None_possible=True) or 0
        blue = self.get_data(LED_BLUE_INTERNAL_NAME, is_None_possible=True) or 0
        moon = self.get_data(LED_MOON_INTERNAL_NAME, is_None_possible=True) or 0

        self.data["local"]["status"] = bool(white > 0 or blue > 0 or moon > 0)

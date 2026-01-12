"""ReefBeat ReefDose API wrapper.

Provides access to ReefDose endpoints:
- Per-head settings and actions (manual dose, calibration workflow)
- Dosing queue and device settings
- Optional bundle setup logic for supported supplements
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Optional, cast

import aiohttp

from .api import ReefBeatAPI

_LOGGER = logging.getLogger(__name__)


class ReefDoseAPI(ReefBeatAPI):
    """ReefDose API wrapper (heads, calibration, bundle support)."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
        heads_nb: int,
    ) -> None:
        """Create a ReefDoseAPI instance.

        Args:
            ip: Device IP/host.
            live_config_update: Whether the base API performs live config updates.
            heads_nb: Number of dosing heads (typically 2 or 4).

        Notes:
            Initializes a `local.head` cache with per-head defaults used by the UI
            (manual dose, calibration dose, supplement wizard fields).
        """
        super().__init__(ip, live_config_update, session)
        self._heads_nb = heads_nb

        # Register sources
        self.add_source("/device-settings", "config", "")
        self.add_source("/dosing-queue", "data", "")

        # Initialize local head cache (preserve existing local keys like use_cloud_api)
        local_any = self.data.get("local")
        if not isinstance(local_any, dict):
            local_any = {}
            self.data["local"] = local_any

        local = cast(dict[str, Any], local_any)
        if self._heads_nb not in (2, 4):
            _LOGGER.error(
                "redsea.reefbeat.ReefDoseAPI.__init__() unknown head number: %d",
                self._heads_nb,
            )
            local.setdefault("head", {})
        else:
            # Start with empty dicts so subsequent assignments won't crash
            local.setdefault("head", {str(i): {} for i in range(1, self._heads_nb + 1)})

        # Add per-head settings sources and default local values
        heads = cast(
            dict[str, dict[str, Any]],
            cast(dict[str, Any], self.data["local"]).get("head", {}),
        )
        for head in range(1, self._heads_nb + 1):
            self.add_source(f"/head/{head}/settings", "data", "")
            heads[str(head)] = {
                "manual_dose": 5,
                "calibration_dose": 5,
                "initial_volume": None,
                "new_supplement": "7d67412c-fde0-44d4-882a-dc8746fd4acb",
                "new_supplement_brand_name": "",
                "new_supplement_name": "",
                "new_supplement_short_name": "",
            }

    async def calibration(self, action: str, head: int, param: Any) -> None:
        """Run a calibration workflow action for a head.

        Sends POST to `/head/{head}/{action}`. When the action ends setup and the
        supplement UID indicates a supported bundle, enables bundle settings.
        """
        await self._http_send(
            self._base_url + "/head/" + str(head) + "/" + action,
            param,
            method="post",
        )

        uid_any = self.get_data(
            "$.sources[?(@.name=='/head/"
            + str(head)
            + "/settings')].data.supplement.uid",
            is_None_possible=True,
        )
        uid = uid_any if isinstance(uid_any, str) else None

        bundles = [
            "6b7d2c15-0d25-4447-b089-854ef6ba99f2",
            "6f6a53db-0985-47f4-92bd-cef092d97d22",
            "18c5a293-f14d-4d40-ad43-0420e54f9a45",
            "bb73e4c2-e366-4304-aaeb-50e4b52fa10f",
        ]
        if (
            action == "end-setup"
            and uid in bundles
            and not self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.bundled_heads",
                is_None_possible=True,
            )
        ):
            payload: dict[str, bool] = {
                "bundled_heads": True,
                "auto_fill_schedule": False,
            }
            await self._http_send(self._base_url + "/bundle/settings", payload, "put")

    async def set_bundle(self, param: Any) -> None:
        """Start/continue bundle setup by posting to `/bundle/setup`."""
        await self._http_send(self._base_url + "/bundle/setup", param, method="post")

    async def press(self, action: str, head: Optional[int] = None) -> None:
        """Trigger an action.

        - If `head` is provided: POST to `/head/{head}/{action}` with a manual dose payload.
        - Otherwise: POST to `/{action}` with an empty payload.
        """
        if head is not None:
            manual_dose = self.get_data(
                "$.local.head." + str(head) + ".manual_dose",
                is_None_possible=True,
            )
            payload: dict[str, Any] = {
                "manual_dose_scheduled": True,
                "volume": manual_dose,
            }
            await self._http_send(
                self._base_url + "/head/" + str(head) + "/" + action,
                payload,
                method="post",
            )
            return

        await self._http_send(self._base_url + "/" + action, payload={}, method="post")

    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        head: Optional[int] = None,
    ) -> None:
        """Push cached values to the device.

        Args:
            source: Endpoint name (used when `head` is not provided).
            method: HTTP method to use for `source`.
            head: If provided, pushes head settings to `/head/{head}/settings`.

        Notes:
            When bundle mode is enabled, some fields are stripped before PUT to match
            the device expectations.
        """
        if isinstance(head, int):
            payload = copy.deepcopy(
                self.get_data(
                    "$.sources[?(@.name=='/head/" + str(head) + "/settings')].data",
                    is_None_possible=True,
                )
            )
            if payload is None:
                _LOGGER.error(
                    "ReefDoseAPI.push_values: no head payload for head=%s", head
                )
                return

            # If bundle suppress some fields
            if self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.bundled_heads",
                is_None_possible=True,
            ):
                if isinstance(payload, dict):
                    payload_dict = cast(dict[str, Any], payload)
                    for field in ("supplement", "is_food_head", "food_delay"):
                        payload_dict.pop(field, None)
                    _LOGGER.debug("Remove fields for bundle %s", payload_dict)

            await self._http_send(
                self._base_url + "/head/" + str(head) + "/settings", payload, "put"
            )
            return

        payload = self.get_data(
            "$.sources[?(@.name=='" + source + "')].data",
            is_None_possible=True,
        )
        if payload is None:
            _LOGGER.error(
                "ReefDoseAPI.push_values: no payload found for source=%s", source
            )
            return
        await self._http_send(self._base_url + source, payload, method)

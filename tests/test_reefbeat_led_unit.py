from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from custom_components.redsea.const import (
    HW_G1_LED_IDS,
    LED_BLUE_INTERNAL_NAME,
    LED_INTENSITY_INTERNAL_NAME,
    LED_KELVIN_INTERNAL_NAME,
    LED_MOON_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
    VIRTUAL_LED,
)
from custom_components.redsea.reefbeat.led import ReefLedAPI


@dataclass
class _FakeSession:
    """Minimal aiohttp session stub for unit tests."""


def _make_led_api(*, hw: str, intensity_compensation: bool = False) -> ReefLedAPI:
    return ReefLedAPI(
        ip="192.0.2.20",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        hw=hw,
        intensity_compensation=intensity_compensation,
    )


def test_led_wb_clamps_and_splits() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    assert api._wb(-10) == (0.0, 100.0)
    assert api._wb(50) == (50.0, 100.0)
    assert api._wb(100) == (100.0, 100.0)
    assert api._wb(150) == (100.0, 50.0)
    assert api._wb(250) == (100.0, 0.0)


def test_kelvin_to_white_and_blue_fallback_uses_wb_200() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 3})

    res = api.kelvin_to_white_and_blue(12000, intensity=50)

    assert res["white"] == 50
    assert res["blue"] == 0
    assert res["moon"] == 3


def test_white_and_blue_to_kelvin_zero_channels_defaults_kelvin_min_9000() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 0, "kelvin": 7000})

    res = api.white_and_blue_to_kelvin(0, 0)

    assert res["intensity"] == 0
    assert res["kelvin"] == 9000


def test_update_light_wb_sets_manual_kelvin_intensity_and_trick_cache() -> None:
    # Use a G1 model so get_data overrides pull from manual_trick
    hw = HW_G1_LED_IDS[0]
    api = _make_led_api(hw=hw)
    api.add_source("/manual", "data", {"white": 100, "blue": 0, "moon": 0})

    api.update_light_wb()

    manual = api.get_data('$.sources[?(@.name=="/manual")].data')
    assert isinstance(manual, dict)

    assert manual.get("kelvin") == 9000
    assert manual.get("intensity") == 100

    assert api.data["local"]["manual_trick"]["kelvin"] == 9000
    assert api.data["local"]["manual_trick"]["intensity"] == 100

    # And G1 get_data should now serve kelvin/intensity from the trick cache
    assert api.get_data(LED_KELVIN_INTERNAL_NAME) == 9000
    assert api.get_data(LED_INTENSITY_INTERNAL_NAME) == 100


def test_update_light_ki_updates_white_blue_from_kelvin_intensity() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source(
        "/manual",
        "data",
        {"white": 0, "blue": 0, "moon": 0, "kelvin": 12000, "intensity": 50},
    )

    api.update_light_ki()

    assert api.get_data(LED_WHITE_INTERNAL_NAME) == 50
    assert api.get_data(LED_BLUE_INTERNAL_NAME) == 0
    assert api.get_data(LED_MOON_INTERNAL_NAME) == 0


@pytest.mark.asyncio
async def test_apply_runtime_source_patches_rsled90_and_preset_name_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    async def _fake_probe(path: str) -> int:
        if path == "/dashboard":
            return 404
        if path == "/preset_name":
            return 200
        return 200

    monkeypatch.setattr(api, "_probe_path", _fake_probe)

    await api._apply_runtime_source_patches()

    assert api._rsled90_patch is True
    assert api._preset_name_is_single is True

    # /dashboard should be removed, and "/" should be added as device-info
    source_names = [
        s.get("name") for s in cast(list[dict[str, Any]], api.data["sources"])
    ]
    assert "/dashboard" not in source_names
    assert "/" in source_names
    assert "/preset_name" in source_names

    # A couple of required sources should also exist
    assert "/manual" in source_names
    assert "/acclimation" in source_names
    assert "/moonphase" in source_names


@pytest.mark.asyncio
async def test_probe_path_returns_zero_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    class _Boom:
        def get(self, *_: Any, **__: Any) -> Any:
            raise RuntimeError("boom")

    monkeypatch.setattr(api, "_session", _Boom())

    assert await api._probe_path("/any") == 0


@pytest.mark.asyncio
async def test_probe_path_returns_status_on_success(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    class _Resp:
        status = 204

        async def __aenter__(self) -> "_Resp":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return

    class _Session:
        def get(self, *_: Any, **__: Any) -> _Resp:
            return _Resp()

    monkeypatch.setattr(api, "_session", _Session())
    assert await api._probe_path("/ok") == 204


@pytest.mark.asyncio
async def test_apply_runtime_source_patches_preset_name_per_day(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    async def _fake_probe(path: str) -> int:
        if path == "/dashboard":
            return 200
        if path == "/preset_name":
            return 404
        return 200

    monkeypatch.setattr(api, "_probe_path", _fake_probe)

    await api._apply_runtime_source_patches()

    assert api._rsled90_patch is False
    assert api._preset_name_is_single is False

    source_names = [
        s.get("name") for s in cast(list[dict[str, Any]], api.data["sources"])
    ]
    assert "/" not in source_names
    for day in range(1, 8):
        assert f"/preset_name/{day}" in source_names


def test_update_acclimation_copies_fields_when_present() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source(
        "/acclimation", "data", {"duration": 10, "start_intensity_factor": 12}
    )

    api.update_acclimation()

    assert api.data["local"]["acclimation"]["duration"] == 10
    assert api.data["local"]["acclimation"]["start_intensity_factor"] == 12


def test_update_acclimation_ignores_non_dict_payload() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    before = dict(api.data["local"]["acclimation"])
    api.add_source("/acclimation", "data", [1, 2, 3])

    api.update_acclimation()

    assert api.data["local"]["acclimation"] == before


@pytest.mark.asyncio
async def test_get_initial_data_builds_kelvin_conversions_from_list_table(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    api.data["local"]["leds_conv"] = [
        {
            "name": VIRTUAL_LED,
            "kelvin": [8000, 9000, 10000, 11000, 12000],
            "white_blue": [0, 25, 50, 75, 100],
        }
    ]

    async def _noop() -> None:
        return

    async def _fake_initial() -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    await api.get_initial_data()
    assert api._kelvin_to_wb is not None
    assert api._wb_to_kelvin is not None


@pytest.mark.asyncio
async def test_get_initial_data_ignores_invalid_leds_conv_table(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    # Not a list or dict => _find_model_params returns None via the final return.
    api.data["local"]["leds_conv"] = "bad"

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    await api.get_initial_data()
    assert api._kelvin_to_wb is None
    assert api._wb_to_kelvin is None


def test_white_and_blue_to_kelvin_compensation_zero_denom_defaults_factor_one() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 0, "kelvin": 12000})

    api._intensity_compensation = lambda _wb: 0.0  # type: ignore[method-assign]
    api._intensity_compensation_reference = 1.0
    api._wb_to_kelvin = lambda _wb: 12000  # type: ignore[method-assign]

    res = api.white_and_blue_to_kelvin(white=50, blue=25)
    assert res["kelvin"] == 12000
    assert res["intensity"] == 50


@pytest.mark.asyncio
async def test_get_initial_data_builds_intensity_compensation_from_dict_table(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED, intensity_compensation=True)

    api.data["local"]["leds_intensity_compensation"] = {
        VIRTUAL_LED: {
            "wb": [0, 25, 50, 75, 100, 125],
            "factor": [1, 1.1, 1.2, 1.3, 1.4, 1.5],
        }
    }

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    await api.get_initial_data()
    assert api._intensity_compensation is not None
    assert api._intensity_compensation_reference is not None


@pytest.mark.asyncio
async def test_get_initial_data_kelvin_conversion_accepts_wb_key(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    # Dict-table variant + 'wb' key variant.
    api.data["local"]["leds_conv"] = {
        VIRTUAL_LED: {
            "kelvin": [8000, 9000, 10000, 11000, 12000],
            "wb": [0, 25, 50, 75, 100],
        }
    }

    async def _noop(self: Any = None) -> None:  # type: ignore[no-untyped-def]
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    await api.get_initial_data()
    assert api._kelvin_to_wb is not None


@pytest.mark.asyncio
async def test_get_initial_data_list_table_skips_non_dict_and_missing_model(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    # List-table variant that contains non-dicts and does not include this model.
    api.data["local"]["leds_conv"] = [
        123,
        {
            "name": "OTHER",
            "kelvin": [8000, 9000, 10000, 11000, 12000],
            "wb": [0, 25, 50, 75, 100],
        },
    ]

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    await api.get_initial_data()
    assert api._kelvin_to_wb is None
    assert api._wb_to_kelvin is None


@pytest.mark.asyncio
async def test_get_initial_data_dict_table_entry_must_be_dict(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    # Dict-table variant where the model entry is not a dict.
    api.data["local"]["leds_conv"] = {VIRTUAL_LED: 123}

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    await api.get_initial_data()
    assert api._kelvin_to_wb is None
    assert api._wb_to_kelvin is None


@pytest.mark.asyncio
async def test_get_initial_data_dict_table_executes_model_lookup_line(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    # Force `conv` to be a dict-table so `_find_model_params()` takes the dict path.
    orig_get_data = api.get_data

    def _forced(name: str, is_None_possible: bool = False) -> Any:
        if name == "$.local.leds_conv":
            return {
                VIRTUAL_LED: {
                    "kelvin": [8000, 9000, 10000, 11000, 12000],
                    "wb": [0, 25, 50, 75, 100],
                }
            }
        return orig_get_data(name, is_None_possible=is_None_possible)

    monkeypatch.setattr(api, "get_data", _forced)

    await api.get_initial_data()
    assert api._wb_to_kelvin is not None


@pytest.mark.asyncio
async def test_get_initial_data_kelvin_conversion_logs_on_exception(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    seen: list[str] = []
    monkeypatch.setattr(
        "custom_components.redsea.reefbeat.led._LOGGER.debug",
        lambda msg, *args, **kwargs: seen.append(msg % args),
    )

    orig_get_data = api.get_data

    def _boom(name: str, is_None_possible: bool = False) -> Any:
        if name == "$.local.leds_conv":
            raise RuntimeError("boom")
        return orig_get_data(name, is_None_possible=is_None_possible)

    monkeypatch.setattr(api, "get_data", _boom)

    await api.get_initial_data()
    assert any("LED conversion init failed" in s for s in seen)


@pytest.mark.asyncio
async def test_get_initial_data_intensity_compensation_logs_on_exception(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED, intensity_compensation=True)

    async def _noop() -> None:
        return

    async def _fake_initial_bound(self: Any) -> dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(api, "_apply_runtime_source_patches", _noop)
    monkeypatch.setattr(ReefLedAPI.__mro__[1], "get_initial_data", _fake_initial_bound)

    seen: list[str] = []
    monkeypatch.setattr(
        "custom_components.redsea.reefbeat.led._LOGGER.debug",
        lambda msg, *args, **kwargs: seen.append(msg % args),
    )

    orig_get_data = api.get_data

    def _boom(name: str, is_None_possible: bool = False) -> Any:
        if name == "$.local.leds_intensity_compensation":
            raise RuntimeError("boom")
        return orig_get_data(name, is_None_possible=is_None_possible)

    monkeypatch.setattr(api, "get_data", _boom)

    await api.get_initial_data()
    assert any("LED intensity compensation init failed" in s for s in seen)


def test_kelvin_to_white_and_blue_applies_intensity_compensation_branches() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 1})

    api._kelvin_to_wb = lambda _: 125
    api._intensity_compensation_reference = 10.0

    # denom == 0 branch
    api._intensity_compensation = lambda _: 0
    res = api.kelvin_to_white_and_blue(12000, intensity=100)
    assert res["moon"] == 1

    # denom != 0 branch
    api._intensity_compensation = lambda _: 5
    res2 = api.kelvin_to_white_and_blue(12000, intensity=100)
    assert res2["moon"] == 1


def test_white_and_blue_to_kelvin_handles_wb_to_kelvin_exception_and_compensation() -> (
    None
):
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 4})

    def _boom(_: Any) -> Any:
        raise RuntimeError("nope")

    api._wb_to_kelvin = _boom
    res = api.white_and_blue_to_kelvin(100, 0)
    assert res["kelvin"] == 9000
    assert res["moon"] == 4

    # Now exercise compensation + divide-by-factor and factor==0 handling.
    api._wb_to_kelvin = lambda _: 12000
    api._intensity_compensation = lambda _: 5
    api._intensity_compensation_reference = 10.0
    res2 = api.white_and_blue_to_kelvin(100, 0)
    assert res2["kelvin"] == 12000
    assert res2["intensity"] == 50

    # factor==0 path (reference 0)
    api._intensity_compensation_reference = 0.0
    res3 = api.white_and_blue_to_kelvin(100, 0)
    assert res3["intensity"] == 100


def test_white_and_blue_to_kelvin_covers_intensity_zero_branches() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 0, "kelvin": 9000})

    # w>=b path with intensity==0 (w=0, b negative)
    res1 = api.white_and_blue_to_kelvin(0, -10)
    assert res1["intensity"] == 0

    # w<b path with intensity==0 (b=0, w negative)
    res2 = api.white_and_blue_to_kelvin(-10, 0)
    assert res2["intensity"] == 0


def test_white_and_blue_to_kelvin_covers_w_less_than_b_nonzero_branch() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 0, "kelvin": 9000})

    res = api.white_and_blue_to_kelvin(10, 20)
    assert res["intensity"] == 20


def test_white_and_blue_to_kelvin_logs_intensity_factor(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 0})

    api._wb_to_kelvin = lambda _: 13000
    api._intensity_compensation = lambda _: 5.0
    api._intensity_compensation_reference = 10.0

    seen: list[str] = []
    monkeypatch.setattr(
        "custom_components.redsea.reefbeat.led._LOGGER.debug",
        lambda msg, *args, **kwargs: seen.append(msg % args),
    )

    res = api.white_and_blue_to_kelvin(100, 0)
    assert res["intensity"] == 50
    assert any("Intensity factor" in s for s in seen)


def test_white_and_blue_to_kelvin_logs_intensity_factor_when_kelvin_high(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 0})

    api._wb_to_kelvin = lambda _: 15000
    api._intensity_compensation = lambda _: 4.0
    api._intensity_compensation_reference = 8.0

    seen: list[str] = []
    monkeypatch.setattr(
        "custom_components.redsea.reefbeat.led._LOGGER.debug",
        lambda msg, *args, **kwargs: seen.append(msg % args),
    )

    api.white_and_blue_to_kelvin(10, 20)
    assert any("Intensity factor" in s for s in seen)


def test_update_light_ki_early_returns() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    # manual not a dict
    api.add_source("/manual", "data", [])
    api.update_light_ki()


def test_update_light_ki_sets_white_blue_when_keys_present(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source(
        "/manual",
        "data",
        {"white": 0, "blue": 0, "moon": 0, "kelvin": 12000, "intensity": 50},
    )

    monkeypatch.setattr(
        api,
        "kelvin_to_white_and_blue",
        lambda *_args, **_kwargs: {"white": 11, "blue": 22, "moon": 33},
    )

    api.update_light_ki()
    assert api.get_data(LED_WHITE_INTERNAL_NAME) == 11
    assert api.get_data(LED_BLUE_INTERNAL_NAME) == 22


def test_update_light_ki_handles_non_int_kelvin_intensity_values() -> None:
    # Use a non-G1 model so get_data reads from /manual directly.
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source(
        "/manual",
        "data",
        {"white": 0, "blue": 0, "moon": 0, "kelvin": "x", "intensity": "y"},
    )

    api.update_light_ki()


def test_update_light_wb_early_returns() -> None:
    hw = HW_G1_LED_IDS[0]
    api = _make_led_api(hw=hw)

    # Not a dict
    api.add_source("/manual", "data", [])
    api.update_light_wb()

    # Missing required keys
    api.remove_source("/manual")
    api.add_source("/manual", "data", {"white": 1})
    api.update_light_wb()

    # kelvin/intensity missing
    api.remove_source("/manual")
    api.add_source("/manual", "data", {"white": 0, "blue": 0, "moon": 0})
    api.update_light_ki()

    # kelvin/intensity not int-able
    api.remove_source("/manual")
    api.add_source(
        "/manual",
        "data",
        {"white": 0, "blue": 0, "moon": 0, "kelvin": "x", "intensity": "y"},
    )
    api.update_light_ki()


@pytest.mark.asyncio
async def test_fetch_data_calls_derivations(monkeypatch: Any) -> None:
    hw = HW_G1_LED_IDS[0]
    api = _make_led_api(hw=hw)

    called: list[str] = []

    async def _fake_fetch(self: Any) -> dict[str, Any]:
        called.append("fetch")
        return {"ok": True}

    monkeypatch.setattr(ReefLedAPI.__mro__[1], "fetch_data", _fake_fetch)
    monkeypatch.setattr(api, "update_light_wb", lambda: called.append("wb"))
    monkeypatch.setattr(api, "update_acclimation", lambda: called.append("accl"))
    monkeypatch.setattr(
        api, "force_status_update", lambda *_, **__: called.append("status")
    )

    await api.fetch_data()
    assert called == ["fetch", "wb", "accl", "status"]


@pytest.mark.asyncio
async def test_push_values_timer_mode_calls_post_specific(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/mode", "data", {"mode": "timer"})

    called: list[str] = []

    async def _post(source: str) -> None:
        called.append(source)

    monkeypatch.setattr(api, "post_specific", _post)
    await api.push_values("/mode")
    assert called == ["/timer"]


@pytest.mark.asyncio
async def test_push_values_missing_payload_logs_and_returns(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    errs: list[str] = []
    monkeypatch.setattr(
        "custom_components.redsea.reefbeat.led._LOGGER.error",
        lambda msg, *args, **kwargs: errs.append(msg % args),
    )

    await api.push_values("/nope")
    assert errs


@pytest.mark.asyncio
async def test_push_values_rsled90_manual_payload_is_reduced(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api._rsled90_patch = True
    api.add_source("/manual", "data", {"white": 1, "blue": 2, "moon": 3, "extra": 4})

    sent: list[tuple[str, dict[str, Any], str]] = []

    async def _send(url: str, payload: Any, method: str) -> None:
        sent.append((url, cast(dict[str, Any], payload), method))

    monkeypatch.setattr(api, "_http_send", _send)
    await api.push_values("/manual")

    assert sent
    _, payload, _ = sent[0]
    assert set(payload) == {"white", "blue", "moon"}


@pytest.mark.asyncio
async def test_post_specific_timer_duration_branches(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"white": 1, "blue": 2, "moon": 3})

    sent: list[str] = []

    async def _send(url: str, payload: Any, method: str) -> None:
        sent.append(url)

    monkeypatch.setattr(api, "_http_send", _send)

    # duration == 0 -> source rewritten to /manual, single send
    api.data["local"]["manual_duration"] = 0
    await api.post_specific("/timer")
    assert sent[-1].endswith("/manual")

    # duration > 0 -> includes duration and sends to /timer twice
    sent.clear()
    api.data["local"]["manual_duration"] = 10
    await api.post_specific("/timer")
    assert len(sent) == 2
    assert all(u.endswith("/timer") for u in sent)


@pytest.mark.asyncio
async def test_post_specific_timer_returns_when_manual_not_dict(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", [])

    called: list[bool] = []

    async def _send(url: str, payload: Any, method: str) -> None:
        called.append(True)

    monkeypatch.setattr(api, "_http_send", _send)
    await api.post_specific("/timer")
    assert called == []


@pytest.mark.asyncio
async def test_post_specific_non_timer_uses_local_payload(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.data["local"]["foo"] = {"a": 1}

    sent: list[str] = []

    async def _send(url: str, payload: Any, method: str) -> None:
        sent.append(url)

    monkeypatch.setattr(api, "_http_send", _send)
    await api.post_specific("/foo")
    assert sent and sent[0].endswith("/foo")


def test_force_status_update_force_and_computed() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"white": 0, "blue": 0, "moon": 0})

    api.force_status_update(True)
    assert api.data["local"]["status"] is True

    api.data["local"]["status"] = False
    api.force_status_update()
    assert api.data["local"]["status"] is False

    api.remove_source("/manual")
    api.add_source("/manual", "data", {"white": 1, "blue": 0, "moon": 0})
    api.force_status_update()
    assert api.data["local"]["status"] is True


@pytest.mark.asyncio
async def test_post_specific_timer_rsled90_payload_reduction(monkeypatch: Any) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api._rsled90_patch = True
    api.add_source("/manual", "data", {"white": 1, "blue": 2, "moon": 3, "extra": 4})
    api.data["local"]["manual_duration"] = 0

    sent: list[dict[str, Any]] = []

    async def _send(url: str, payload: Any, method: str) -> None:
        sent.append(cast(dict[str, Any], payload))

    monkeypatch.setattr(api, "_http_send", _send)
    await api.post_specific("/timer")

    assert sent
    assert set(sent[-1]) == {"white", "blue", "moon"}


@pytest.mark.asyncio
async def test_post_specific_non_timer_missing_payload_is_noop(
    monkeypatch: Any,
) -> None:
    api = _make_led_api(hw=VIRTUAL_LED)

    called: list[bool] = []

    async def _send(url: str, payload: Any, method: str) -> None:
        called.append(True)

    monkeypatch.setattr(api, "_http_send", _send)
    await api.post_specific("/missing")
    assert called == []


def test_white_and_blue_to_kelvin_uses_cached_kelvin_when_no_wb_to_kelvin() -> None:
    api = _make_led_api(hw=VIRTUAL_LED)
    api.add_source("/manual", "data", {"moon": 1, "kelvin": 10000})
    api._wb_to_kelvin = None

    res = api.white_and_blue_to_kelvin(100, 0)
    assert res["kelvin"] == 10000

from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from typing_extensions import Self

from custom_components.redsea.config_flow import (
    _device_to_string,
    _is_cidr,
    get_scan_interval,
    get_scan_interval_safe,
    validate_cloud_input,
)
from custom_components.redsea.const import (
    ADD_CLOUD_API,
    ADD_LOCAL_DETECT,
    ADD_MANUAL_MODE,
    ATO_SCAN_INTERVAL,
    CLOUD_DEVICE_TYPE,
    CLOUD_SCAN_INTERVAL,
    CLOUD_SERVER_ADDR,
    CONF_GROUP_MEMBERS,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_SCAN_INTERVAL,
    CONTROL_SCAN_INTERVAL,
    DOMAIN,
    DOSE_SCAN_INTERVAL,
    HW_ATO_IDS,
    HW_CONTROL_IDS,
    HW_DOSE_IDS,
    HW_LED_IDS,
    HW_MAT_IDS,
    HW_POWER_IDS,
    HW_RUN_IDS,
    LED_SCAN_INTERVAL,
    MAT_SCAN_INTERVAL,
    POWER_SCAN_INTERVAL,
    RUN_SCAN_INTERVAL,
    SCAN_INTERVAL,
    VIRTUAL_LED,
    VIRTUAL_LED_SCAN_INTERVAL,
)
from tests._scan_test_helpers import drive_scan_to_end


def test_scan_interval_helpers() -> None:
    # Cover all get_scan_interval branches.
    assert get_scan_interval(next(iter(HW_DOSE_IDS))) == DOSE_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_MAT_IDS))) == MAT_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_ATO_IDS))) == ATO_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_LED_IDS))) == LED_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_RUN_IDS))) == RUN_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_POWER_IDS))) == POWER_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_CONTROL_IDS))) == CONTROL_SCAN_INTERVAL
    assert get_scan_interval(CLOUD_DEVICE_TYPE) == CLOUD_SCAN_INTERVAL
    assert get_scan_interval("unknown-model") == SCAN_INTERVAL

    assert get_scan_interval_safe(None) == SCAN_INTERVAL


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("192.0.2.0/24", True),
        ("192.0.2.1", True),  # strict=False means single IP parses as /32
        ("not-an-ip", False),
    ],
)
def test_is_cidr(value: str, expected: bool) -> None:
    assert _is_cidr(value) is expected


def test_device_to_string_missing_keys() -> None:
    assert _device_to_string({"ip": "192.0.2.10"}).startswith("192.0.2.10")


@pytest.mark.asyncio
async def test_validate_cloud_input_status_handling(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.config_flow as cf

    class _Resp:
        def __init__(self, status: int) -> None:
            self.status = status

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

    class _Session:
        def __init__(self, status: int, *, raises: bool = False) -> None:
            self._status = status
            self._raises = raises

        def post(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            if self._raises:
                raise RuntimeError("boom")
            return _Resp(self._status)

    monkeypatch.setattr(cf, "async_get_clientsession", lambda _hass: _Session(200))
    assert await validate_cloud_input(hass, "u", "p") is True

    # Another server (a simulator): its own token endpoint
    urls: list[str] = []

    class _Recording(_Session):
        def post(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            urls.append(args[0])
            return super().post(*args, **kwargs)

    monkeypatch.setattr(cf, "async_get_clientsession", lambda _hass: _Recording(200))
    assert await validate_cloud_input(hass, "u", "p", "192.0.2.251") is True
    assert urls == ["https://192.0.2.251/oauth/token"]

    monkeypatch.setattr(cf, "async_get_clientsession", lambda _hass: _Session(401))
    assert await validate_cloud_input(hass, "u", "p") is False

    monkeypatch.setattr(
        cf, "async_get_clientsession", lambda _hass: _Session(0, raises=True)
    )
    assert await validate_cloud_input(hass, "u", "p") is False


@pytest.mark.asyncio
async def test_manual_mode_unique_id_falls_back_to_ip(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the manual-probe path + _unique_id retry fallback."""

    import custom_components.redsea.config_flow as cf

    # Force manual probe branch even for a plain IP (otherwise _is_cidr() treats
    # single IPs as /32 and routes to auto-detect).
    monkeypatch.setattr(cf, "_is_cidr", lambda _s: False)

    async def _sleep(_: float) -> None:
        return None

    monkeypatch.setattr(cf.asyncio, "sleep", _sleep, raising=True)
    monkeypatch.setattr(cf, "HTTP_MAX_RETRY", 2, raising=True)
    monkeypatch.setattr(cf, "HTTP_DELAY_BETWEEN_RETRY", 0, raising=True)

    # Manual probe says device is ReefBeat.
    def _is_rb(*, ip: str):  # type: ignore[no-untyped-def]
        return (True, ip, "RSLED50", "My Light", "uuid-from-probe")

    monkeypatch.setattr(cf, "is_reefbeat", _is_rb)

    # But UUID fetch keeps failing -> fall back to IP.
    def _no_uuid(*, ip: str):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(cf, "get_unique_id", _no_uuid)

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_MANUAL_MODE},
        ),
    )
    assert result2["type"] == FlowResultType.FORM

    result3 = cast(
        dict[str, Any],
        await flow.async_configure(
            result2["flow_id"],
            user_input={CONFIG_FLOW_IP_ADDRESS: "192.0.2.10"},
        ),
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["data"][CONFIG_FLOW_IP_ADDRESS] == "192.0.2.10"
    assert result3["data"][CONFIG_FLOW_HW_MODEL] == "RSLED50"

    entry = cast(Any, result3["result"])
    assert entry.unique_id == "192.0.2.10"

    # Unload to cancel the coordinator's Debouncer timer before teardown.
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_manual_mode_unique_id_resolves_uuid_first_try(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.config_flow as cf

    monkeypatch.setattr(cf, "_is_cidr", lambda _s: False)

    def _is_rb(*, ip: str):  # type: ignore[no-untyped-def]
        return (True, ip, "RSLED50", "My Light", "uuid-from-probe")

    monkeypatch.setattr(cf, "is_reefbeat", _is_rb)

    def _uuid(*, ip: str):  # type: ignore[no-untyped-def]
        return "uuid-ok"

    monkeypatch.setattr(cf, "get_unique_id", _uuid)

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_MANUAL_MODE},
        ),
    )
    assert result2["type"] == FlowResultType.FORM

    result3 = cast(
        dict[str, Any],
        await flow.async_configure(
            result2["flow_id"],
            user_input={CONFIG_FLOW_IP_ADDRESS: "192.0.2.10"},
        ),
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY

    entry = cast(Any, result3["result"])
    assert entry.unique_id == "uuid-ok"

    # Unload to cancel the coordinator's Debouncer timer before teardown.
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_add_local_detect_calls_auto_detect_and_filters_existing(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    import custom_components.redsea.config_flow as cf

    existing_uuid = "uuid-existing"
    MockConfigEntry(
        domain=DOMAIN, title="t", data={}, unique_id=existing_uuid
    ).add_to_hass(hass)

    devices = [
        {
            "ip": "192.0.2.10",
            "hw_model": "RSLED50",
            "friendly_name": "A",
            "uuid": existing_uuid,
        },
        {
            "ip": "192.0.2.11",
            "hw_model": "RSMAT",
            "friendly_name": "B",
            "uuid": "uuid-new",
        },
    ]

    def _get_rb(**_kwargs: Any):  # type: ignore[no-untyped-def]
        return devices

    monkeypatch.setattr(cf, "get_reefbeats", _get_rb)
    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: ["192.0.2.0/24"])

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_LOCAL_DETECT},
        ),
    )
    result2 = await drive_scan_to_end(hass, result2)

    assert result2["type"] == FlowResultType.FORM
    # Should include VIRTUAL_LED and exclude already-configured device
    assert "192.0.2.10" not in str(result2.get("data_schema"))


@pytest.mark.asyncio
async def test_auto_detect_get_reefbeats_exception_shows_form(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover the except branch: when get_reefbeats raises, show the manual IP form."""
    import custom_components.redsea.config_flow as cf

    def _get_rb_raises(**_kwargs: Any) -> None:  # type: ignore[return]
        raise RuntimeError("network failure")

    monkeypatch.setattr(cf, "get_reefbeats", _get_rb_raises)
    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: ["192.0.2.0/24"])

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_LOCAL_DETECT},
        ),
    )
    result2 = await drive_scan_to_end(hass, result2)

    # Exception path must return a form (not crash HA) with nothing_detected error
    assert result2["type"] == FlowResultType.FORM
    assert result2.get("errors", {}).get("base") == "nothing_detected"


@pytest.mark.asyncio
async def test_add_type_virtual_led_creates_entry(hass: HomeAssistant) -> None:
    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: VIRTUAL_LED},
        ),
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONFIG_FLOW_HW_MODEL] == VIRTUAL_LED
    assert result2["data"][CONFIG_FLOW_SCAN_INTERVAL] == VIRTUAL_LED_SCAN_INTERVAL


@pytest.mark.asyncio
async def test_manual_virtual_led_string_creates_entry(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.config_flow as cf

    monkeypatch.setattr(cf, "_is_cidr", lambda _s: False)

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_MANUAL_MODE},
        ),
    )
    assert result2["type"] == FlowResultType.FORM

    result3 = cast(
        dict[str, Any],
        await flow.async_configure(
            result2["flow_id"],
            user_input={CONFIG_FLOW_IP_ADDRESS: VIRTUAL_LED},
        ),
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_cidr_routes_to_auto_detect(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea.config_flow as cf

    def _get_rb(**_kwargs: Any):  # type: ignore[no-untyped-def]
        return []

    monkeypatch.setattr(cf, "get_reefbeats", _get_rb)
    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: ["192.0.2.0/24"])

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_MANUAL_MODE},
        ),
    )
    assert result2["type"] == FlowResultType.FORM

    result3 = cast(
        dict[str, Any],
        await flow.async_configure(
            result2["flow_id"],
            user_input={CONFIG_FLOW_IP_ADDRESS: "192.0.2.0/24"},
        ),
    )
    result3 = await drive_scan_to_end(hass, result3)
    assert result3["type"] == FlowResultType.FORM
    assert result3.get("errors", {}).get("base") == "nothing_detected"


@pytest.mark.asyncio
async def test_manual_probe_status_false_executes_fallback_path(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import custom_components.redsea.config_flow as cf

    monkeypatch.setattr(cf, "_is_cidr", lambda _s: False)

    def _is_rb(*, ip: str):  # type: ignore[no-untyped-def]
        return (False, ip, None, None, None)

    monkeypatch.setattr(cf, "is_reefbeat", _is_rb)

    def _uuid(*, ip: str):  # type: ignore[no-untyped-def]
        return "uuid-ok"

    monkeypatch.setattr(cf, "get_unique_id", _uuid)

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    result2 = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_ADD_TYPE: ADD_MANUAL_MODE},
        ),
    )
    assert result2["type"] == FlowResultType.FORM

    result3 = cast(
        dict[str, Any],
        await flow.async_configure(
            result2["flow_id"],
            user_input={CONFIG_FLOW_IP_ADDRESS: "192.0.2.10"},
        ),
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["data"][CONFIG_FLOW_HW_MODEL] == ""


@pytest.mark.asyncio
async def test_unknown_submission_aborts_reason_unknown(hass: HomeAssistant) -> None:
    import custom_components.redsea.config_flow as cf

    # Going through the HA flow manager enforces schema validation, so an
    # arbitrary payload would raise InvalidData before our code sees it.
    direct = cf.ReefBeatConfigFlow()
    direct.hass = hass

    result = cast(dict[str, Any], await direct.async_step_user({"x": "y"}))
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown"


@pytest.mark.asyncio
async def test_options_flow_cloud_invalid_credentials_shows_error(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    import custom_components.redsea.config_flow as cf

    async def _invalid(
        hass: HomeAssistant, username: str, password: str, server: str = ""
    ) -> bool:
        return False

    monkeypatch.setattr(cf, "validate_cloud_input", cast(Any, _invalid))

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Cloud",
        data={
            CONFIG_FLOW_IP_ADDRESS: CLOUD_SERVER_ADDR,
            CONFIG_FLOW_HW_MODEL: CLOUD_DEVICE_TYPE,
            CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "pw",
            CONFIG_FLOW_SCAN_INTERVAL: CLOUD_SCAN_INTERVAL,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id="cloud-uid",
    )
    entry.add_to_hass(hass)

    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
                CONFIG_FLOW_CLOUD_PASSWORD: "bad",
                CONFIG_FLOW_SCAN_INTERVAL: CLOUD_SCAN_INTERVAL,
                CONFIG_FLOW_CONFIG_TYPE: False,
            },
        ),
    )
    assert result2["type"] == FlowResultType.FORM
    assert "base" in result2.get("errors", {})


@pytest.mark.asyncio
async def test_options_flow_cloud_valid_credentials_schedules_reload(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    import custom_components.redsea.config_flow as cf

    async def _valid(
        hass: HomeAssistant, username: str, password: str, server: str = ""
    ) -> bool:
        return True

    monkeypatch.setattr(cf, "validate_cloud_input", cast(Any, _valid))

    scheduled: list[str] = []

    def _fake_schedule_reload(entry_id: str) -> None:
        scheduled.append(entry_id)

    monkeypatch.setattr(
        hass.config_entries,
        "async_schedule_reload",
        _fake_schedule_reload,
        raising=True,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Cloud",
        data={
            CONFIG_FLOW_IP_ADDRESS: CLOUD_SERVER_ADDR,
            CONFIG_FLOW_HW_MODEL: CLOUD_DEVICE_TYPE,
            CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "pw",
            CONFIG_FLOW_SCAN_INTERVAL: CLOUD_SCAN_INTERVAL,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id="cloud-uid",
    )
    entry.add_to_hass(hass)

    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert result["type"] == FlowResultType.FORM

    result2 = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
                CONFIG_FLOW_CLOUD_PASSWORD: "pw2",
                CONFIG_FLOW_SCAN_INTERVAL: CLOUD_SCAN_INTERVAL,
                CONFIG_FLOW_CONFIG_TYPE: False,
            },
        ),
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert entry.entry_id in scheduled


async def test_config_flow_cloud_invalid_shows_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea import config_flow as cf

    async def _bad(
        hass: HomeAssistant, username: str, password: str, server: str = ""
    ) -> bool:
        return False

    monkeypatch.setattr(cf, "validate_cloud_input", cast(Any, _bad))

    flow = cast(Any, hass.config_entries.flow)

    result = await flow.async_init(DOMAIN, context={"source": "user"})
    result_dict = cast(dict[str, Any], result)
    assert result_dict["type"] == FlowResultType.FORM

    result2 = await flow.async_configure(
        result_dict["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_CLOUD_API}
    )
    result2_dict = cast(dict[str, Any], result2)
    assert result2_dict["type"] == FlowResultType.FORM

    result3 = await flow.async_configure(
        result2_dict["flow_id"],
        user_input={
            CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "bad",
        },
    )
    result3_dict = cast(dict[str, Any], result3)
    assert result3_dict["type"] == FlowResultType.FORM
    errors = cast(dict[str, Any], result3_dict.get("errors") or {})
    assert errors.get("base")


async def test_config_flow_cloud_creates_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cloud config flow should create an entry when creds validate."""
    from custom_components.redsea import config_flow as cf

    async def _ok(
        hass: HomeAssistant, username: str, password: str, server: str = ""
    ) -> bool:
        return True

    monkeypatch.setattr(cf, "validate_cloud_input", cast(Any, _ok))

    flow = cast(Any, hass.config_entries.flow)

    result = await flow.async_init(DOMAIN, context={"source": "user"})
    result_dict = cast(dict[str, Any], result)
    assert result_dict["type"] == FlowResultType.FORM

    # Step 1: select add type
    result2 = await flow.async_configure(
        result_dict["flow_id"],
        user_input={CONFIG_FLOW_ADD_TYPE: ADD_CLOUD_API},
    )

    result2_dict = cast(dict[str, Any], result2)
    assert result2_dict["type"] == FlowResultType.FORM

    # Step 2: provide cloud credentials
    result3 = await flow.async_configure(
        result2_dict["flow_id"],
        user_input={
            CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "pw",
        },
    )

    result3_dict = cast(dict[str, Any], result3)
    assert result3_dict["type"] == FlowResultType.CREATE_ENTRY
    assert result3_dict["title"]
    # Entry keys are component-defined; just assert username-like value exists.
    assert "test@example.com" in str(result3_dict["data"]).lower()

    # Unload the created entry so its coordinator's Debouncer timer is cancelled.
    entry = cast(Any, result3_dict["result"])
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_options_flow_led_with_intensity_compensation_updates_entry(
    hass: HomeAssistant,
) -> None:
    """Cover options schema for LEDs that support intensity compensation + update branch."""

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My LED",
        data={
            CONFIG_FLOW_IP_ADDRESS: "192.0.2.10",
            CONFIG_FLOW_HW_MODEL: "RSLED160",
            CONFIG_FLOW_SCAN_INTERVAL: 120,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id="led-uid",
    )
    entry.add_to_hass(hass)

    # Local entries with a known hw_model land on the menu first, so pick
    # "settings" to reach the classic form.
    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert result["type"] == FlowResultType.MENU

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"next_step_id": "settings"},
        ),
    )
    assert result["type"] == FlowResultType.FORM

    # Configure with scan interval/options; include intensity compensation.
    result2 = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONFIG_FLOW_SCAN_INTERVAL: 123,
                CONFIG_FLOW_CONFIG_TYPE: True,
                CONFIG_FLOW_INTENSITY_COMPENSATION: True,
            },
        ),
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY

    # MockConfigEntry should reflect updated data.
    assert entry.data[CONFIG_FLOW_SCAN_INTERVAL] == 123
    assert entry.data[CONFIG_FLOW_CONFIG_TYPE] is True
    assert entry.data[CONFIG_FLOW_INTENSITY_COMPENSATION] is True


@pytest.mark.asyncio
async def test_options_flow_missing_hw_model_falls_back_to_generic_schema(
    hass: HomeAssistant,
) -> None:
    """Cover options-flow exception branch when hw_model is missing/invalid."""

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="No model",
        data={
            CONFIG_FLOW_IP_ADDRESS: "192.0.2.11",
            # Missing CONFIG_FLOW_HW_MODEL on purpose
            CONFIG_FLOW_SCAN_INTERVAL: 120,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id="nomodel-uid",
    )
    entry.add_to_hass(hass)

    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert result["type"] == FlowResultType.FORM

    # Only validate that the form is shown; the update path requires hw_model.
    schema = result["data_schema"]
    schema_keys = {str(k) for k in schema.schema}
    assert CONFIG_FLOW_SCAN_INTERVAL in " ".join(schema_keys)
    assert CONFIG_FLOW_CONFIG_TYPE in " ".join(schema_keys)


class ReefLedCoordinator:
    """Stand-in for a loaded G1 lamp (the options flow matches the type name)."""

    def __init__(self, serial: str, model: str) -> None:
        self.serial = serial
        self.model = model


class ReefLedG2Coordinator(ReefLedCoordinator):
    """Stand-in for a loaded G2 lamp."""


class _OtherGroup:
    """Stand-in for another loaded group (a coordinator with member_ids)."""

    def __init__(self, members: list[str]) -> None:
        self.member_ids = members


def _virtual_entry(hass: HomeAssistant, members: list[str]) -> Any:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"{VIRTUAL_LED}-123",
        data={
            CONFIG_FLOW_IP_ADDRESS: VIRTUAL_LED,
            CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
            CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
            CONF_GROUP_MEMBERS: members,
        },
        unique_id="vled-uid",
        minor_version=2,
    )
    entry.add_to_hass(hass)
    return entry


def _options(result: dict[str, Any]) -> dict[str, str]:
    """value -> label of the (single) select field of a group step."""
    field = next(iter(result["data_schema"].schema.values()))
    return {o["value"]: o["label"] for o in field.config["options"]}


@pytest.mark.asyncio
async def test_options_flow_virtual_led_chooses_and_orders_members(
    hass: HomeAssistant,
) -> None:
    """Choose the LEDs of a group, then order them: the order is kept."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["dev1"] = ReefLedCoordinator("S1", "RSLED50")
    hass.data[DOMAIN]["dev2"] = ReefLedG2Coordinator("S2", "RSLED60")
    hass.data[DOMAIN]["dev3"] = ReefLedCoordinator("S3", "RSLED90")
    # dev4 is in another group: not offered
    hass.data[DOMAIN]["dev4"] = ReefLedCoordinator("S4", "RSLED90")
    hass.data[DOMAIN]["other"] = _OtherGroup(["dev4"])
    # A current member not loaded is still offered (with its entry title)
    offline = MockConfigEntry(domain=DOMAIN, title="Offline LED", data={})
    offline.add_to_hass(hass)
    entry = _virtual_entry(hass, ["dev3", offline.entry_id, "gone"])
    # Our own coordinator is loaded too: it must not exclude its members
    hass.data[DOMAIN][entry.entry_id] = _OtherGroup(["dev3"])

    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "group_members"
    labels = _options(result)
    assert labels["dev1"] == "S1 (RSLED50)"
    assert labels["dev2"] == "S2 (RSLED60)"
    assert "dev4" not in labels
    assert labels[offline.entry_id] == "Offline LED (?)"
    assert labels["gone"] == "gone (?)"

    # Fewer than two LEDs: refused
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_GROUP_MEMBERS: ["dev1"]}
        ),
    )
    assert result["errors"] == {"base": "group_min_members"}

    # Kept members keep their order, new ones come last
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_GROUP_MEMBERS: ["dev1", "dev3"]}
        ),
    )
    assert result["step_id"] == "group_order"
    keys = [str(k) for k in result["data_schema"].schema]
    assert keys == ["position_1", "position_2"]
    defaults = [k.default() for k in result["data_schema"].schema]
    assert defaults == ["dev3", "dev1"]

    # The same LED twice: refused, the form shows the order given
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"position_1": "dev1", "position_2": "dev1"},
        ),
    )
    assert result["errors"] == {"base": "group_duplicate_position"}
    defaults = [k.default() for k in result["data_schema"].schema]
    assert defaults == ["dev1", "dev1"]

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"position_1": "dev1", "position_2": "dev3"},
        ),
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_GROUP_MEMBERS] == ["dev1", "dev3"]
    assert entry.data[CONFIG_FLOW_HW_MODEL] == VIRTUAL_LED


async def test_config_flow_cloud_server_with_simulator_flag(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """With the local flag file the cloud server can be a simulator's."""
    from custom_components.redsea import config_flow as cf
    from custom_components.redsea.const import CONFIG_FLOW_CLOUD_SERVER

    servers: list[str] = []

    async def _check(
        hass: HomeAssistant, username: str, password: str, server: str = ""
    ) -> bool:
        servers.append(server)
        return password == "pw"

    monkeypatch.setattr(cf, "validate_cloud_input", cast(Any, _check))
    flag = tmp_path / ".simulator_enabled"
    flag.write_text("")
    monkeypatch.setattr(cf, "_SIM_FLAG", flag)
    flow = cast(Any, hass.config_entries.flow)

    result = await flow.async_init(DOMAIN, context={"source": "user"})
    result2 = await flow.async_configure(
        result["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_CLOUD_API}
    )
    fields = [str(key) for key in result2["data_schema"].schema]
    assert CONFIG_FLOW_CLOUD_SERVER in fields

    # Refused: the form comes back with the server typed
    result3 = await flow.async_configure(
        result2["flow_id"],
        user_input={
            CONFIG_FLOW_CLOUD_USERNAME: "sim@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "bad",
            CONFIG_FLOW_CLOUD_SERVER: " 192.0.2.251 ",
        },
    )
    assert result3["errors"] == {"base": "auth_failed"}
    defaults = {str(key): key.default() for key in result3["data_schema"].schema}
    assert defaults[CONFIG_FLOW_CLOUD_SERVER] == "192.0.2.251"

    result4 = await flow.async_configure(
        result3["flow_id"],
        user_input={
            CONFIG_FLOW_CLOUD_USERNAME: "sim@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "pw",
            CONFIG_FLOW_CLOUD_SERVER: "192.0.2.251",
        },
    )
    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert servers == ["192.0.2.251", "192.0.2.251"]
    assert result4["data"][CONFIG_FLOW_IP_ADDRESS] == "192.0.2.251"
    assert CONFIG_FLOW_CLOUD_SERVER not in result4["data"]
    entry = cast(Any, result4["result"])
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_config_flow_cloud_server_hidden_by_default(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Without the flag file, even in advanced mode: the real cloud only."""
    from custom_components.redsea import config_flow as cf

    monkeypatch.setattr(cf, "_SIM_FLAG", tmp_path / ".simulator_enabled")
    flow = cast(Any, hass.config_entries.flow)
    result = await flow.async_init(
        DOMAIN, context={"source": "user", "show_advanced_options": True}
    )
    result2 = await flow.async_configure(
        result["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_CLOUD_API}
    )
    fields = [str(key) for key in result2["data_schema"].schema]
    assert fields == [CONFIG_FLOW_CLOUD_USERNAME, CONFIG_FLOW_CLOUD_PASSWORD]


class ReefBeatCloudCoordinator:
    """Stand-in for a loaded cloud account (matched by its type name)."""

    def __init__(self, devices: list[dict[str, Any]]) -> None:
        self.devices = devices

    def get_data(self, _name: str, _none: bool = False) -> Any:
        return self.devices


@pytest.mark.asyncio
async def test_options_flow_new_group_starts_with_the_app_group(
    hass: HomeAssistant,
) -> None:
    """A new virtual LED proposes the lamps grouped in the ReefBeat app."""
    hass.data.setdefault(DOMAIN, {})
    for n in (1, 2, 3):
        led = ReefLedCoordinator(f"S{n}", "RSLED160")
        led.model_id = f"h{n}"  # type: ignore[attr-defined]
        hass.data[DOMAIN][f"dev{n}"] = led

    def device(hwid: str, grouped: bool, index: int = 0) -> dict[str, Any]:
        return {
            "hwid": hwid,
            "model": "RSLED160",
            "aquarium_uid": "aq",
            "grouped": grouped,
            "group_index": index,
        }

    hass.data[DOMAIN]["cloud"] = ReefBeatCloudCoordinator(
        [
            device("h1", True, 1),
            device("h3", True, 0),
            device("h2", False),
            device("unknown", True),
        ]
    )
    # Another account with a group of one lamp: not enough for a group
    hass.data[DOMAIN]["cloud2"] = ReefBeatCloudCoordinator([device("h2", True)])
    entry = _virtual_entry(hass, [])
    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    field = next(iter(result["data_schema"].schema))
    assert field.default() == ["dev3", "dev1"]
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_GROUP_MEMBERS: ["dev1", "dev3"]}
        ),
    )
    # In the app's order
    assert [k.default() for k in result["data_schema"].schema] == ["dev3", "dev1"]

    # Nothing grouped in the app: nothing proposed
    hass.data[DOMAIN]["cloud"] = ReefBeatCloudCoordinator(None)  # type: ignore[arg-type]
    del hass.data[DOMAIN]["cloud2"]
    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert next(iter(result["data_schema"].schema)).default() == []


class _AppGroups:
    """Stand-in for a loaded cloud account listing the groups of the app."""

    def __init__(self, groups: dict[tuple[str, str], list[str]]) -> None:
        self.groups = groups

    def app_groups(self) -> dict[tuple[str, str], list[str]]:
        return self.groups


def _discovery(members: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "aquarium_uid": "aq",
        "aquarium": "Reef",
        "model": "RSLED160",
        CONF_GROUP_MEMBERS: members,
        **extra,
    }


@pytest.mark.asyncio
async def test_discovered_group_creates_its_virtual_led(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A group of the ReefBeat app is proposed; confirmed, its virtual LED
    is made of the lamps the cloud lists then (in the app's order)."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    import custom_components.redsea as integration

    async def _setup(*_a: Any) -> bool:
        return True

    monkeypatch.setattr(integration, "async_setup_entry", _setup)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["dev1"] = ReefLedCoordinator("S1", "RSLED160")
    MockConfigEntry(domain=DOMAIN, title="Lamp 2", entry_id="dev2").add_to_hass(hass)

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any],
        await flow.async_init(
            DOMAIN,
            context={"source": "integration_discovery"},
            data=_discovery(["dev1", "dev2", "gone"]),
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    placeholders = result["description_placeholders"]
    assert placeholders["model"] == "RSLED160"
    assert placeholders["aquarium"] == "Reef"
    # Loaded lamp, lamp not loaded (its entry title), unknown lamp
    assert placeholders["leds"] == "1. S1 (RSLED160)\n2. Lamp 2\n3. gone"
    progress = flow.async_progress()
    assert progress[0]["context"]["title_placeholders"] == {
        "name": f"{VIRTUAL_LED} RSLED160 × 3"
    }
    # The same group again: already proposed
    again = cast(
        dict[str, Any],
        await flow.async_init(
            DOMAIN,
            context={"source": "integration_discovery"},
            data=_discovery(["dev1", "dev2"]),
        ),
    )
    assert again["type"] == FlowResultType.ABORT

    # The cloud now lists the group in another order
    hass.data[DOMAIN]["cloud"] = _AppGroups({("aq", "RSLED160"): ["dev2", "dev1"]})
    hass.data[DOMAIN]["other"] = _AppGroups({})
    done = cast(
        dict[str, Any], await flow.async_configure(result["flow_id"], user_input={})
    )
    assert done["type"] == FlowResultType.CREATE_ENTRY
    assert done["title"].startswith(f"{VIRTUAL_LED}-")
    assert done["data"] == {
        CONFIG_FLOW_IP_ADDRESS: done["title"],
        CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
        CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
        CONF_GROUP_MEMBERS: ["dev2", "dev1"],
    }
    # Its virtual LED exists: not proposed again
    result = cast(
        dict[str, Any],
        await flow.async_init(
            DOMAIN,
            context={"source": "integration_discovery"},
            data=_discovery(["dev1", "dev2"]),
        ),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "info",
    [
        _discovery(["dev1"]),
        _discovery("dev1"),  # type: ignore[arg-type]
        _discovery(["dev1", "dev2"], model=""),
        _discovery(["dev1", "dev2"], aquarium_uid=None),
    ],
)
async def test_discovered_group_unusable(
    hass: HomeAssistant, info: dict[str, Any]
) -> None:
    result = cast(
        dict[str, Any],
        await cast(Any, hass.config_entries.flow).async_init(
            DOMAIN, context={"source": "integration_discovery"}, data=info
        ),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "cannot_create"


@pytest.mark.asyncio
async def test_discovered_group_taken_meanwhile(hass: HomeAssistant) -> None:
    """A lamp of the group went in a virtual LED made meanwhile, or the
    group lost its lamps: nothing is created."""
    hass.data.setdefault(DOMAIN, {})
    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any],
        await flow.async_init(
            DOMAIN,
            context={"source": "integration_discovery"},
            data=_discovery(["dev1", "dev2"]),
        ),
    )
    _virtual_entry(hass, ["dev2", "dev9"])
    done = cast(
        dict[str, Any], await flow.async_configure(result["flow_id"], user_input={})
    )
    assert done["type"] == FlowResultType.ABORT
    assert done["reason"] == "group_already_driven"

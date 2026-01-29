from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

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
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_SCAN_INTERVAL,
    DOMAIN,
    DOSE_SCAN_INTERVAL,
    HW_ATO_IDS,
    HW_DOSE_IDS,
    HW_LED_IDS,
    HW_MAT_IDS,
    HW_RUN_IDS,
    LED_SCAN_INTERVAL,
    LINKED_LED,
    MAT_SCAN_INTERVAL,
    RUN_SCAN_INTERVAL,
    SCAN_INTERVAL,
    VIRTUAL_LED,
    VIRTUAL_LED_SCAN_INTERVAL,
)


def test_scan_interval_helpers() -> None:
    # Cover all get_scan_interval branches.
    assert get_scan_interval(next(iter(HW_DOSE_IDS))) == DOSE_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_MAT_IDS))) == MAT_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_ATO_IDS))) == ATO_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_LED_IDS))) == LED_SCAN_INTERVAL
    assert get_scan_interval(next(iter(HW_RUN_IDS))) == RUN_SCAN_INTERVAL
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

        async def __aenter__(self) -> "_Resp":
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

    def _get_rb(*, subnetwork: str | None = None):  # type: ignore[no-untyped-def]
        return devices

    monkeypatch.setattr(cf, "get_reefbeats", _get_rb)

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

    assert result2["type"] == FlowResultType.FORM
    # Should include VIRTUAL_LED and exclude already-configured device
    assert "192.0.2.10" not in str(result2.get("data_schema"))


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

    def _get_rb(*, subnetwork: str | None = None):  # type: ignore[no-untyped-def]
        return []

    monkeypatch.setattr(cf, "get_reefbeats", _get_rb)

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
    assert result3["type"] == FlowResultType.FORM


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

    async def _invalid(hass: HomeAssistant, username: str, password: str) -> bool:
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

    async def _valid(hass: HomeAssistant, username: str, password: str) -> bool:
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

    async def _bad(hass: HomeAssistant, username: str, password: str) -> bool:
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

    async def _ok(hass: HomeAssistant, username: str, password: str) -> bool:
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

    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
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
    schema_keys = {str(k) for k in schema.schema.keys()}
    assert CONFIG_FLOW_SCAN_INTERVAL in " ".join(schema_keys)
    assert CONFIG_FLOW_CONFIG_TYPE in " ".join(schema_keys)


@pytest.mark.asyncio
async def test_options_flow_virtual_led_builds_leds_schema_and_links_enabled_leds(
    hass: HomeAssistant,
) -> None:
    """Cover virtual LED options schema creation (iterating hass.data) + linking update."""

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Populate hass.data with fake LED coordinators whose type names match.
    class ReefLedCoordinator:
        def __init__(self, serial: str, model: str) -> None:
            self.serial = serial
            self.model = model

    class ReefLedG2Coordinator:
        def __init__(self, serial: str, model: str) -> None:
            self.serial = serial
            self.model = model

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["dev1"] = ReefLedCoordinator("S1", "RSLED50")
    hass.data[DOMAIN]["dev2"] = ReefLedG2Coordinator("S2", "RSLED60")

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"{VIRTUAL_LED}-123",
        data={
            CONFIG_FLOW_IP_ADDRESS: VIRTUAL_LED,
            CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
            CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
            LINKED_LED: {},
        },
        unique_id="vled-uid",
    )
    entry.add_to_hass(hass)

    result = cast(
        dict[str, Any], await hass.config_entries.options.async_init(entry.entry_id)
    )
    assert result["type"] == FlowResultType.FORM

    # Extract the keys from the schema; should include our LED devices.
    schema = result["data_schema"]
    schema_keys = list(schema.schema.keys())
    assert any("LED-RSLED50" in str(k) for k in schema_keys)
    assert any("LED-RSLED60" in str(k) for k in schema_keys)

    # Configure linking: enable only the first.
    led1_key = next(k for k in schema_keys if "LED-RSLED50" in str(k))
    led2_key = next(k for k in schema_keys if "LED-RSLED60" in str(k))

    result2 = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                str(led1_key): True,
                str(led2_key): False,
            },
        ),
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY

    # Entry should get the linked LED mapping with only the enabled one.
    linked = cast(dict[str, Any], entry.data[LINKED_LED])
    assert len(linked) == 1

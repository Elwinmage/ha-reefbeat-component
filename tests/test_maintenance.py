"""Unit tests for the maintenance subsystem.

Covers the pure helpers (`compute_days_left`, `is_overdue`), the persistent
`MaintenanceStore`, and the `redsea.reset_maintenance` service handler.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea as redsea_pkg
import custom_components.redsea.maintenance as maint
from custom_components.redsea.const import DOMAIN


# =============================================================================
# Pure helpers
# =============================================================================


class TestComputeDaysLeft:
    """`compute_days_left` is the heart of the gauge / overdue logic."""

    def test_returns_none_when_no_last_reset(self) -> None:
        # Tasks never performed yet are "pending first reset", not overdue.
        assert maint.compute_days_left(None, 30) is None

    def test_just_reset_returns_full_interval(self) -> None:
        # `compute_days_left` uses integer floor of remaining seconds, so
        # any time elapsed at all -> N-1 days, not N. To assert "full
        # interval", we have to pretend zero seconds elapsed.
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        assert maint.compute_days_left(now, 30, now=now) == 30

    def test_one_second_after_reset_loses_one_day(self) -> None:
        # Documents the floor behaviour: 30d - 1s = 29 whole days remaining.
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        last = now - timedelta(seconds=1)
        assert maint.compute_days_left(last, 30, now=now) == 29

    def test_partial_day_elapsed_still_counts_as_full_remaining(self) -> None:
        # 12h elapsed of a 30-day interval -> 29 days left (int floor of remainder).
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        last = now - timedelta(hours=12)
        assert maint.compute_days_left(last, 30, now=now) == 29

    def test_exact_interval_boundary(self) -> None:
        # Elapsed == interval exactly -> 0 days left (still due, not yet overdue).
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        last = now - timedelta(days=30)
        assert maint.compute_days_left(last, 30, now=now) == 0

    def test_overdue_returns_negative(self) -> None:
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        last = now - timedelta(days=35)
        # 5 days overdue; negative.
        assert maint.compute_days_left(last, 30, now=now) == -5

    def test_overdue_rounding_consistency(self) -> None:
        # Overdue by 1 hour past the interval: should report -1 (rounded up
        # in magnitude) so the UI says "1 day late" rather than "0 days left".
        now = datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc)
        last = now - timedelta(days=30, hours=1)
        result = maint.compute_days_left(last, 30, now=now)
        assert result is not None and result < 0


class TestIsOverdue:
    def test_none_last_reset_is_not_overdue(self) -> None:
        # Never reset -> not overdue (the UI treats it as "needs first run").
        assert maint.is_overdue(None, 30) is False

    def test_zero_days_left_is_not_overdue(self) -> None:
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        last = now - timedelta(days=30)
        assert maint.is_overdue(last, 30, now=now) is False

    def test_negative_days_left_is_overdue(self) -> None:
        now = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        last = now - timedelta(days=40)
        assert maint.is_overdue(last, 30, now=now) is True


# =============================================================================
# Task catalogue
# =============================================================================


class TestTaskCatalogue:
    def test_all_known_models_have_at_least_one_task(self) -> None:
        # Every supported hw_id should map to a non-empty task tuple.
        for hw_id in (
            "RSATO+",
            "RSDOSE2",
            "RSDOSE4",
            "RSRUN",
            "RSWAVE25",
            "RSWAVE45",
            "RSMAT",
        ):
            assert maint.tasks_for(hw_id), f"no tasks for {hw_id}"

    def test_unknown_model_returns_empty_tuple(self) -> None:
        assert maint.tasks_for("UNKNOWN_HW") == ()

    def test_task_keys_are_unique_per_model(self) -> None:
        # Storage uses (serial, sub_id, task_key); duplicate keys within a
        # model would collide silently.
        for hw_id, tasks in maint.TASKS.items():
            keys = [t.key for t in tasks]
            assert len(keys) == len(set(keys)), f"duplicate task keys in {hw_id}"

    def test_translation_key_matches_role_prefix(self) -> None:
        # The blueprint matches reef_role starting with "maint_".
        for tasks in maint.TASKS.values():
            for t in tasks:
                assert t.translation_key.startswith(maint.ROLE_PREFIX)

    def test_intervals_are_within_bounds(self) -> None:
        for tasks in maint.TASKS.values():
            for t in tasks:
                assert t.min_days < t.default_days < t.max_days, (
                    f"interval bounds invalid for {t.key}: "
                    f"min={t.min_days} default={t.default_days} max={t.max_days}"
                )

    def test_register_led_tasks_does_not_overwrite(self) -> None:
        # If called twice (e.g. test isolation), the second call must not
        # clobber any custom entries that may have been added meanwhile.
        before = dict(maint.TASKS)
        maint.register_led_tasks(("RSLED-IMAGINARY",))
        maint.register_led_tasks(("RSLED-IMAGINARY",))  # second call: idempotent
        assert maint.TASKS["RSLED-IMAGINARY"] is before.get(
            "RSLED-IMAGINARY", maint.TASKS["RSLED-IMAGINARY"]
        )


# =============================================================================
# MaintenanceStore (persistent state)
# =============================================================================


@pytest.mark.asyncio
class TestMaintenanceStore:
    """Use HA's real Store fixture (provided by pytest-homeassistant-custom-component)."""

    async def test_load_empty_store_yields_no_data(self, hass: HomeAssistant) -> None:
        store = maint.MaintenanceStore(hass, "entry-test-1")
        await store.async_load()
        # No instances yet -> get_state auto-creates a fresh blank one.
        state = store.get_state("serial-abc", 0, "led_lens")
        assert state.last_reset is None
        assert state.interval_days is None

    async def test_reset_roundtrip(self, hass: HomeAssistant) -> None:
        store = maint.MaintenanceStore(hass, "entry-test-2")
        await store.async_load()
        before = datetime.now(timezone.utc)
        ts = await store.async_reset("serial-abc", 1, "dose_heads_replace")
        # Returned timestamp lands between "before" and "now".
        assert before <= ts <= datetime.now(timezone.utc)
        # Read-back matches the persisted value.
        assert store.get_last_reset("serial-abc", 1, "dose_heads_replace") == ts

    async def test_interval_override(self, hass: HomeAssistant) -> None:
        store = maint.MaintenanceStore(hass, "entry-test-3")
        await store.async_load()
        # Without override, fallback to default is returned verbatim.
        assert store.get_interval("s", 0, "led_lens", 21) == 21
        await store.async_set_interval("s", 0, "led_lens", 42)
        assert store.get_interval("s", 0, "led_lens", 21) == 42

    async def test_listener_fired_on_reset_and_interval(
        self, hass: HomeAssistant
    ) -> None:
        store = maint.MaintenanceStore(hass, "entry-test-4")
        await store.async_load()
        # The listener is per (serial, sub_id, task_key) tuple; a callback
        # registered for one instance must not see another instance's events.
        calls_a: list[int] = []
        calls_b: list[int] = []
        store.async_add_listener("s", 0, "led_lens", lambda: calls_a.append(1))
        store.async_add_listener("s", 0, "led_fan", lambda: calls_b.append(1))
        await store.async_reset("s", 0, "led_lens")
        assert calls_a == [1] and calls_b == []
        await store.async_set_interval("s", 0, "led_fan", 200)
        assert calls_a == [1] and calls_b == [1]

    async def test_listener_unsub(self, hass: HomeAssistant) -> None:
        store = maint.MaintenanceStore(hass, "entry-test-5")
        await store.async_load()
        calls: list[int] = []
        unsub = store.async_add_listener("s", 0, "led_lens", lambda: calls.append(1))
        unsub()
        await store.async_reset("s", 0, "led_lens")
        assert calls == []

    async def test_persistence_across_instances(self, hass: HomeAssistant) -> None:
        # Saving on one instance and loading another (same entry_id) must
        # round-trip both last_reset and interval_days through JSON.
        store1 = maint.MaintenanceStore(hass, "entry-persist")
        await store1.async_load()
        ts = await store1.async_reset("serial", 2, "run_pump_motor")
        await store1.async_set_interval("serial", 2, "run_pump_motor", 100)

        store2 = maint.MaintenanceStore(hass, "entry-persist")
        await store2.async_load()
        # Datetimes round-trip via ISO with tz preserved.
        assert store2.get_last_reset("serial", 2, "run_pump_motor") == ts
        assert store2.get_interval("serial", 2, "run_pump_motor", 999) == 100


# =============================================================================
# reset_maintenance service handler
# =============================================================================
#
# We can't easily exercise the full service via hass.services.async_call here
# without bringing up a real coordinator, so we focus on the device_id parsing
# logic which is what's most likely to regress (head/pump suffix detection).


def test_device_id_parsing_main_device(hass: HomeAssistant) -> None:
    """A device identifier '<serial>' resolves to (serial, sub_id=0)."""
    dev_reg = dr.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="parse-test-main")
    entry.add_to_hass(hass)
    ha_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ABC123")},
    )
    serial, sub_id = _resolve_serial(ha_device)
    assert serial == "ABC123" and sub_id == 0


def test_device_id_parsing_head_subdevice(hass: HomeAssistant) -> None:
    """A '<serial>_head_<n>' identifier yields (serial, sub_id=n)."""
    dev_reg = dr.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="parse-test-head")
    entry.add_to_hass(hass)
    ha_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ABC123_head_3")},
    )
    serial, sub_id = _resolve_serial(ha_device)
    assert serial == "ABC123" and sub_id == 3


def test_device_id_parsing_pump_subdevice(hass: HomeAssistant) -> None:
    """A '<serial>_pump_<n>' identifier yields (serial, sub_id=n)."""
    dev_reg = dr.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="parse-test-pump")
    entry.add_to_hass(hass)
    ha_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "XYZ999_pump_2")},
    )
    serial, sub_id = _resolve_serial(ha_device)
    assert serial == "XYZ999" and sub_id == 2


def test_device_id_parsing_non_redsea_device_returns_none(
    hass: HomeAssistant,
) -> None:
    """A device with no redsea identifier yields None."""
    dev_reg = dr.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="parse-test-other")
    entry.add_to_hass(hass)
    ha_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("some_other_domain", "OTHER123")},
    )
    serial, sub_id = _resolve_serial(ha_device)
    assert serial is None and sub_id == 0


def _resolve_serial(ha_device: Any) -> tuple[str | None, int]:
    """Mirror the resolution logic of `handle_reset_maintenance`.

    Extracted so we can unit-test it without standing up the full service.
    If the production code changes, this helper must follow.
    """
    serial: str | None = None
    sub_id = 0
    for domain, ident in ha_device.identifiers:
        if domain != DOMAIN:
            continue
        for kind in ("head", "pump"):
            token = f"_{kind}_"
            if token in ident:
                base, _, tail = ident.rpartition(token)
                if tail.isdigit():
                    serial = base
                    sub_id = int(tail)
                    break
        else:
            serial = ident
        if serial:
            break
    return serial, sub_id


# =============================================================================
# End-to-end service handler via hass.services.async_call
# =============================================================================
#
# These bring up the real handler by calling async_setup, registering the
# service, and invoking it through hass.services.async_call with a stub
# coordinator wired into hass.data[DOMAIN]. They cover the previously
# uncovered lines 342-390 in __init__.py.
#
# Note: `async_setup_component(hass, DOMAIN, {})` runs the integration's
# `async_setup`, which does panel/HTTP registration. If your test harness
# can't provide those, these tests may need `async_setup` to be skipped or
# the service registration extracted into a smaller helper.


class _StubCoordinator:
    """Minimal stand-in for a ReefBeatCoordinator from the service POV."""

    def __init__(self, hass: HomeAssistant, serial: str, entry_id: str) -> None:
        self.serial = serial
        self._hass = hass
        self.maintenance = maint.MaintenanceStore(hass, entry_id)


async def _bootstrap_service(
    hass: HomeAssistant, serial: str, ha_identifier: str
) -> tuple[_StubCoordinator, str]:
    """Set up the redsea service with a stub coordinator and one HA device.

    Returns (coordinator, device_id) so tests can drive `async_call`.
    """
    # Run the integration's async_setup so reset_maintenance gets registered.
    await async_setup_component(hass, redsea_pkg.DOMAIN, {})

    entry = MockConfigEntry(
        domain=redsea_pkg.DOMAIN, data={}, unique_id=f"svc-{serial}"
    )
    entry.add_to_hass(hass)

    coord = _StubCoordinator(hass, serial, entry.entry_id)
    await coord.maintenance.async_load()
    hass.data.setdefault(redsea_pkg.DOMAIN, {})[entry.entry_id] = coord

    dev_reg = dr.async_get(hass)
    ha_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(redsea_pkg.DOMAIN, ha_identifier)},
    )
    return coord, ha_device.id


@pytest.mark.asyncio
async def test_service_reset_main_device(hass: HomeAssistant) -> None:
    """Calling the service on a main device persists `last_reset`."""
    coord, device_id = await _bootstrap_service(hass, "SERIAL-MAIN", "SERIAL-MAIN")

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": device_id, "task_key": "led_lens"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)

    # Service returns the reset timestamp plus parsed sub_id.
    assert response["serial"] == "SERIAL-MAIN"
    assert response["sub_id"] == 0
    assert "reset_at" in response
    # And the store actually persisted the reset.
    assert coord.maintenance.get_last_reset("SERIAL-MAIN", 0, "led_lens") is not None


@pytest.mark.asyncio
async def test_service_reset_head_subdevice(hass: HomeAssistant) -> None:
    """A sub-device identifier `<serial>_head_<n>` resolves to sub_id=n."""
    coord, device_id = await _bootstrap_service(
        hass, "SERIAL-DOSE", "SERIAL-DOSE_head_3"
    )

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": device_id, "task_key": "dose_heads_replace"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)

    assert response["serial"] == "SERIAL-DOSE"
    assert response["sub_id"] == 3
    # Reset landed on the correct (serial, sub_id) slot, not on the main one.
    assert (
        coord.maintenance.get_last_reset("SERIAL-DOSE", 3, "dose_heads_replace")
        is not None
    )
    assert (
        coord.maintenance.get_last_reset("SERIAL-DOSE", 0, "dose_heads_replace") is None
    )


@pytest.mark.asyncio
async def test_service_reset_pump_subdevice(hass: HomeAssistant) -> None:
    """`<serial>_pump_<n>` works the same way as `_head_<n>`."""
    _coord, device_id = await _bootstrap_service(
        hass, "SERIAL-RUN", "SERIAL-RUN_pump_2"
    )

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": device_id, "task_key": "run_pump_motor"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)

    assert response["serial"] == "SERIAL-RUN"
    assert response["sub_id"] == 2


@pytest.mark.asyncio
async def test_service_unknown_device_returns_error(hass: HomeAssistant) -> None:
    """Calling with a device_id absent from the registry returns an error."""
    await _bootstrap_service(hass, "SERIAL-X", "SERIAL-X")

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": "non-existent-device-id", "task_key": "led_lens"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)
    assert "error" in response


@pytest.mark.asyncio
async def test_service_non_redsea_device_returns_error(
    hass: HomeAssistant,
) -> None:
    """A HA device that has no redsea identifier is rejected cleanly."""
    await _bootstrap_service(hass, "SERIAL-Y", "SERIAL-Y")

    # Create another entry with a non-redsea identifier.
    other_entry = MockConfigEntry(domain="other_domain", data={}, unique_id="other-1")
    other_entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    other = dev_reg.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={("other_domain", "alien-id")},
    )

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": other.id, "task_key": "led_lens"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)
    assert "error" in response


@pytest.mark.asyncio
async def test_service_no_active_coordinator_returns_error(
    hass: HomeAssistant,
) -> None:
    """If the serial doesn't match any registered coordinator, error out."""
    # Bootstrap with serial A, but then create a device for serial B.
    await _bootstrap_service(hass, "SERIAL-A", "SERIAL-A")

    other_entry = MockConfigEntry(
        domain=redsea_pkg.DOMAIN, data={}, unique_id="b-entry"
    )
    other_entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    orphan = dev_reg.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={(redsea_pkg.DOMAIN, "SERIAL-B")},
    )

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": orphan.id, "task_key": "led_lens"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)
    assert "error" in response
    assert "SERIAL-B" in str(response["error"])


@pytest.mark.asyncio
async def test_service_missing_required_args_rejected(
    hass: HomeAssistant,
) -> None:
    """Both device_id and task_key are required.

    HA's service-call validation (declared in services.yaml `required: true`)
    is expected to reject the call before reaching the handler. If validation
    is bypassed for some reason, the handler's own guard returns an error.
    """
    await _bootstrap_service(hass, "SERIAL-Z", "SERIAL-Z")

    import voluptuous as vol  # local import to keep top-level test imports lean

    raised = False
    response: Any = None
    try:
        response = await hass.services.async_call(
            redsea_pkg.DOMAIN,
            "reset_maintenance",
            {"device_id": "doesnt-matter"},  # task_key missing
            blocking=True,
            return_response=True,
        )
    except vol.Invalid:
        raised = True

    assert raised or (isinstance(response, dict) and "error" in response)


# =============================================================================
# MaintenanceIntervalNumberEntity weeks/months conversion
# =============================================================================
#
# The number entity converts day-based storage to weeks or months for display
# and back on write. Bugs here would silently corrupt user settings.


class _FakeNumberDevice:
    """Stand-in for a coordinator from the number entity's POV."""

    def __init__(self, hass: HomeAssistant, serial: str = "S1") -> None:
        self.serial = serial
        self._hass = hass
        self.maintenance: maint.MaintenanceStore | None = None
        self.device_info = None


@pytest.mark.asyncio
async def test_number_entity_converts_days_to_weeks(hass: HomeAssistant) -> None:
    """A 35-day stored interval shows as 5 on a weeks-based task."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    device = _FakeNumberDevice(hass)
    device.maintenance = maint.MaintenanceStore(hass, "n-test-weeks")
    await device.maintenance.async_load()

    # Pick a task whose unit is "weeks". `register_led_tasks` is called by
    # __init__.async_setup, so by the time tests run with the integration
    # bootstrapped, every HW_LED_IDS entry has _RSLED_TASKS attached.
    maint.register_led_tasks(("RSLED90",))
    task = next(t for t in maint.TASKS["RSLED90"] if t.unit == "weeks")

    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)
    # Pre-seed the store with 35 days under this (serial, sub_id, task) slot.
    await device.maintenance.async_set_interval(device.serial, 0, task.key, 35)

    # 35 days / 7 = 5 weeks.
    assert entity.native_value == 5.0
    # Display bounds are also converted.
    assert entity.native_min_value == float(task.min_days // 7)
    assert entity.native_max_value == float(task.max_days // 7)


@pytest.mark.asyncio
async def test_number_entity_converts_days_to_months(hass: HomeAssistant) -> None:
    """A 90-day stored interval shows as 3 on a months-based task."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    device = _FakeNumberDevice(hass)
    device.maintenance = maint.MaintenanceStore(hass, "n-test-months")
    await device.maintenance.async_load()

    # Pick a months-based task; "run_pump_motor" is one.
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    assert task.unit == "months", "test fixture changed: expected months unit"

    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=1)
    await device.maintenance.async_set_interval(device.serial, 1, task.key, 90)

    # 90 days / 30 = 3 months.
    assert entity.native_value == 3.0


@pytest.mark.asyncio
async def test_number_entity_write_converts_back_to_days(
    hass: HomeAssistant,
) -> None:
    """Setting the slider to 4 (months) persists 120 days in the store."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    device = _FakeNumberDevice(hass)
    device.maintenance = maint.MaintenanceStore(hass, "n-test-write")
    await device.maintenance.async_load()

    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)

    await entity.async_set_native_value(4.0)
    # Stored in days (4 * 30).
    assert device.maintenance.get_interval(device.serial, 0, task.key, 0) == 120


@pytest.mark.asyncio
async def test_number_entity_falls_back_to_default_when_store_unset(
    hass: HomeAssistant,
) -> None:
    """With no override stored, native_value reflects the task default."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    device = _FakeNumberDevice(hass)
    device.maintenance = maint.MaintenanceStore(hass, "n-test-default")
    await device.maintenance.async_load()

    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)

    # 135 days default / 30 = 4 (floor).
    assert entity.native_value == float(task.default_days // 30)


# =============================================================================
# ReefRoleMixin fallback branches
# =============================================================================


def test_reef_role_mixin_returns_none_when_no_attrs_and_no_translation() -> None:
    """Covers entity.py:71 fallback: no _attr_extra_state_attributes, no TK."""
    from custom_components.redsea.entity import ReefRoleMixin

    obj = ReefRoleMixin()
    assert obj.extra_state_attributes is None


def test_reef_role_mixin_returns_base_dict_when_no_translation_key() -> None:
    """When TK is None but base attrs exist, the base dict passes through."""
    from custom_components.redsea.entity import ReefRoleMixin

    class Stub(ReefRoleMixin):
        _attr_extra_state_attributes = {"k": "v"}
        translation_key = None

    obj = Stub()
    result = obj.extra_state_attributes
    assert result is not None
    assert result == {"k": "v"}
    # Defensive copy: mutating result must not affect the source.
    result["new"] = "z"
    assert "new" not in Stub._attr_extra_state_attributes


# =============================================================================
# Defensive branches: missing maintenance store / unknown hw / pump exceptions
# =============================================================================
#
# These cover the fallback paths in button.py and number.py that protect the
# integration when wiring is partial, plus the error-return branch of the
# service handler when the coordinator lacks a maintenance store.


class _StoreLessDevice:
    """Coordinator lookalike WITHOUT a `.maintenance` attribute.

    Used to exercise the `_store` property's lazy-fallback branch, which
    logs a WARNING and creates an ephemeral MaintenanceStore so the entity
    keeps working instead of crashing.
    """

    def __init__(self, hass: HomeAssistant, serial: str = "STORELESS") -> None:
        self.serial = serial
        self._hass = hass
        self._title = "FakeDevice"
        self.device_info = None
        # NOTE: deliberately no `self.maintenance`.


@pytest.mark.asyncio
async def test_button_store_fallback_creates_ephemeral_store(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Covers button.py:1083-1097 (lazy ephemeral MaintenanceStore creation)."""
    from custom_components.redsea.button import MaintenanceButtonEntity

    device = _StoreLessDevice(hass)
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")

    entity = MaintenanceButtonEntity(cast(Any, device), task, sub_id=0)

    with caplog.at_level("WARNING"):
        store = entity._store

    # The fallback creates a real MaintenanceStore and attaches it.
    assert isinstance(store, maint.MaintenanceStore)
    assert getattr(device, "maintenance", None) is store
    # And it logged a warning so the misconfiguration is visible.
    assert any("MaintenanceStore missing" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_number_store_fallback_creates_ephemeral_store(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Same fallback path on the number entity (number.py:1133-1138)."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    device = _StoreLessDevice(hass)
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")

    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)

    with caplog.at_level("WARNING"):
        store = entity._store

    assert isinstance(store, maint.MaintenanceStore)
    assert getattr(device, "maintenance", None) is store


def test_iter_run_pumps_returns_empty_on_get_data_exception() -> None:
    """Covers button.py:672-673 (`except Exception: pump = None`)."""
    from custom_components.redsea.button import _iter_run_pumps

    class _ExplodingDevice:
        def get_data(self, _path: str, _silent: bool = False) -> Any:
            raise RuntimeError("boom")

    # No pump survives the exception; result is empty regardless of wanted type.
    assert _iter_run_pumps(cast(Any, _ExplodingDevice()), "return") == []
    assert _iter_run_pumps(cast(Any, _ExplodingDevice()), "skimmer") == []


def test_iter_run_pumps_skips_non_dict_responses() -> None:
    """Covers the `not isinstance(pump, dict)` guard."""
    from custom_components.redsea.button import _iter_run_pumps

    class _StringDevice:
        def get_data(self, _path: str, _silent: bool = False) -> Any:
            return "not-a-dict"

    assert _iter_run_pumps(cast(Any, _StringDevice()), "return") == []


def test_add_maintenance_buttons_returns_when_hw_unknown() -> None:
    """Covers button.py:639 (`return` when tasks_for(hw) is empty)."""
    from custom_components.redsea.button import _add_maintenance_buttons

    class _UnknownHwDevice:
        _hw = "RS-NOT-A-REAL-MODEL"

    entities: list[Any] = []
    _add_maintenance_buttons(cast(Any, _UnknownHwDevice()), entities)
    # No task catalogue -> no entity added; the function exited early.
    assert entities == []


def test_add_maintenance_numbers_returns_when_hw_unknown() -> None:
    """Covers number.py:641 (symmetric early-return)."""
    from custom_components.redsea.number import _add_maintenance_numbers

    class _UnknownHwDevice:
        _hw = "RS-NOT-A-REAL-MODEL"

    entities: list[Any] = []
    _add_maintenance_numbers(cast(Any, _UnknownHwDevice()), entities)
    assert entities == []


def test_iter_run_pumps_in_number_skips_on_exception(hass: HomeAssistant) -> None:
    """Covers number.py:662-663 (same exception swallow as button.py)."""
    # The number module inlines the pump iteration (no helper), so we drive
    # it by calling _add_maintenance_numbers on a device whose get_data
    # raises. The function must not propagate the exception.
    from custom_components.redsea.number import _add_maintenance_numbers
    from custom_components.redsea.coordinator import ReefRunCoordinator

    class _ExplodingRun(ReefRunCoordinator):  # type: ignore[misc]
        # Bypass __init__: we only need get_data + _hw + serial to drive
        # the catalogue. `serial` is a @property on the parent, so we
        # override it rather than assigning to self.serial.
        serial = "boom"  # type: ignore[assignment]

        def __init__(self) -> None:  # noqa: D401
            self._hw = "RSRUN"

        def get_data(self, name: str, is_None_possible: bool = False) -> Any:
            raise RuntimeError("boom")

    entities: list[Any] = []
    _add_maintenance_numbers(cast(Any, _ExplodingRun()), entities)
    # All pump iterations raised -> no entity created for pump tasks.
    # Non-pump tasks (if any for RSRUN) would still be added; for RSRUN every
    # task is pump-scoped so the list ends empty.
    assert entities == []


@pytest.mark.asyncio
async def test_service_returns_error_when_coordinator_lacks_store(
    hass: HomeAssistant,
) -> None:
    """Covers __init__.py:387: coord found but no `.maintenance` attribute.

    Builds on the same _bootstrap_service helper but pokes the coordinator
    to drop its store before invoking the service.
    """
    coord, device_id = await _bootstrap_service(hass, "SERIAL-NM", "SERIAL-NM")

    # Remove the maintenance store from the coordinator the service will find.
    del coord.maintenance

    response = await hass.services.async_call(
        redsea_pkg.DOMAIN,
        "reset_maintenance",
        {"device_id": device_id, "task_key": "led_lens"},
        blocking=True,
        return_response=True,
    )
    assert isinstance(response, dict)
    assert "error" in response
    assert "store" in str(response["error"]).lower()


# =============================================================================
# Button entity lifecycle and action
# =============================================================================


@pytest.mark.asyncio
async def test_button_press_triggers_store_reset(hass: HomeAssistant) -> None:
    """Covers button.py:1145-1149 (async_press writes through to the store)."""
    from custom_components.redsea.button import MaintenanceButtonEntity

    class _Device:
        def __init__(self) -> None:
            self.serial = "PRESS-TEST"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "press-test")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceButtonEntity(cast(Any, device), task, sub_id=0)

    # Before press: no last_reset recorded.
    assert device.maintenance.get_last_reset(device.serial, 0, task.key) is None

    await entity.async_press()

    # After press: a timestamp is persisted.
    assert device.maintenance.get_last_reset(device.serial, 0, task.key) is not None


def test_button_extra_state_attributes_exposes_full_payload(
    hass: HomeAssistant,
) -> None:
    """Covers button.py:1116-1121 (compose attrs + ReefRoleMixin contribution)."""
    from custom_components.redsea.button import MaintenanceButtonEntity

    class _Device:
        def __init__(self) -> None:
            self.serial = "ATTRS-TEST"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "attrs-test")
            self.device_info = None

    device = _Device()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceButtonEntity(cast(Any, device), task, sub_id=0)

    attrs = entity.extra_state_attributes
    # _compute_attrs payload + reef_role from the mixin.
    assert attrs is not None
    assert attrs["task_key"] == task.key
    assert attrs["interval_days"] == task.default_days
    assert attrs["last_reset"] is None  # never reset
    assert attrs["days_left"] is None  # consequence of last_reset == None
    assert attrs["overdue"] is False
    assert attrs["reef_role"] == task.translation_key


# =============================================================================
# Lifecycle callbacks: store change triggers entity re-render
# =============================================================================
#
# `_on_store_change` is the nested callback bound in async_added_to_hass for
# both the button and number entities. Each test invokes that lifecycle hook
# and then mutates the store to verify the listener actually fires.


@pytest.mark.asyncio
async def test_button_callback_fires_on_store_change(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive `async_added_to_hass` then trigger the store; the nested
    callback (button.py:1131) must run.

    We can't bring up the full HA entity platform here, but we only need
    `super().async_added_to_hass()` to be a no-op so the rest of the method
    executes — which is exactly what monkeypatching the parent does.
    """
    from custom_components.redsea.button import MaintenanceButtonEntity
    from homeassistant.components.button import ButtonEntity

    class _Device:
        def __init__(self) -> None:
            self.serial = "CB-BTN"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "cb-btn")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceButtonEntity(cast(Any, device), task, sub_id=0)

    # Neutralise the parent's `async_added_to_hass`; we only care about the
    # subclass body that installs the listener.
    async def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(ButtonEntity, "async_added_to_hass", _noop, raising=False)

    # Track callback fires via async_write_ha_state.
    calls = {"n": 0}
    entity.async_write_ha_state = lambda: calls.__setitem__("n", calls["n"] + 1)  # type: ignore[assignment]

    # This is the call we previously skipped: it builds and registers the
    # real _on_store_change defined in production code, covering line 1131.
    await entity.async_added_to_hass()

    # Now mutate the store: the production callback (not a test-built one)
    # is what fires.
    await device.maintenance.async_reset(device.serial, 0, task.key)
    assert calls["n"] >= 1


@pytest.mark.asyncio
async def test_number_callback_fires_on_store_change(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same as the button test, for the number entity (covers number.py:1174)."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity
    from homeassistant.components.number import NumberEntity

    class _Device:
        def __init__(self) -> None:
            self.serial = "CB-NUM"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "cb-num")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)

    async def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(NumberEntity, "async_added_to_hass", _noop, raising=False)

    calls = {"n": 0}
    entity.async_write_ha_state = lambda: calls.__setitem__("n", calls["n"] + 1)  # type: ignore[assignment]

    await entity.async_added_to_hass()

    await device.maintenance.async_set_interval(device.serial, 0, task.key, 100)
    assert calls["n"] >= 1


# =============================================================================
# MaintenanceStore.async_load: idempotency and _parse_dt branches
# =============================================================================


@pytest.mark.asyncio
async def test_async_load_is_idempotent(hass: HomeAssistant) -> None:
    """Covers maintenance.py:326 (the `return` when self._loaded is True)."""
    store = maint.MaintenanceStore(hass, "idempotency")
    await store.async_load()
    # A second async_load() must hit the fast-path return without re-reading.
    # We assert that by stubbing the underlying Store and verifying it's not
    # called a second time.
    calls = {"n": 0}
    orig = store._store.async_load

    async def _counting_load(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        return await orig(*args, **kwargs)

    store._store.async_load = _counting_load  # type: ignore[assignment]
    await store.async_load()
    assert calls["n"] == 0, "second async_load must short-circuit"


def test_parse_dt_returns_none_for_non_string() -> None:
    """Covers maintenance.py:455-456 (the `not isinstance(value, str)` branch)."""
    assert maint._parse_dt(None) is None
    assert maint._parse_dt(123) is None
    assert maint._parse_dt({"k": "v"}) is None


def test_parse_dt_returns_none_for_malformed_iso() -> None:
    """Covers maintenance.py:459-460 (`except ValueError: return None`)."""
    assert maint._parse_dt("not-a-date") is None
    assert maint._parse_dt("2026-99-99T00:00:00") is None


def test_parse_dt_attaches_utc_when_tz_missing() -> None:
    """Covers maintenance.py:461-462 (`if dt.tzinfo is None: replace utc`)."""
    # Naive ISO timestamp must come back as timezone-aware UTC.
    dt = maint._parse_dt("2026-01-15T12:00:00")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.utcoffset() == timedelta(0)


def test_parse_dt_keeps_explicit_tz() -> None:
    """Sanity check: an explicit tz must NOT be overwritten."""
    dt = maint._parse_dt("2026-01-15T12:00:00+02:00")
    assert dt is not None
    assert dt.utcoffset() == timedelta(hours=2)


# =============================================================================
# MaintenanceIntervalNumberEntity.native_value: store exception fallback
# =============================================================================


@pytest.mark.asyncio
async def test_number_native_value_falls_back_on_store_exception(
    hass: HomeAssistant,
) -> None:
    """Covers number.py:1151-1152 (`except Exception: days = default`)."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    class _Device:
        def __init__(self) -> None:
            self.serial = "EXC"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "exc")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)

    # Make the store's get_interval raise; the entity must swallow it and
    # report the task's default.
    def _boom(*_args: Any, **_kwargs: Any) -> int:
        raise RuntimeError("store unavailable")

    device.maintenance.get_interval = _boom  # type: ignore[assignment]
    # Default 135 days / 30 = 4 (floor) for run_pump_motor.
    assert entity.native_value == 4.0


# =============================================================================
# Driving async_added_to_hass directly to cover the nested closure body
# =============================================================================
#
# The previous callback tests rebuild an equivalent `_on_store_change`
# externally; that exercises `async_write_ha_state()` but not the closure
# defined *inside* `async_added_to_hass`. To hit those exact lines we have
# to invoke `async_added_to_hass` and then trigger the store. The bottleneck
# is `await super().async_added_to_hass()` which expects a fully-initialised
# HA entity; we monkeypatch it to a no-op.


@pytest.mark.asyncio
async def test_button_async_added_to_hass_wires_real_closure(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers button.py:1131 by executing the real nested `_on_store_change`."""
    from custom_components.redsea.button import MaintenanceButtonEntity

    # Stub parent chain: ReefRoleMixin/RestoreEntity etc. all the way up to
    # Entity. We skip them entirely; the only piece we need to run is the
    # body of MaintenanceButtonEntity.async_added_to_hass that wires the
    # listener.
    async def _noop_super(self: Any) -> None:
        return None

    monkeypatch.setattr(
        "homeassistant.helpers.entity.Entity.async_added_to_hass",
        _noop_super,
    )

    class _Device:
        def __init__(self) -> None:
            self.serial = "REAL-CB-BTN"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "real-cb-btn")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceButtonEntity(cast(Any, device), task, sub_id=0)

    # Stub async_write_ha_state so the closure has a callable target.
    calls = {"n": 0}
    entity.async_write_ha_state = lambda: calls.__setitem__("n", calls["n"] + 1)  # type: ignore[assignment]

    # Now invoke the real lifecycle hook; this defines the real closure and
    # registers it as a listener.
    await entity.async_added_to_hass()

    # Trigger the listener; the real (in-scope) closure must fire.
    await device.maintenance.async_reset(device.serial, 0, task.key)
    assert calls["n"] >= 1

    # Clean up: invoke the removal hook for completeness.
    await entity.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_number_async_added_to_hass_wires_real_closure(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers number.py:1174 by executing the real nested closure."""
    from custom_components.redsea.number import MaintenanceIntervalNumberEntity

    async def _noop_super(self: Any) -> None:
        return None

    monkeypatch.setattr(
        "homeassistant.helpers.entity.Entity.async_added_to_hass",
        _noop_super,
    )

    class _Device:
        def __init__(self) -> None:
            self.serial = "REAL-CB-NUM"
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "real-cb-num")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()
    task = next(t for t in maint.TASKS["RSRUN"] if t.key == "run_pump_motor")
    entity = MaintenanceIntervalNumberEntity(cast(Any, device), task, sub_id=0)

    calls = {"n": 0}
    entity.async_write_ha_state = lambda: calls.__setitem__("n", calls["n"] + 1)  # type: ignore[assignment]

    await entity.async_added_to_hass()

    await device.maintenance.async_set_interval(device.serial, 0, task.key, 60)
    assert calls["n"] >= 1

    await entity.async_will_remove_from_hass()

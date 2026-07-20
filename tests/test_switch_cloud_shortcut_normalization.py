"""Regression tests for ReefBeat cloud shortcut availability.

Some ReefBeat cloud accounts return non-canonical shortcut payloads:

* ``"enabled": "false"`` (string) instead of ``false`` (bool)
* ``"code": "EMERGENCY_1"`` (uppercase) instead of ``"emergency_1"``
* ``"type": "EMERGENCY"`` (uppercase) instead of ``"emergency"``

The pre-fix code path had three combined bugs that made every shortcut
switch appear as *Unavailable* on those accounts:

1. ``_recompute_active_switches`` iterated every property dict and treated
   any truthy ``enabled`` as an active shortcut. The string ``"false"`` is
   truthy in Python, so ``emergency_1`` was falsely flagged as active.
2. ``_recompute_active_switches`` stored the property *key* (``emergency_1``)
   while ``__init__`` stored ``entity_description.key`` (``shortcut_emergency_1``);
   two writers, two formats, incompatible with the availability comparison.
3. ``available`` compared against ``self._shortcut["code"]`` case-sensitively,
   so ``EMERGENCY_1`` never matched ``emergency_1``.

These tests lock in the fixes.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from custom_components.redsea.switch import (
    ReefCloudSwitchEntity,
    ReefCloudSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator


class _CloudDevice(FakeCoordinator):
    """Cloud coordinator fake matching the shape used by real code."""


# ---------------------------------------------------------------------------
# _coerce_enabled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("True", True),
        ("  TRUE  ", True),
        ("false", False),
        ("False", False),
        ("", False),
        (None, False),
        (0, False),
        (1, True),
    ],
)
def test_coerce_enabled_normalizes_bools_and_strings(
    value: Any, expected: bool
) -> None:
    """The string 'false' must be coerced to False, not treated as truthy."""
    assert ReefCloudSwitchEntity._coerce_enabled(value) is expected


# ---------------------------------------------------------------------------
# _recompute_active_switches - server quirk defenses
# ---------------------------------------------------------------------------


def _clear_active_switches() -> None:
    ReefCloudSwitchEntity._active_switches.clear()


def test_recompute_ignores_string_false_enabled() -> None:
    """`"enabled": "false"` must not flag the shortcut as active."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                # Real user payload: uppercase type + string enabled.
                "emergency_1": {
                    "code": "EMERGENCY_1",
                    "name": "Emergency",
                    "type": "EMERGENCY",
                    "enabled": "false",
                },
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": False,
                },
                "maintenance_1": {
                    "name": "Maintenance",
                    "code": "maintenance_1",
                    "type": "maintenance",
                    "enabled": False,
                },
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))

    # No active shortcut should be recorded.
    assert "a1" not in ReefCloudSwitchEntity._active_switches


def test_recompute_ignores_non_shortcut_dict_properties() -> None:
    """Random dict properties with truthy `enabled` must not be picked up."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                # A non-shortcut dict with `enabled` set - must be ignored.
                "groups": [{"name": "rsled160"}],
                "some_random_config": {"enabled": True, "type": "misc"},
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": False,
                },
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    assert "a1" not in ReefCloudSwitchEntity._active_switches


def test_recompute_records_active_shortcut_lowercased() -> None:
    """`code: "EMERGENCY_1"` with real string `"true"` must record `emergency_1`."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                "emergency_1": {
                    "code": "EMERGENCY_1",
                    "name": "Emergency",
                    "type": "EMERGENCY",
                    "enabled": "true",
                },
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    assert ReefCloudSwitchEntity._active_switches["a1"] == "emergency_1"


def test_recompute_records_active_shortcut_from_bool_true() -> None:
    """The canonical payload (bool `enabled: True`) still works after the fix."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": True,
                },
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    assert ReefCloudSwitchEntity._active_switches["a1"] == "feeding_1"


def test_recompute_breaks_on_first_active_shortcut() -> None:
    """Only the first active shortcut is recorded (mutual exclusion contract)."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": True,
                },
                "maintenance_1": {
                    "name": "Maintenance",
                    "code": "maintenance_1",
                    "type": "maintenance",
                    "enabled": True,
                },
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    # feeding_1 comes first in insertion order; keep original tie-break behavior.
    assert ReefCloudSwitchEntity._active_switches["a1"] == "feeding_1"


def test_recompute_handles_multiple_aquariums_independently() -> None:
    """Each aquarium tracks its own active shortcut (or lack thereof)."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": True,
                },
            },
        },
        {
            "uid": "a2",
            "properties": {
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": "false",  # string false, must NOT activate
                },
            },
        },
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    assert ReefCloudSwitchEntity._active_switches["a1"] == "feeding_1"
    assert "a2" not in ReefCloudSwitchEntity._active_switches


# ---------------------------------------------------------------------------
# available - case-insensitive comparison
# ---------------------------------------------------------------------------


def _make_entity(
    device: _CloudDevice,
    aquarium_uid: str,
    key: str,
    shortcut_path: str,
) -> ReefCloudSwitchEntity:
    """Build a ReefCloudSwitchEntity wired to `device` for `aquarium_uid`."""
    aquarium = {"uid": aquarium_uid, "name": "Tank"}
    desc = ReefCloudSwitchEntityDescription(
        key=key,
        translation_key=key,
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name=shortcut_path + ".enabled",
        aquarium=aquarium,
    )
    return ReefCloudSwitchEntity(cast(Any, device), desc)


def test_available_matches_uppercase_code_against_lowercase_active() -> None:
    """`code: "EMERGENCY_1"` must match `_active_switches["a1"] = "emergency_1"`."""
    _clear_active_switches()
    device = _CloudDevice()
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {
        "name": "Emergency",
        "code": "EMERGENCY_1",  # uppercase from the server
        "type": "EMERGENCY",
        "enabled": "true",
    }

    entity = _make_entity(device, "a1", "shortcut_emergency_1", shortcut_path)

    # Simulate: emergency is the currently-active shortcut.
    ReefCloudSwitchEntity._active_switches["a1"] = "emergency_1"

    assert entity.available is True


def test_available_true_for_inactive_switch_when_no_active_shortcut() -> None:
    """All shortcuts must be available when none is running."""
    _clear_active_switches()
    device = _CloudDevice()
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {
        "name": "Feeding",
        "code": "feeding_1",
        "type": "feeding",
        "enabled": False,
    }

    entity = _make_entity(device, "a1", "shortcut_feeding_1", shortcut_path)
    assert entity.available is True


def test_available_false_for_other_shortcut_when_one_is_active() -> None:
    """Mutual exclusion: the other shortcuts must be unavailable while one runs."""
    _clear_active_switches()
    device = _CloudDevice()
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {
        "name": "Feeding",
        "code": "feeding_1",
        "type": "feeding",
        "enabled": False,
    }

    entity = _make_entity(device, "a1", "shortcut_feeding_1", shortcut_path)

    # Emergency is running; feeding must be unavailable.
    ReefCloudSwitchEntity._active_switches["a1"] = "emergency_1"

    assert entity.available is False


# ---------------------------------------------------------------------------
# End-to-end: full user-reported payload
# ---------------------------------------------------------------------------


def test_full_user_payload_all_shortcuts_available_when_none_active() -> None:
    """Reproduce the exact user payload and assert every shortcut is available."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                "disable_shortcut": False,
                "emergency": False,
                "emergency_1": {
                    "code": "EMERGENCY_1",
                    "name": "Emergency",
                    "type": "EMERGENCY",
                    "enabled": "false",  # <-- the root cause
                },
                "feeding": False,
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": False,
                    "enabled_by_schedule": False,
                },
                "groups": [{"name": "rsled90", "properties": {}}],
                "healthy": True,
                "led_emergency": True,
                "maintenance": False,
                "maintenance_1": {
                    "name": "Maintenance",
                    "code": "maintenance_1",
                    "type": "maintenance",
                    "enabled": False,
                    "enabled_by_schedule": False,
                },
                "shortcut_reminder": False,
                "staggered": True,
                "staggered_delay": 10,
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))

    # No shortcut is actually running.
    assert "a1" not in ReefCloudSwitchEntity._active_switches

    # Every switch resolves to available.
    aquarium_props = device.get_data_map["$.sources[?(@.name=='/aquarium')].data"][0][
        "properties"
    ]

    for shortcut_key in ("emergency_1", "feeding_1", "maintenance_1"):
        shortcut_path = f"$.{shortcut_key}"
        device.get_data_map[shortcut_path] = aquarium_props[shortcut_key]
        entity = _make_entity(device, "a1", f"shortcut_{shortcut_key}", shortcut_path)
        assert entity.available is True, f"{shortcut_key} should be available"


# ---------------------------------------------------------------------------
# icon - lowercase type
# ---------------------------------------------------------------------------
# Note: at the time of writing, `ReefCloudSwitchEntity.icon` computes
# `"redsea:" + type.lower()` but never returns it — the only observable
# outputs are `"redsea:" + shortcut["icon"]` (when the `icon` field is set)
# or `entity_description.icon` (fallback). The `.lower()` normalization on
# `type` is kept as a defensive measure in case the dead code branch is
# revived, but we only test the observable paths here.


def test_icon_falls_back_to_entity_description_when_no_icon_field() -> None:
    """Without a custom `icon` field, the entity_description icon is used."""
    _clear_active_switches()
    device = _CloudDevice()
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {
        "name": "Emergency",
        "code": "EMERGENCY_1",
        "type": "EMERGENCY",  # uppercase must not raise or leak into output
        "enabled": "false",
    }

    entity = _make_entity(device, "a1", "shortcut_emergency_1", shortcut_path)
    # entity_description.icon comes from _make_entity ("mdi:play").
    assert entity.icon == "mdi:play"


def test_icon_still_prefers_explicit_icon_field() -> None:
    """A custom `icon` field must still take precedence over `type`."""
    _clear_active_switches()
    device = _CloudDevice()
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {
        "name": "Feeding",
        "code": "feeding_1",
        "type": "FEEDING",  # uppercase type must not break the custom icon path
        "icon": "feeding4",
        "enabled": False,
    }

    entity = _make_entity(device, "a1", "shortcut_feeding_1", shortcut_path)
    assert entity.icon == "redsea:feeding4"


# ---------------------------------------------------------------------------
# _compute_is_on - normalize enabled read via value_name JSONPath
# ---------------------------------------------------------------------------
#
# `_compute_is_on` fetches the `enabled` field through the coordinator via a
# JSONPath ending in `.enabled`. The cloud may return that as a string, and
# `bool("false")` is True, which would pin the switch to ON in the UI.


def _make_entity_with_value(
    device: _CloudDevice,
    aquarium_uid: str,
    key: str,
    shortcut_payload: dict,
    enabled_value: Any,
) -> ReefCloudSwitchEntity:
    """Build an entity where `value_name` resolves to `enabled_value`."""
    shortcut_path = f"$.shortcut_for_{key}"
    value_path = f"$.value_for_{key}"
    device.get_data_map[shortcut_path] = shortcut_payload
    device.get_data_map[value_path] = enabled_value

    aquarium = {"uid": aquarium_uid, "name": "Tank"}
    desc = ReefCloudSwitchEntityDescription(
        key=key,
        translation_key=key,
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name=value_path,
        aquarium=aquarium,
    )
    return ReefCloudSwitchEntity(cast(Any, device), desc)


@pytest.mark.parametrize(
    ("enabled_value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("True", True),
        ("false", False),
        ("False", False),
        ("", False),
    ],
)
def test_compute_is_on_normalizes_enabled(enabled_value: Any, expected: bool) -> None:
    """`_compute_is_on` must treat string "false" as False, not truthy."""
    _clear_active_switches()
    device = _CloudDevice()
    entity = _make_entity_with_value(
        device,
        "a1",
        "shortcut_feeding_1",
        shortcut_payload={
            "name": "Feeding",
            "code": "feeding_1",
            "type": "feeding",
            # Match the same value for consistency with __init__ logic.
            "enabled": enabled_value,
        },
        enabled_value=enabled_value,
    )

    assert entity._compute_is_on() is expected


def test_compute_is_on_returns_false_when_not_present() -> None:
    """Guard: `_compute_is_on` must return False when shortcut is absent."""
    _clear_active_switches()
    device = _CloudDevice()
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = None  # _present will be False

    aquarium = {"uid": "a1", "name": "Tank"}
    desc = ReefCloudSwitchEntityDescription(
        key="shortcut_feeding_1",
        translation_key="shortcut_feeding_1",
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name="$.missing",
        aquarium=aquarium,
    )
    entity = ReefCloudSwitchEntity(cast(Any, device), desc)
    assert entity._compute_is_on() is False


# ---------------------------------------------------------------------------
# End-to-end: newer server payload with `disable_shortcut` as a string
# ---------------------------------------------------------------------------


def test_recompute_survives_disable_shortcut_as_string() -> None:
    """The cloud may return `disable_shortcut: "feeding_1"` (string) instead
    of a bool. That property is not consumed by the integration, but must not
    poison `_recompute_active_switches` or crash it."""
    _clear_active_switches()
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                # New quirk observed on some accounts.
                "disable_shortcut": "feeding_1",
                "emergency": False,
                "emergency_1": {
                    "code": "EMERGENCY_1",
                    "name": "Emergency",
                    "type": "EMERGENCY",
                    "enabled": "false",
                },
                "feeding": False,
                "feeding_1": {
                    "name": "Feeding",
                    "code": "feeding_1",
                    "type": "feeding",
                    "enabled": False,
                    "enabled_by_schedule": False,
                },
                "groups": [{"name": "rsled90", "properties": {}}],
                "healthy": True,
                "led_emergency": True,
                "maintenance": False,
                "maintenance_1": {
                    "name": "Maintenance",
                    "code": "maintenance_1",
                    "type": "maintenance",
                    "enabled": False,
                    "enabled_by_schedule": False,
                },
                "shortcut_reminder": False,
                "staggered": True,
                "staggered_delay": 10,
            },
        }
    ]

    # Must not raise, and no shortcut should be marked active (all off).
    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    assert "a1" not in ReefCloudSwitchEntity._active_switches

"""Unit tests for `probe_entities.py` — the pure registry-key helpers used to
purge or rename a probe's entities. No Home Assistant imports involved.
"""

from __future__ import annotations

from custom_components.redsea import probe_entities as pe


def test_sanitise_uid_keeps_alphanumerics_lowercased() -> None:
    assert pe.sanitise_uid("0x0A:F1") == "0x0af1"


def test_probe_sub_id_parses_hex() -> None:
    assert pe.probe_sub_id("0x1F") == 31


def test_probe_key_prefix() -> None:
    assert pe.probe_key_prefix("Temperature", "0xAB") == "probe_temperature_0xab_"


def test_is_orphan_probe_entity() -> None:
    valid = {"probe_temperature_0xab_"}
    assert pe.is_orphan_probe_entity("socket_0_on_off", valid) is False  # not a probe_
    assert pe.is_orphan_probe_entity("probe_temperature_0xab_value", valid) is False
    assert pe.is_orphan_probe_entity("probe_ph_0xcd_value", valid) is True


def test_maintenance_probe_sub_id() -> None:
    tasks = {"clean_probe"}
    assert pe.maintenance_probe_sub_id("clean_probe_interval_31", tasks) == 31
    # Matches the task but has no trailing integer -> None.
    assert pe.maintenance_probe_sub_id("clean_probe", tasks) is None
    # Unrelated key -> None.
    assert pe.maintenance_probe_sub_id("socket_0_on_off", tasks) is None


def test_rename_unique_id_direct_probe_entity() -> None:
    got = pe.rename_unique_id(
        "CTL_probe_temperature_0xab_value",
        serial="CTL",
        old_type="temperature",
        old_uid="0xAB",
        new_uid="0xCD",
        probe_task_keys=set(),
    )
    assert got == "CTL_probe_temperature_0xcd_value"


def test_rename_unique_id_maintenance_instance() -> None:
    got = pe.rename_unique_id(
        "CTL_clean_probe_interval_171",  # 171 == int("0xAB", 16)
        serial="CTL",
        old_type="temperature",
        old_uid="0xAB",
        new_uid="0xCD",
        probe_task_keys={"clean_probe"},
    )
    assert got == f"CTL_clean_probe_interval_{int('0xCD', 16)}"


def test_rename_unique_id_wrong_serial_or_unrelated_returns_none() -> None:
    # Different serial prefix.
    assert (
        pe.rename_unique_id(
            "OTHER_probe_temperature_0xab_value",
            serial="CTL",
            old_type="temperature",
            old_uid="0xAB",
            new_uid="0xCD",
            probe_task_keys=set(),
        )
        is None
    )
    # Right serial but neither a matching probe key nor a maintenance instance.
    assert (
        pe.rename_unique_id(
            "CTL_socket_0_on_off",
            serial="CTL",
            old_type="temperature",
            old_uid="0xAB",
            new_uid="0xCD",
            probe_task_keys={"clean_probe"},
        )
        is None
    )


def test_probe_display_name_single_probe_no_suffix() -> None:
    ato = {"type": "ato", "uid": "0xA1", "name": "ATO"}
    assert pe.probe_display_name(ato, [ato]) == "ATO"


def test_probe_display_name_falls_back_to_type_when_unnamed() -> None:
    probe = {"type": "orp", "uid": "0xO1"}
    assert pe.probe_display_name(probe, [probe]) == "orp"


def test_probe_display_name_first_of_several_stays_plain() -> None:
    first = {"type": "ato", "uid": "0xA1", "name": "ATO"}
    second = {"type": "ato", "uid": "0xA2", "name": "ATO"}
    probes = [first, second]
    assert pe.probe_display_name(first, probes) == "ATO"


def test_probe_display_name_later_ones_get_hash_suffix() -> None:
    first = {"type": "ato", "uid": "0xA1", "name": "ATO"}
    second = {"type": "ato", "uid": "0xA2", "name": "ATO"}
    third = {"type": "ato", "uid": "0xA3", "name": "ATO"}
    probes = [first, second, third]
    assert pe.probe_display_name(second, probes) == "ATO #2"
    assert pe.probe_display_name(third, probes) == "ATO #3"


def test_probe_display_name_ignores_other_types_when_counting() -> None:
    ato = {"type": "ato", "uid": "0xA1", "name": "ATO"}
    ph = {"type": "ph", "uid": "0xP1", "name": "pH"}
    probes = [ato, ph]
    # Only one ATO among these -> no suffix, even though the list has 2 probes.
    assert pe.probe_display_name(ato, probes) == "ATO"


def test_probe_display_name_defensive_fallback_when_uid_absent_from_list() -> None:
    """If the probe itself isn't found among its own same-type siblings
    (should not normally happen), fall back to the plain label rather than
    raising.
    """
    orphan = {"type": "ato", "uid": "0xGONE", "name": "ATO"}
    siblings = [
        {"type": "ato", "uid": "0xA1", "name": "ATO"},
        {"type": "ato", "uid": "0xA2", "name": "ATO"},
    ]
    assert pe.probe_display_name(orphan, siblings) == "ATO"

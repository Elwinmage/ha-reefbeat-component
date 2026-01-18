from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast

import pytest


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    last_update_success: bool = True
    device_info: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.device_info is None:
            self.device_info = {"identifiers": {("redsea", self.serial)}}

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        def _remove() -> None:
            return None

        return _remove

    def get_data(self, _path: str, _is_None_possible: bool = False) -> Any:  # noqa: N803
        return None


def test_dose_get_value_missing_value_name_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from custom_components.redsea.binary_sensor import (
        ReefDoseBinarySensorEntity,
        ReefDoseBinarySensorEntityDescription,
    )

    desc = ReefDoseBinarySensorEntityDescription(
        key="dose",
        translation_key="dose",
        head=1,
        value_name=None,
        value_fn=None,
    )

    caplog.clear()
    ent = ReefDoseBinarySensorEntity(cast(Any, _FakeCoordinator()), desc)

    assert ent.is_on is None
    assert any("missing value_name" in rec.message for rec in caplog.records)


def test_dose_device_info_head_zero_returns_base() -> None:
    from custom_components.redsea.binary_sensor import (
        ReefDoseBinarySensorEntity,
        ReefDoseBinarySensorEntityDescription,
    )

    base_di = {"identifiers": {("redsea", "BASE")}, "manufacturer": "Red Sea"}
    device = _FakeCoordinator(serial="BASE", device_info=base_di)

    desc = ReefDoseBinarySensorEntityDescription(
        key="dose",
        translation_key="dose",
        head=0,
        value_name="$.x",
    )

    ent = ReefDoseBinarySensorEntity(cast(Any, device), desc)

    assert ent.device_info == base_di


def test_dose_device_info_builds_head_device_and_copies_fields_and_via_device() -> None:
    from custom_components.redsea.binary_sensor import (
        ReefDoseBinarySensorEntity,
        ReefDoseBinarySensorEntityDescription,
    )

    base_di = {
        # Explicit identifiers so ident != device.serial is exercised
        "identifiers": {("redsea", "IDENT")},
        "manufacturer": "Red Sea",
        "model": None,
        "model_id": "mid",
        "hw_version": "1",
        "sw_version": "2",
        "via_device": ("redsea", "IDENT"),
    }
    device = _FakeCoordinator(serial="SERIAL", title="Dose", device_info=base_di)

    desc = ReefDoseBinarySensorEntityDescription(
        key="dose",
        translation_key="dose",
        head=3,
        value_name="$.x",
    )

    ent = ReefDoseBinarySensorEntity(cast(Any, device), desc)
    di = cast(dict[str, Any], ent.device_info)

    assert di["identifiers"] == {("redsea", "IDENT", "head_3")}
    assert di["name"] == "Dose head 3"
    assert di["manufacturer"] == "Red Sea"
    assert di["model"] is None
    assert di["model_id"] == "mid"
    assert di["via_device"] == ("redsea", "IDENT")


def test_dose_device_info_falls_back_to_default_identifiers_when_missing() -> None:
    from custom_components.redsea.binary_sensor import (
        ReefDoseBinarySensorEntity,
        ReefDoseBinarySensorEntityDescription,
    )

    # No identifiers key present => should fall back to {(DOMAIN, device.serial)}
    device = _FakeCoordinator(serial="SER123", title="Dose", device_info={})

    desc = ReefDoseBinarySensorEntityDescription(
        key="dose",
        translation_key="dose",
        head=1,
        value_name="$.x",
    )

    ent = ReefDoseBinarySensorEntity(cast(Any, device), desc)
    di = cast(dict[str, Any], ent.device_info)

    assert di["identifiers"] == {("redsea", "SER123", "head_1")}

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, cast

import pytest

from custom_components.redsea.button import (
    ReefDoseButtonEntity,
    ReefDoseButtonEntityDescription,
)


@dataclass
class _FakeAPI:
    live_config_update: bool = False
    sent_http: list[tuple[str, Any, str]] = field(default_factory=list)

    async def http_send(self, path: str, payload: Any, method: str = "put") -> None:
        self.sent_http.append((path, payload, method))


@dataclass
class _FakeDoseCoordinator:
    serial: str = "DOSE-SERIAL"
    heads_nb: int = 2

    my_api: _FakeAPI = field(default_factory=_FakeAPI)

    get_data_map: dict[str, Any] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)
    fetched: list[str | None] = field(default_factory=list)
    calibrated: list[tuple[str, int, dict[str, Any]]] = field(default_factory=list)
    pressed: list[tuple[str, int]] = field(default_factory=list)
    bundles: list[dict[str, Any]] = field(default_factory=list)
    refresh_count: int = 0

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    async def delete(self, source: str) -> None:
        self.deleted.append(source)

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetched.append(config_path)

    async def calibration(
        self, action: str, head: int, payload: dict[str, Any]
    ) -> None:
        self.calibrated.append((action, head, payload))

    async def press(self, action: str, head: int) -> None:
        self.pressed.append((action, head))

    async def set_bundle(self, payload: dict[str, Any]) -> None:
        self.bundles.append(payload)

    async def async_request_refresh(self) -> None:
        self.refresh_count += 1


@pytest.mark.asyncio
async def test_reefdose_button_delete_uses_bundled_head_settings() -> None:
    device = _FakeDoseCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.bundled_heads"] = True

    desc = ReefDoseButtonEntityDescription(
        key="delete",
        translation_key="delete_supplement",
        action="/head/1/settings",
        delete=True,
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert device.deleted == ["/head/settings"]
    assert device.refresh_count == 1


@pytest.mark.asyncio
async def test_reefdose_button_fetch_config_calls_head_settings_path() -> None:
    device = _FakeDoseCoordinator()

    desc = ReefDoseButtonEntityDescription(
        key="fetch_config_1",
        translation_key="fetch_config",
        action="fetch_config",
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert device.fetched == ["/head/1/settings"]
    assert device.refresh_count == 1


@pytest.mark.asyncio
async def test_reefdose_button_list_actions_call_calibration_per_action() -> None:
    device = _FakeDoseCoordinator()

    desc = ReefDoseButtonEntityDescription(
        key="start_calibration_1",
        translation_key="start_calibration",
        action=["start-calibration", "calibration/start"],
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert device.calibrated == [
        ("start-calibration", 1, {}),
        ("calibration/start", 1, {}),
    ]
    assert device.refresh_count == 1


@pytest.mark.asyncio
async def test_reefdose_button_end_calibration_uses_local_volume() -> None:
    device = _FakeDoseCoordinator()
    device.get_data_map["$.local.head.1.calibration_dose"] = 7

    desc = ReefDoseButtonEntityDescription(
        key="set_calibration_value_head_1",
        translation_key="set_calibration_value",
        action="end-calibration",
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert device.calibrated == [("end-calibration", 1, {"volume": 7})]
    assert device.refresh_count == 1


@pytest.mark.asyncio
async def test_reefdose_set_supplement_redsea_reefcare_uses_bundle() -> None:
    device = _FakeDoseCoordinator()
    device.get_data_map["$.local.head.1.new_supplement"] = "redsea-reefcare"

    desc = ReefDoseButtonEntityDescription(
        key="set_supplement_head_1",
        translation_key="set_supplement",
        action="setup-supplement",
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert device.bundles, "Expected set_bundle to be called"
    assert device.calibrated == []
    assert device.refresh_count == 1


@pytest.mark.asyncio
async def test_reefdose_set_supplement_other_requires_non_empty_fields() -> None:
    device = _FakeDoseCoordinator()
    device.get_data_map["$.local.head.1.new_supplement"] = "other"
    device.get_data_map["$.local.head.1.new_supplement_name"] = ""
    device.get_data_map["$.local.head.1.new_supplement_short_name"] = "x"
    device.get_data_map["$.local.head.1.new_supplement_brand_name"] = "y"

    desc = ReefDoseButtonEntityDescription(
        key="set_supplement_head_1",
        translation_key="set_supplement",
        action="setup-supplement",
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)

    with pytest.raises(Exception, match=r"text box can not be empty"):
        await entity.async_press()


@pytest.mark.asyncio
async def test_reefdose_set_supplement_other_builds_payload_and_calls_calibration() -> (
    None
):
    device = _FakeDoseCoordinator()
    device.get_data_map["$.local.head.1.new_supplement"] = "other"
    device.get_data_map["$.local.head.1.new_supplement_name"] = "My Supp"
    device.get_data_map["$.local.head.1.new_supplement_short_name"] = "MS"
    device.get_data_map["$.local.head.1.new_supplement_brand_name"] = "Brand"

    desc = ReefDoseButtonEntityDescription(
        key="set_supplement_head_1",
        translation_key="set_supplement",
        action="setup-supplement",
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert len(device.calibrated) == 1
    action, head, payload = device.calibrated[0]
    assert action == "setup-supplement"
    assert head == 1

    # Payload should contain a generated uid and the input strings
    assert uuid.UUID(str(payload["uid"]))
    assert payload["name"] == "My Supp"
    assert payload["short_name"] == "MS"
    assert payload["brand_name"] == "Brand"
    assert device.refresh_count == 1


@pytest.mark.asyncio
async def test_dose_button_set_supplement_name_calls_http_send() -> None:
    """Couvre _set_supplement_name() : lignes 594, 615-635."""
    from custom_components.redsea.button import (
        ReefDoseButtonEntity,
        ReefDoseButtonEntityDescription,
    )

    device = _FakeDoseCoordinator()
    device.get_data_map.update(
        {
            "$.local.head.1.new_supplement_display_name": "Custom Supplement",
            "$.local.head.1.new_supplement_name": "custom_supp",
            "$.local.head.1.new_supplement_brand_name": "MyBrand",
            "$.local.head.1.new_supplement_short_name": "CS",
        }
    )

    desc = ReefDoseButtonEntityDescription(
        key="set_supplement_name_1",
        translation_key="set_supplement_name",
        head=1,
    )

    entity = ReefDoseButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert len(device.my_api.sent_http) == 1
    path, payload, method = device.my_api.sent_http[0]
    assert path == "/head/1/settings"
    assert method == "put"
    assert payload["supplement"]["name"] == "custom_supp"
    assert payload["supplement"]["display_name"] == "Custom Supplement"
    assert payload["supplement"]["brand_name"] == "MyBrand"
    assert payload["supplement"]["short_name"] == "CS"

    assert device.refresh_count == 1

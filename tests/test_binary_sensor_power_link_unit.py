"""Coverage for the RSPOWER `connected_device` binary sensors.

A ReefPower strip paired with a ReefControl hub reports the hub under
`connected_device` on /dashboard. Three states have to be told apart, because
the card draws each differently: no hub was ever paired (nothing to show), a
hub is paired and reachable (link picture), and a hub is paired but offline
(link picture, blinking). Pairing and reachability are therefore separate
sensors — collapsing them would make an unplugged hub look like no hub at all.

Covers `control_link_up`, `control_paired` and `control_internet_connected`
in `binary_sensor.py`.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

import custom_components.redsea.binary_sensor as binary_sensor_platform


class _FakeConnectedDevice:
    """A device answering /dashboard connected_device lookups from a dict.

    `payload` is what the hub sub-object holds, or None when nothing was ever
    paired — the state a strip reports before it meets a ReefControl.
    """

    def __init__(self, payload: dict[str, Any] | None) -> None:
        self.payload = payload
        self.calls: list[tuple[str, bool]] = []

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        self.calls.append((name, is_None_possible))
        if "connected_device." not in name:
            return None
        field = name.rsplit("connected_device.", 1)[1]
        if self.payload is None:
            return None
        return self.payload.get(field)


_PAIRED: dict[str, Any] = {
    "type": "control",
    "hwid": "d4e9f4e89208",
    "status": "connected",
    "internet_connected": True,
}

_OFFLINE: dict[str, Any] = {
    **_PAIRED,
    "status": "disconnected",
    "internet_connected": False,
}

_KEYS = ["control_link_up", "control_paired", "control_internet_connected"]


def _binary(key: str) -> Any:
    return next(d for d in binary_sensor_platform.POWER_SENSORS if d.key == key)


@pytest.mark.parametrize("key", _KEYS)
def test_reachable_hub_reports_every_flag_on(key: str) -> None:
    """A paired, online hub lights all three connectivity flags."""
    device = _FakeConnectedDevice(_PAIRED)

    assert _binary(key).value_fn(cast(Any, device)) is True


@pytest.mark.parametrize("key", _KEYS)
def test_unpaired_strip_reports_every_flag_off(key: str) -> None:
    """No hub means no link, no pairing and no hub internet."""
    device = _FakeConnectedDevice(None)

    assert _binary(key).value_fn(cast(Any, device)) is False


@pytest.mark.parametrize("key", _KEYS)
def test_connected_device_lookups_allow_none(key: str) -> None:
    """A null connected_device is a normal state, so the flag must be set."""
    device = _FakeConnectedDevice(None)

    _binary(key).value_fn(cast(Any, device))

    assert all(flag is True for _, flag in device.calls)


def test_offline_hub_stays_paired() -> None:
    """Pairing survives the hub going offline — the card still draws it."""
    device = _FakeConnectedDevice(_OFFLINE)

    assert _binary("control_paired").value_fn(cast(Any, device)) is True


def test_offline_hub_drops_its_link() -> None:
    """An unreachable hub is what puts the card's link picture in alert."""
    device = _FakeConnectedDevice(_OFFLINE)

    assert _binary("control_link_up").value_fn(cast(Any, device)) is False


def test_offline_hub_drops_its_internet_flag() -> None:
    """The hub's own internet flag follows it down."""
    device = _FakeConnectedDevice(_OFFLINE)

    assert _binary("control_internet_connected").value_fn(cast(Any, device)) is False


def test_unexpected_status_is_not_a_live_link() -> None:
    """Only the documented `connected` status counts as a live link."""
    device = _FakeConnectedDevice({**_PAIRED, "status": "pairing"})

    assert _binary("control_link_up").value_fn(cast(Any, device)) is False


def test_missing_internet_flag_is_not_truthy() -> None:
    """A payload without the flag must not read as connected."""
    payload = {k: v for k, v in _PAIRED.items() if k != "internet_connected"}
    device = _FakeConnectedDevice(payload)

    assert _binary("control_internet_connected").value_fn(cast(Any, device)) is False


@pytest.mark.parametrize("key", _KEYS)
def test_flags_are_strictly_boolean(key: str) -> None:
    """HA needs a real bool, not a truthy payload value leaking through."""
    device = _FakeConnectedDevice(_PAIRED)

    assert isinstance(_binary(key).value_fn(cast(Any, device)), bool)

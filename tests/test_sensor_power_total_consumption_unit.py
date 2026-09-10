"""Coverage for `_total_power_consumption` in `sensor.py`.

The helper backs the RSPOWER `total_consumption` entity: it sums the
per-socket wattage reported on /dashboard. Two behaviours matter beyond the
happy path, and both are covered here. A socket that reports nothing must not
be counted as 0 W — a strip whose sockets are all silent goes unavailable
rather than claiming it draws no power. And a payload carrying a non-numeric
wattage must not take the whole sensor down: that socket is skipped and the
others still add up.

Covers lines 1172-1186 in `sensor.py`.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

import custom_components.redsea.sensor as sensor_platform


class _FakeDashboard:
    """A device answering per-socket consumption lookups from a list.

    `values[i]` is what socket `i` reports; `None` stands for a socket that
    returns nothing. Any index beyond the list also returns nothing, so a
    short list models a strip whose later sockets are absent from /dashboard.
    """

    def __init__(self, values: list[Any], socket_count: int | None = None) -> None:
        self.values = values
        self.calls: list[tuple[str, bool]] = []
        if socket_count is not None:
            self.socket_count = socket_count

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        self.calls.append((name, is_None_possible))
        for idx, value in enumerate(self.values):
            if f"sockets[{idx}].consumption" in name:
                return value
        return None


def _total(device: Any) -> Any:
    return sensor_platform._total_power_consumption(cast(Any, device))


def test_sums_every_socket() -> None:
    """Each socket's wattage contributes to the total."""
    device = _FakeDashboard([10, 20, 5], socket_count=3)

    assert _total(device) == 35.0


def test_reads_consumption_with_none_allowed() -> None:
    """A socket missing from /dashboard is a normal state, not an error."""
    device = _FakeDashboard([10], socket_count=1)

    _total(device)

    assert device.calls == [
        (
            "$.sources[?(@.name=='/dashboard')].data.sockets[0].consumption",
            True,
        )
    ]


def test_queries_exactly_socket_count_paths() -> None:
    """The helper walks the sockets the model declares, no more."""
    device = _FakeDashboard([1, 2, 3, 4, 5, 6, 7, 8], socket_count=6)

    _total(device)

    assert len(device.calls) == 6


def test_silent_sockets_are_skipped() -> None:
    """A socket reporting nothing does not drag the total down to 0."""
    device = _FakeDashboard([10, None, 5], socket_count=3)

    assert _total(device) == 15.0


def test_all_silent_reports_unavailable() -> None:
    """No socket reporting means unavailable, not 0 W."""
    device = _FakeDashboard([None, None], socket_count=2)

    assert _total(device) is None


def test_no_sockets_reports_unavailable() -> None:
    """A strip declaring no socket has nothing to sum."""
    device = _FakeDashboard([], socket_count=0)

    assert _total(device) is None
    assert device.calls == []


def test_missing_socket_count_reports_unavailable() -> None:
    """A device without socket_count is skipped rather than crashing."""
    device = _FakeDashboard([10, 20])

    assert _total(device) is None
    assert device.calls == []


@pytest.mark.parametrize("bad", ["n/a", None, object(), [1]])
def test_unparsable_wattage_is_ignored(bad: Any) -> None:
    """A malformed reading is dropped; the remaining sockets still count."""
    device = _FakeDashboard([10, bad, 5], socket_count=3)

    assert _total(device) == 15.0


def test_only_unparsable_wattage_reports_unavailable() -> None:
    """A reading that is present but unusable is not a valid measurement."""
    device = _FakeDashboard(["n/a"], socket_count=1)

    assert _total(device) is None


def test_numeric_strings_are_accepted() -> None:
    """The device may serialise wattage as a string."""
    device = _FakeDashboard(["10.5", 4.5], socket_count=2)

    assert _total(device) == 15.0


def test_total_is_rounded_to_one_decimal() -> None:
    """Floating-point noise must not leak into the state."""
    device = _FakeDashboard([0.1, 0.2], socket_count=2)

    assert _total(device) == 0.3


def test_zero_watt_socket_is_a_real_reading() -> None:
    """An idle socket reports 0 W, which keeps the sensor available."""
    device = _FakeDashboard([0, 0], socket_count=2)

    assert _total(device) == 0.0


def test_value_fn_is_wired_to_the_helper() -> None:
    """The entity description reads the summed wattage."""
    description = next(
        d for d in sensor_platform.POWER_SENSORS if d.key == "total_consumption"
    )
    device = _FakeDashboard([12, 8], socket_count=2)

    assert description.value_fn(cast(Any, device)) == 20.0


def test_total_consumption_description_is_a_power_measurement() -> None:
    """The entity must be typed so HA records and graphs it as power."""
    description = next(
        d for d in sensor_platform.POWER_SENSORS if d.key == "total_consumption"
    )

    assert description.translation_key == "total_consumption"
    assert description.native_unit_of_measurement == "W"
    assert description.device_class == "power"
    assert description.state_class == "measurement"

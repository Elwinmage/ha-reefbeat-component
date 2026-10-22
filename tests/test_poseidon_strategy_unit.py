"""Poseidon strategies: flatten, compare, comparisons, mergers, poll control."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import strategy
from custom_components.redsea.poseidon.strategy import (
    Comparisons,
    PollControl,
    compare,
    flatten,
    is_state_topic,
    merge_state,
    polled_leaves,
)


def test_is_state_topic() -> None:
    assert is_state_topic("device/reef-wave/aa/state")
    assert not is_state_topic("device/reef-wave/aa/telemetry")
    assert not is_state_topic("other/state")


def test_flatten() -> None:
    value = {"a": {"b": 1, "c": [2, {"d": 3}]}, "e": {}, "f": []}
    assert dict(flatten(value)) == {
        "a.b": 1,
        "a.c.0": 2,
        "a.c.1.d": 3,
        "e": {},
        "f": [],
    }
    assert list(flatten(5)) == [("", 5)]
    assert list(flatten([1])) == [("0", 1)]


def _coordinator(sources: Any) -> Any:
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def test_polled_leaves() -> None:
    coordinator = _coordinator([{"name": "/mode", "data": {"mode": "auto"}}, "junk"])
    assert polled_leaves(coordinator) == [("/mode", "mode", "auto")]
    assert polled_leaves(SimpleNamespace()) == []
    assert polled_leaves(_coordinator(None)) == []


def test_compare_verdicts() -> None:
    leaves = [
        ("/mode", "mode", "auto"),
        ("/dashboard", "heads.1.state", "on"),
        ("/dashboard", "status.heads.1.state", "off"),
        ("/dashboard", "speed", 40),
    ]
    results = {
        r["path"]: r
        for r in compare(
            {"mode": "auto", "heads": {"1": {"state": "on"}}, "speed": 50, "x": 1},
            leaves,
        )
    }
    assert results["mode"]["verdict"] == "same"
    # The closest polled path wins
    assert results["heads.1.state"]["verdict"] == "same"
    assert [m["path"] for m in results["heads.1.state"]["matches"]] == ["heads.1.state"]
    assert results["speed"]["verdict"] == "differs"
    assert results["x"]["verdict"] == "unknown" and results["x"]["matches"] == []
    # A bare value has no path to compare
    assert compare(3, leaves) == []


def test_comparisons_report_on_next_poll() -> None:
    written: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    comparisons = Comparisons()
    coordinator = _coordinator([{"name": "/mode", "data": {"mode": "auto"}}])
    comparisons.polled("aa", coordinator)  # nothing pushed: nothing written
    assert written == []
    comparisons.add(
        "aa", "device/reef-wave/aa/state", {"mode": "auto", "new": 1}, written.append
    )
    comparisons.add(
        "aa", "device/reef-wave/aa/state", {"mode": "x"}, other.append, merged=True
    )
    comparisons.polled("aa", coordinator)
    assert len(written) == 1 and len(other) == 1
    record = written[0]
    assert record["kind"] == "compare" and record["merged"] is False
    assert record["hwid"] == "aa" and record["topic"].endswith("/state")
    assert record["summary"] == {"same": 1, "differs": 0, "unknown": 1}
    assert other[0]["merged"] is True
    assert other[0]["summary"] == {"same": 0, "differs": 1, "unknown": 0}
    comparisons.polled("aa", coordinator)
    assert len(written) == 1
    comparisons.add("aa", "t", {}, written.append)
    comparisons.drop("aa")
    comparisons.drop("aa")
    assert comparisons.pending == {}


def test_merge_state(monkeypatch: Any) -> None:
    assert merge_state("reef-wave", None, "t", {}) is False
    calls: list[Any] = []

    def _merger(coordinator: Any, topic: str, payload: Any) -> bool:
        calls.append((coordinator, topic, payload))
        return True

    monkeypatch.setitem(strategy.MERGERS, "reef-wave", _merger)
    assert merge_state("reef-wave", "c", "t", {"a": 1}) is True
    assert calls == [("c", "t", {"a": 1})]


def test_poll_control() -> None:
    one = SimpleNamespace(update_interval=timedelta(seconds=30))
    two = SimpleNamespace(update_interval=None)
    control = PollControl()
    control.set("a", one, timedelta(minutes=10))
    control.set("a", one, timedelta(minutes=5))  # the original is kept
    control.set("b", two, timedelta(minutes=10))
    assert one.update_interval == timedelta(minutes=5)
    assert control.interval("a") == timedelta(minutes=5)
    assert control.interval("zz") is None
    assert control.controlled == {"a", "b"}
    assert control.restore("a") is one
    assert one.update_interval == timedelta(seconds=30)
    assert control.restore("a") is None  # already restored
    # Paused
    control.set("a", one, None)
    assert one.update_interval is None
    # A new coordinator for the same device (reload): its own interval saved
    three = SimpleNamespace(update_interval=timedelta(seconds=60))
    control.set("b", three, timedelta(minutes=10))
    restored = control.restore_all()
    assert len(restored) == 2 and one in restored and three in restored
    assert three.update_interval == timedelta(seconds=60)
    assert one.update_interval == timedelta(seconds=30)
    assert control.controlled == set()

"""Unit tests for `reefbeat/fusion.py`.

The fusion module is pure (no Home Assistant imports): it takes a raw ``probes``
list plus a per-uid history and returns plain values. That makes every branch
directly reachable here — candidate extraction, coherence/spread, the fusion
aggregators, and the single-fault anomaly attribution — without spinning up a
coordinator.
"""

from __future__ import annotations

from typing import Any

from custom_components.redsea.reefbeat import fusion

# ---------------------------------------------------------------------------
# temperature_candidates
# ---------------------------------------------------------------------------


def test_temperature_candidates_non_list_returns_empty() -> None:
    """A non-list payload (e.g. missing dashboard) yields no candidates."""
    assert fusion.temperature_candidates(None) == []
    assert fusion.temperature_candidates("nope") == []


def test_temperature_candidates_tags_status_and_availability() -> None:
    """Each temperature-capable probe is tagged with value/status/availability.

    Exercises every ``reason`` branch (disabled / disconnected / no_value) plus
    the healthy case, the non-dict and unknown-type skips, and the bool guard.
    """
    probes: list[Any] = [
        "not-a-dict",  # skipped
        {"type": "light", "uid": "0xL"},  # unknown temp type -> skipped
        {
            "type": "temperature",
            "uid": "0xT",
            "name": "Temp",
            "value": 25.0,
            "status": "connected",
        },
        {"type": "ec", "uid": "0xE", "temp_value": 25.4, "status": "connected"},
        {"type": "ph", "uid": "0xP", "temp_value": 24.9, "status": "disabled"},
        {"type": "ato", "uid": "0xA", "temp_value": 25.1, "status": "disconnected"},
        {"type": "temperature", "uid": "0xN", "value": None, "status": "connected"},
        {"type": "temperature", "uid": "0xB", "value": True, "status": "connected"},
    ]
    cands = fusion.temperature_candidates(probes)
    by_uid = {c["uid"]: c for c in cands}

    # Only temperature-capable dict probes survive.
    assert set(by_uid) == {"0xT", "0xE", "0xP", "0xA", "0xN", "0xB"}

    assert by_uid["0xT"]["available"] is True
    assert by_uid["0xT"]["reason"] is None
    assert by_uid["0xT"]["name"] == "Temp"

    # Embedded temperature read from temp_value; name falls back to uid.
    assert by_uid["0xE"]["value"] == 25.4
    assert by_uid["0xE"]["name"] == "0xE"

    assert by_uid["0xP"]["reason"] == "disabled"
    assert by_uid["0xP"]["available"] is False
    assert by_uid["0xA"]["reason"] == "disconnected"

    # Non-numeric and boolean readings are treated as "no value".
    assert by_uid["0xN"]["reason"] == "no_value"
    assert by_uid["0xN"]["value"] is None
    assert by_uid["0xB"]["reason"] == "no_value"
    assert by_uid["0xB"]["value"] is None


# ---------------------------------------------------------------------------
# change_over_window
# ---------------------------------------------------------------------------


def test_change_over_window_empty_returns_none() -> None:
    assert fusion.change_over_window([], now=1000.0) is None


def test_change_over_window_too_few_points_in_window_returns_none() -> None:
    """Only one sample falls inside the window -> not enough to judge."""
    now = 10_000.0
    samples = [(now - 999_999, 20.0), (now, 21.0)]  # first is outside the window
    assert fusion.change_over_window(samples, now=now) is None


def test_change_over_window_span_too_short_returns_none() -> None:
    """Two samples closer together than ``min_span`` -> untrusted."""
    now = 10_000.0
    samples = [(now - 100, 20.0), (now, 21.0)]  # 100s < 600s default min_span
    assert fusion.change_over_window(samples, now=now) is None


def test_change_over_window_returns_signed_change() -> None:
    now = 10_000.0
    samples = [(now - 700, 20.0), (now, 21.5)]
    assert fusion.change_over_window(samples, now=now) == 1.5


# ---------------------------------------------------------------------------
# _drift_culprit
# ---------------------------------------------------------------------------


def _valued(*uids: str) -> list[dict[str, Any]]:
    return [{"uid": u, "name": u, "value": 25.0} for u in uids]


def test_drift_culprit_no_history_returns_none() -> None:
    assert fusion._drift_culprit(_valued("a", "b"), {}, now=0.0, threshold=0.5) is None


def test_drift_culprit_below_threshold_returns_none() -> None:
    now = 10_000.0
    history = {
        "a": [(now - 700, 20.0), (now, 20.2)],
        "b": [(now - 700, 20.0), (now, 20.05)],
    }
    assert fusion._drift_culprit(_valued("a", "b"), history, now, threshold=0.5) is None


def test_drift_culprit_runner_up_within_margin_returns_none() -> None:
    """Two probes drift almost equally -> ambiguous, blame nobody."""
    now = 10_000.0
    history = {
        "a": [(now - 700, 20.0), (now, 21.0)],  # +1.0
        "b": [(now - 700, 20.0), (now, 20.9)],  # +0.9 (within 0.25 margin)
    }
    assert fusion._drift_culprit(_valued("a", "b"), history, now, threshold=0.5) is None


def test_drift_culprit_clear_drifter_wins() -> None:
    now = 10_000.0
    history = {
        "a": [(now - 700, 20.0), (now, 21.0)],  # +1.0
        "b": [(now - 700, 20.0), (now, 20.1)],  # +0.1
    }
    assert fusion._drift_culprit(_valued("a", "b"), history, now, threshold=0.5) == "a"


# ---------------------------------------------------------------------------
# _worst_extreme
# ---------------------------------------------------------------------------


def _v(uid: str, value: float) -> dict[str, Any]:
    return {"uid": uid, "name": uid, "value": value}


def test_worst_extreme_needs_three_sources() -> None:
    assert fusion._worst_extreme([_v("a", 20), _v("b", 25)], threshold=0.5) is None


def test_worst_extreme_low_outlier() -> None:
    got = fusion._worst_extreme([_v("a", 15), _v("b", 20), _v("c", 20)], threshold=0.5)
    assert got == ("a", "outlier_low")


def test_worst_extreme_high_outlier() -> None:
    got = fusion._worst_extreme([_v("a", 20), _v("b", 20), _v("c", 25)], threshold=0.5)
    assert got == ("c", "outlier_high")


def test_worst_extreme_within_threshold_returns_none() -> None:
    got = fusion._worst_extreme(
        [_v("a", 20.0), _v("b", 20.1), _v("c", 20.2)], threshold=0.5
    )
    assert got is None


def test_worst_extreme_high_side_within_threshold_returns_none() -> None:
    # dev_hi > dev_lo but still under threshold -> no culprit (else-branch False).
    got = fusion._worst_extreme(
        [_v("a", 20.0), _v("b", 20.0), _v("c", 20.3)], threshold=0.5
    )
    assert got is None


# ---------------------------------------------------------------------------
# _closest_to_baseline
# ---------------------------------------------------------------------------


def test_closest_to_baseline_uses_history_mean() -> None:
    now = 10_000.0
    valued = [_v("a", 20.0), _v("b", 30.0)]
    history = {"a": [(now - 100, 21.0)], "b": [(now - 100, 21.0)]}  # baseline ~21
    keep = fusion._closest_to_baseline(valued, history, now)
    assert keep["uid"] == "a"


def test_closest_to_baseline_falls_back_to_current_mean() -> None:
    now = 10_000.0
    valued = [_v("a", 20.0), _v("b", 24.0)]
    # No history -> baseline = current mean (22); both are 2 away, min() keeps first.
    keep = fusion._closest_to_baseline(valued, {}, now)
    assert keep["uid"] in {"a", "b"}


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------


def _cand(
    uid: str, value: float | None, available: bool = True, reason: str | None = None
) -> dict[str, Any]:
    return {
        "uid": uid,
        "name": uid,
        "value": value,
        "available": available,
        "reason": reason,
    }


def test_detect_anomalies_structural_culprit_and_coherent() -> None:
    cands = [
        _cand("a", 25.0),
        _cand("b", None, available=False, reason="disconnected"),
    ]
    res = fusion.detect_anomalies(cands, {}, threshold=0.5, now=0.0)
    assert res["incoherent"] is False
    assert res["unknown"] is False
    assert {c["uid"] for c in res["culprits"]} == {"b"}
    assert [c["uid"] for c in res["clean"]] == ["a"]


def test_detect_anomalies_incoherent_two_probes_unknown() -> None:
    """Two disagreeing probes with no history: cannot attribute -> unknown."""
    cands = [_cand("a", 24.0), _cand("b", 26.0)]
    res = fusion.detect_anomalies(cands, {}, threshold=0.5, now=0.0)
    assert res["incoherent"] is True
    assert res["unknown"] is True
    assert res["culprits"] == []


def test_detect_anomalies_incoherent_two_probes_drift_attributed() -> None:
    now = 10_000.0
    cands = [_cand("a", 24.0), _cand("b", 26.0)]
    history = {
        "a": [(now - 700, 24.0), (now, 24.0)],  # steady
        "b": [(now - 700, 24.5), (now, 26.0)],  # +1.5 clear drift
    }
    res = fusion.detect_anomalies(cands, history, threshold=0.5, now=now)
    assert res["incoherent"] is True
    assert res["unknown"] is False
    culprit = {c["uid"] for c in res["culprits"]}
    assert culprit == {"b"}
    assert [c["uid"] for c in res["clean"]] == ["a"]


def test_detect_anomalies_incoherent_extreme_outlier() -> None:
    """Three probes, one far off: the extreme is blamed via _worst_extreme."""
    cands = [_cand("a", 25.0), _cand("b", 25.0), _cand("c", 28.0)]
    res = fusion.detect_anomalies(cands, {}, threshold=0.5, now=0.0)
    assert res["incoherent"] is True
    assert {c["uid"] for c in res["culprits"]} == {"c"}
    reasons = res["culprits"][0]["reasons"]
    assert "outlier_high" in reasons


def test_detect_anomalies_never_excludes_everyone() -> None:
    """Defensive fallback: if all readings would be excluded, keep the one
    closest to the trailing-hour baseline (still flagged)."""
    now = 10_000.0
    # Same uid appears available and disconnected -> structural flag removes the
    # only available reading, so `clean` would be empty without the fallback.
    cands = [
        _cand("x", 25.0),
        _cand("x", None, available=False, reason="disconnected"),
    ]
    history = {"x": [(now - 100, 25.0)]}
    res = fusion.detect_anomalies(cands, history, threshold=0.5, now=now)
    assert [c["uid"] for c in res["clean"]] == ["x"]
    assert {c["uid"] for c in res["culprits"]} == {"x"}


# ---------------------------------------------------------------------------
# temperature_sources
# ---------------------------------------------------------------------------


def test_temperature_sources_non_list_returns_empty() -> None:
    assert fusion.temperature_sources(None) == []


def test_temperature_sources_filters_and_collects() -> None:
    probes: list[Any] = [
        "not-a-dict",  # skipped
        {"type": "temperature", "uid": "0xT", "name": "T", "value": 25.0},
        {"type": "ec", "uid": "0xE", "temp_value": 25.4},
        {"type": "ph", "uid": "0xP", "temp_value": "bad", "status": "connected"},
        {"type": "temperature", "uid": "0xD", "value": 24.0, "status": "disabled"},
        {"type": "light", "uid": "0xL", "value": 1},  # non-temp type skipped
        {"type": "temperature", "uid": "0xB", "value": True},  # bool skipped
    ]
    out = fusion.temperature_sources(probes)
    uids = {s["uid"] for s in out}
    assert uids == {"0xT", "0xE"}
    assert next(s for s in out if s["uid"] == "0xE")["name"] == "0xE"


# ---------------------------------------------------------------------------
# _median / fuse / spread / is_coherent
# ---------------------------------------------------------------------------


def test_median_odd_and_even() -> None:
    assert fusion._median([3.0, 1.0, 2.0]) == 2.0
    assert fusion._median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_fuse_methods() -> None:
    values = [20.0, 22.0, 30.0]
    assert fusion.fuse(values, "mean") == 24.0
    assert fusion.fuse(values, "min") == 20.0
    assert fusion.fuse(values, "max") == 30.0
    assert fusion.fuse(values, "median") == 22.0
    # Unknown method falls back to the robust median.
    assert fusion.fuse(values, "bogus") == 22.0


def test_fuse_empty_returns_none() -> None:
    assert fusion.fuse([], "mean") is None


def test_spread() -> None:
    assert fusion.spread([]) is None
    assert fusion.spread([20.0, 20.4, 21.0]) == 1.0


def test_is_coherent() -> None:
    assert fusion.is_coherent([25.0]) is None  # single source
    assert fusion.is_coherent([25.0, 25.3], threshold=0.5) is True
    assert fusion.is_coherent([25.0, 26.0], threshold=0.5) is False


# ---------------------------------------------------------------------------
# summarise
# ---------------------------------------------------------------------------


def test_summarise_normalises_method_and_reports() -> None:
    probes = [
        {"type": "temperature", "uid": "0xT", "value": 25.0},
        {"type": "ec", "uid": "0xE", "temp_value": 25.6},
    ]
    got = fusion.summarise(probes, method="bogus", threshold=0.5)
    assert got["count"] == 2
    assert got["fused"] is not None
    assert got["spread"] == 0.6000000000000014 or round(got["spread"], 3) == 0.6
    assert got["coherent"] is False
    assert got["method"] == fusion.DEFAULT_METHOD  # invalid method normalised
    assert got["threshold"] == 0.5


def test_summarise_keeps_valid_method() -> None:
    got = fusion.summarise([], method="mean")
    assert got["method"] == "mean"
    assert got["count"] == 0
    assert got["fused"] is None

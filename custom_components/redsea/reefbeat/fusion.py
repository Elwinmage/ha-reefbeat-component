"""Temperature fusion & coherence for multi-probe RSCONTROL setups.

A ReefControl hub often carries several temperature readings at once: a
dedicated ``temperature`` probe plus the temperature embedded in the ``ec``
(salinity), ``ph`` and ``ato`` probes. ReefBeat shows each in isolation; this
module adds two things it does not offer:

- a **coherence** check — how far apart the readings are — flagging a probe
  that has drifted or a bad contact before it silently skews automations;
- a **fusion** value — a single robust temperature (median by default) the
  user can drive automations from instead of picking one probe arbitrarily.

Everything here is pure: it takes the raw ``probes`` list (as served on
``/dashboard``) and returns plain values, so it is trivially testable and free
of Home Assistant imports.
"""

from __future__ import annotations

from typing import Any, cast

# Aggregation strategies exposed to the user through the fusion-method select.
FUSION_METHODS = ("median", "mean", "min", "max")
DEFAULT_METHOD = "median"

# Default coherence threshold in °C. Matches the ``temp_hysteresis`` the RSPower
# firmware itself uses, so "incoherent" means the spread exceeds what the device
# already treats as noise.
DEFAULT_THRESHOLD = 0.5

# Probe ``status`` values meaning the probe is unplugged from the hub. While
# unplugged, the hub answers 503 to every per-probe request (reading, offset).
DISCONNECTED_STATUSES: frozenset[str] = frozenset(
    {"disconnected", "not_connected", "offline"}
)


def is_probe_disconnected(probe: Any) -> bool:
    """Whether a ``/dashboard.probes`` entry reports an unplugged probe.

    A missing or unknown status counts as connected, so a firmware that does
    not report it keeps the previous behaviour.
    """
    if not isinstance(probe, dict):
        return False
    status: Any = cast(dict[str, Any], probe).get("status")
    return isinstance(status, str) and status.lower() in DISCONNECTED_STATUSES


# Probe types whose embedded temperature counts as a source, and the field the
# reading lives in on the dashboard payload.
_EMBEDDED_TEMP_TYPES = {"ec": "temp_value", "ph": "temp_value", "ato": "temp_value"}

# Temperature-capable probe types and the field their reading lives in.
_TEMP_FIELD = {
    "temperature": "value",
    "ec": "temp_value",
    "ph": "temp_value",
    "ato": "temp_value",
}

# History window and drift tuning for anomaly attribution.
HISTORY_WINDOW_S = 3600  # look back ~1h
DRIFT_MIN_SPAN_S = 600  # need >=10 min of samples before trusting a drift verdict


def temperature_candidates(probes: Any) -> list[dict[str, Any]]:
    """Every temperature-capable probe, whether or not it currently reads.

    Unlike :func:`temperature_sources`, this keeps probes that are disconnected,
    disabled or reporting a non-numeric value, tagging each with:

    - ``value``: the numeric reading, or ``None`` when unusable;
    - ``status``: the probe's ``status`` string;
    - ``available``: True when the probe has a usable numeric reading;
    - ``reason``: why it is unusable (``disabled`` / ``disconnected`` /
      ``no_value``), or ``None`` when available.

    This is the input to anomaly detection, which must reason about missing
    probes, not just the ones that read.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(probes, list):
        return out
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        ptype = str(probe.get("type", "")).lower()
        field = _TEMP_FIELD.get(ptype)
        if field is None:
            continue
        status = str(probe.get("status", "") or "").lower()
        raw = probe.get(field)
        value = (
            float(raw)
            if isinstance(raw, (int, float)) and not isinstance(raw, bool)
            else None
        )
        reason: str | None = None
        if status == "disabled":
            reason = "disabled"
        elif status in DISCONNECTED_STATUSES:
            reason = "disconnected"
        elif value is None:
            reason = "no_value"
        out.append(
            {
                "uid": probe.get("uid"),
                "type": ptype,
                "name": probe.get("name") or probe.get("uid"),
                "value": value,
                "status": status,
                "available": reason is None and value is not None,
                "reason": reason,
            }
        )
    return out


def change_over_window(
    samples: Any,
    now: float,
    window: int = HISTORY_WINDOW_S,
    min_span: int = DRIFT_MIN_SPAN_S,
) -> float | None:
    """Signed change (latest − earliest) of a source over the trailing window.

    ``samples`` is a sequence of ``(timestamp, value)``. Returns ``None`` when
    there is not enough history to trust a verdict (fewer than two points, or a
    span shorter than ``min_span``).
    """
    if not samples:
        return None
    pts = [(float(t), float(v)) for t, v in samples if t >= now - window]
    if len(pts) < 2:
        return None
    pts.sort(key=lambda p: p[0])
    if pts[-1][0] - pts[0][0] < min_span:
        return None
    return pts[-1][1] - pts[0][1]


def _drift_culprit(
    valued: list[dict[str, Any]],
    history: dict[str, list],
    now: float,
    threshold: float,
) -> str | None:
    """uid of the probe that drifted clearly the most over the window, else None.

    "Clearly" means its absolute change is the largest, exceeds the real-move
    floor (``threshold``) and beats the runner-up by a margin, so noise or a
    genuine tank-wide temperature change (all probes move together) does not
    wrongly single one out.
    """
    changes: list[tuple[str, float]] = []
    for s in valued:
        uid = s["uid"]
        ch = change_over_window(history.get(uid, []), now)
        if ch is not None:
            changes.append((uid, abs(ch)))
    if not changes:
        return None
    changes.sort(key=lambda c: c[1], reverse=True)
    top_uid, top_ch = changes[0]
    if top_ch < float(threshold):
        return None
    margin = max(float(threshold) / 2.0, 0.2)
    if len(changes) > 1 and top_ch - changes[1][1] < margin:
        return None
    return top_uid


def _worst_extreme(
    valued: list[dict[str, Any]], threshold: float
) -> tuple[str, str] | None:
    """Return the single extreme that disagrees most with the *rest*, if beyond
    threshold.

    A single anomalous probe pulls the overall mean toward itself, so we test
    each extreme against the mean of the *other* readings (the consensus). We
    only ever return one probe — double failures are out of scope — namely the
    min or the max, whichever is further from consensus, and only when that gap
    exceeds the threshold.
    """
    if len(valued) < 3:
        return None
    ordered = sorted(valued, key=lambda c: c["value"])
    lo = ordered[0]
    hi = ordered[-1]
    others_lo = [c["value"] for c in ordered[1:]]
    others_hi = [c["value"] for c in ordered[:-1]]
    dev_lo = (sum(others_lo) / len(others_lo)) - lo["value"]
    dev_hi = hi["value"] - (sum(others_hi) / len(others_hi))
    if dev_lo >= dev_hi:
        if dev_lo > float(threshold):
            return (lo["uid"], "outlier_low")
    else:
        if dev_hi > float(threshold):
            return (hi["uid"], "outlier_high")
    return None


def _closest_to_baseline(
    valued: list[dict[str, Any]], history: dict[str, list], now: float
) -> dict[str, Any]:
    """Pick the reading closest to the trailing-hour baseline.

    Baseline = mean of every sample seen in the last hour, across all sources
    (a stable reference less sensitive to a probe that just went bad). Falls
    back to the current mean when there is no history.
    """
    samples = [
        v for hist in history.values() for (t, v) in hist if t >= now - HISTORY_WINDOW_S
    ]
    if samples:
        baseline = sum(samples) / len(samples)
    else:
        baseline = sum(c["value"] for c in valued) / len(valued)
    return min(valued, key=lambda c: abs(c["value"] - baseline))


def detect_anomalies(
    candidates: list[dict[str, Any]],
    history: dict[str, list],
    threshold: float = DEFAULT_THRESHOLD,
    now: float = 0.0,
) -> dict[str, Any]:
    """Classify temperature candidates into healthy vs anomalous.

    Returns a dict with:
    - ``culprits``: list of ``{uid, name, reasons: [...]}`` — probes to exclude;
    - ``unknown``: True when incoherent but no probe could be blamed;
    - ``clean``: the sources kept for fusion (``{uid, name, value}``);
    - ``incoherent``: whether the *available* readings disagree beyond threshold.

    Attribution (single-fault model): structural failures
    (disabled/disconnected/no value) are always culprits; among available
    readings, a >2-probe disagreement blames the single extreme furthest from
    the others' consensus (when beyond threshold), a 2-probe disagreement blames
    the clear 1h drifter (else unknown), and a clear drifter is always added.
    If everything would be excluded, the reading closest to the trailing-hour
    baseline is kept (still flagged) so fusion never goes blank.
    """
    reasons: dict[str, set] = {}
    names: dict[str, str] = {}
    for c in candidates:
        names[c["uid"]] = c["name"]
    # Structural anomalies first.
    for c in candidates:
        if not c.get("available"):
            reasons.setdefault(c["uid"], set()).add(c.get("reason") or "no_value")

    valued = [c for c in candidates if c.get("available")]
    values = [c["value"] for c in valued]
    sp = spread(values)
    incoherent = len(valued) >= 2 and sp is not None and sp > float(threshold)
    unknown = False

    if incoherent:
        value_culprit = False
        drift_uid = _drift_culprit(valued, history, now, threshold)
        if drift_uid is not None:
            reasons.setdefault(drift_uid, set()).add("drift")
            value_culprit = True
        if len(valued) > 2:
            worst = _worst_extreme(valued, threshold)
            if worst is not None:
                reasons.setdefault(worst[0], set()).add(worst[1])
                value_culprit = True
        if not value_culprit:
            unknown = True

    culprit_uids = set(reasons.keys())
    clean = [
        {"uid": c["uid"], "name": c["name"], "value": c["value"]}
        for c in valued
        if c["uid"] not in culprit_uids
    ]
    # Never exclude everyone: keep the reading closest to the trailing-hour
    # baseline, still flagged, so the fused value never disappears.
    if not clean and valued:
        keep = _closest_to_baseline(valued, history, now)
        clean = [{"uid": keep["uid"], "name": keep["name"], "value": keep["value"]}]

    culprits = [
        {"uid": uid, "name": names.get(uid, uid), "reasons": sorted(reasons[uid])}
        for uid in reasons
    ]
    return {
        "culprits": culprits,
        "unknown": unknown,
        "clean": clean,
        "incoherent": bool(incoherent),
    }


def temperature_sources(probes: Any) -> list[dict[str, Any]]:
    """Collect every usable temperature reading from a ``probes`` list.

    Returns a list of ``{"uid", "type", "name", "value"}`` — one entry per
    dedicated temperature probe and per probe that embeds a temperature
    (ec/ph/ato). Disabled probes and non-numeric readings are skipped.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(probes, list):
        return out
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        if str(probe.get("status", "")).lower() == "disabled":
            continue
        ptype = str(probe.get("type", "")).lower()
        if ptype == "temperature":
            field = "value"
        elif ptype in _EMBEDDED_TEMP_TYPES:
            field = _EMBEDDED_TEMP_TYPES[ptype]
        else:
            continue
        value = probe.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        out.append(
            {
                "uid": probe.get("uid"),
                "type": ptype,
                "name": probe.get("name") or probe.get("uid"),
                "value": float(value),
            }
        )
    return out


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def fuse(values: list[float], method: str = DEFAULT_METHOD) -> float | None:
    """Aggregate readings into a single value using ``method``."""
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    if method == "mean":
        return sum(nums) / len(nums)
    if method == "min":
        return min(nums)
    if method == "max":
        return max(nums)
    # median (default / unknown method falls back to the robust choice)
    return _median(nums)


def spread(values: list[float]) -> float | None:
    """Return max−min of the readings (0 for a single source, None for empty)."""
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return max(nums) - min(nums)


def is_coherent(
    values: list[float], threshold: float = DEFAULT_THRESHOLD
) -> bool | None:
    """Whether the readings agree within ``threshold`` °C.

    None when there are fewer than two sources (nothing to compare).
    """
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if len(nums) < 2:
        return None
    sp = max(nums) - min(nums)
    return sp <= float(threshold)


def summarise(
    probes: Any, method: str = DEFAULT_METHOD, threshold: float = DEFAULT_THRESHOLD
) -> dict[str, Any]:
    """One-shot: sources + fused value + spread + coherence, for attributes."""
    sources = temperature_sources(probes)
    values = [s["value"] for s in sources]
    return {
        "sources": sources,
        "count": len(sources),
        "fused": fuse(values, method),
        "spread": spread(values),
        "coherent": is_coherent(values, threshold),
        "method": method if method in FUSION_METHODS else DEFAULT_METHOD,
        "threshold": float(threshold),
    }

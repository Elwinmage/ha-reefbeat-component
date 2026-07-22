"""Unit tests for the socket/port effective-state derivation.

The helper collapses the ``(mode, state)`` pair returned by the firmware
into a single meaningful value, so the socket/port state sensor never
surfaces the literal ``"unknown"`` that the firmware emits in manual
modes. See ``custom_components.redsea.sensor._effective_socket_state``.
"""

from __future__ import annotations

import pytest

from custom_components.redsea.sensor import _effective_socket_state
from custom_components.redsea.switch import _effective_state_is_on


@pytest.mark.parametrize(
    ("mode", "state", "expected"),
    [
        # Manual overrides win over whatever state the firmware reports —
        # firmware always emits "unknown" here.
        ("on", "unknown", "on"),
        ("off", "unknown", "off"),
        # Manual override still wins if firmware unexpectedly filled state.
        ("on", "standby", "on"),
        ("off", "on", "off"),
        # Programmatic modes: state is authoritative.
        ("schedule", "on", "on"),
        ("schedule", "standby", "standby"),
        ("sensor", "on", "on"),
        ("sensor", "standby", "standby"),
        ("auto", "on", "on"),
        ("feeding", "standby", "standby"),
        ("maintenance", "on", "on"),
        # Fully unknown -> None (leave the sensor as-is / unavailable).
        (None, None, None),
        (None, "on", "on"),
        ("schedule", None, None),
        # Weird cases stay safe: non-string mode is ignored, non-string
        # state falls through to None.
        (42, "on", "on"),
        ("schedule", 42, None),
    ],
)
def test_effective_state_derivation(
    mode: object, state: object, expected: object
) -> None:
    assert _effective_socket_state(mode, state) == expected


# The switch-side helper is a separate function that returns bool | None. We
# validate it here alongside the sensor helper so the "both unknown → None"
# branch is exercised, keeping switch.py at 100% coverage.


@pytest.mark.parametrize(
    ("mode", "state", "expected"),
    [
        # Manual override — the mode string alone answers the question.
        ("on", "unknown", True),
        ("off", "unknown", False),
        # Programmatic modes — the state string answers.
        ("schedule", "on", True),
        ("schedule", "standby", False),
        ("sensor", "on", True),
        ("auto", "standby", False),
        # Nothing usable in either field → leave the attr alone.
        (None, None, None),
        (42, None, None),
        (None, 42, None),
    ],
)
def test_effective_state_is_on(mode: object, state: object, expected: object) -> None:
    assert _effective_state_is_on(mode, state) == expected

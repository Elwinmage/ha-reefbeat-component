"""ReefBeat API package.

This package is a split-out version of the former `reefbeat.py` module.
It re-exports the public API so external imports remain stable.
"""

from __future__ import annotations

# Core helpers / base API
from .api import ReefBeatAPI, parse

# Device/cloud implementations (import and re-export)
from .ato import ReefATOAPI
from .cloud import InvalidAuth, ReefBeatCloudAPI
from .dose import ReefDoseAPI
from .led import ReefLedAPI
from .mat import ReefMatAPI
from .run import ReefRunAPI
from .wave import ReefWaveAPI

__all__ = [
    "ReefBeatAPI",
    "parse",
    "ReefBeatCloudAPI",
    "InvalidAuth",
    "ReefLedAPI",
    "ReefMatAPI",
    "ReefDoseAPI",
    "ReefATOAPI",
    "ReefRunAPI",
    "ReefWaveAPI",
]

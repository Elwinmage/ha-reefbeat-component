# Red Sea ReefBeat - Generated Tests

These tests are intended for `pytest-homeassistant-custom-component`.

## Install test deps

Typical:
- pytest
- pytest-asyncio
- pytest-homeassistant-custom-component

## Run

pytest -q

## Notes
- Network is disabled by monkeypatching `ReefBeatAPI.fetch_data()` to load captured fixture payloads.
- Fixtures included under `tests/fixtures/`.

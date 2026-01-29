# Red Sea ReefBeat - Generated Tests

These tests are intended for `pytest-homeassistant-custom-component`.

## Install test deps

Typical:

- pytest
- pytest-asyncio
- pytest-homeassistant-custom-component

This repo supports two Home Assistant targets via constraints (while `requirements.test.txt` provides minimum versions).

Note: some dependencies are **runtime requirements of the integration** (declared in `custom_components/redsea/manifest.json`).
Home Assistant installs these automatically; for local test runs we install them explicitly.

- **Default (minimums)**: install with lower bounds (pip may choose newer):

  - `pip install -r requirements.test.txt`
  - `python -c "import json; print('\\n'.join(json.load(open('custom_components/redsea/manifest.json'))['requirements']))" | pip install -r /dev/stdin`
- **2025.x compatibility** ("anything 2025 should work"):

  - `python -c "import json; print('\\n'.join(json.load(open('custom_components/redsea/manifest.json'))['requirements']))" | pip install -r /dev/stdin -c constraints-ha2025.txt`
  - `pip install -r requirements.test.txt -c constraints-ha2025.txt`
- **2026.1.x / production**:

  - `python -c "import json; print('\\n'.join(json.load(open('custom_components/redsea/manifest.json'))['requirements']))" | pip install -r /dev/stdin -c constraints-ha2026.txt`
  - `pip install -r requirements.test.txt -c constraints-ha2026.txt`

## Run

pytest -q

## Notes

- Network is disabled by monkeypatching `ReefBeatAPI.fetch_data()` to load captured fixture payloads.
- Fixtures included under `tests/fixtures/`.

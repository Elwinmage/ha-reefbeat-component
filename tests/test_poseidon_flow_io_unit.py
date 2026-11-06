"""Poseidon options flow: keystore export link and import by upload."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.flow import PoseidonOptionsFlowMixin


class _Flow(PoseidonOptionsFlowMixin):
    """The mixin with the few FlowHandler methods the steps call."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def async_abort(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "abort", **kwargs}

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "form", **kwargs}


class _Poseidon:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.keystore = type("K", (), {"with_keys": lambda _self: [1, 2]})()
        self.uploads: list[str] = []

    def export_url(self) -> str:
        return "/api/redsea/poseidon/keystore?authSig=x"

    async def async_import_upload(self, file_id: str) -> tuple[int, int, int]:
        self.uploads.append(file_id)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


async def test_steps_without_poseidon(hass: HomeAssistant) -> None:
    flow: Any = _Flow(hass)
    assert (await flow.async_step_export_keystore())["reason"] == "poseidon_not_running"
    assert (await flow.async_step_import_keystore())["reason"] == "poseidon_not_running"


async def test_export_link(hass: HomeAssistant) -> None:
    hass.data[const.DATA_POSEIDON] = _Poseidon(None)
    flow: Any = _Flow(hass)
    result = await flow.async_step_export_keystore()
    assert result["reason"] == "poseidon_export_link"
    assert result["description_placeholders"] == {
        "link_start": (
            '<a href="/api/redsea/poseidon/keystore?authSig=x" target="_blank">'
        ),
        "link_end": "</a>",
        "count": "2",
        "minutes": str(const.EXPORT_LINK_MINUTES),
    }


def test_export_link_escapes() -> None:
    from custom_components.redsea.poseidon.flow import export_link

    assert export_link('/x?a=1&b="2"')["link_start"] == (
        '<a href="/x?a=1&amp;b=&quot;2&quot;" target="_blank">'
    )


@pytest.mark.parametrize(
    ("result", "error"),
    [(FileNotFoundError("x"), "upload_missing"), (ValueError("x"), "invalid_keystore")],
)
async def test_import_errors(hass: HomeAssistant, result: Any, error: str) -> None:
    poseidon = _Poseidon(result)
    hass.data[const.DATA_POSEIDON] = poseidon
    flow: Any = _Flow(hass)
    form = await flow.async_step_import_keystore()
    assert form["type"] == "form" and form["errors"] == {}
    # The form takes a file uploaded from the browser
    file_id = "9b7b0bcd-0b4a-4f39-9e43-7a50d7f3b6a1"
    assert form["data_schema"]({const.CONF_FILE: file_id}) == {const.CONF_FILE: file_id}
    form = await flow.async_step_import_keystore({const.CONF_FILE: file_id})
    assert form["errors"] == {const.CONF_FILE: error}
    assert poseidon.uploads == [file_id]


async def test_import_done(hass: HomeAssistant) -> None:
    hass.data[const.DATA_POSEIDON] = _Poseidon((1, 2, 3))
    flow: Any = _Flow(hass)
    result = await flow.async_step_import_keystore({const.CONF_FILE: "id"})
    assert result["reason"] == "poseidon_imported"
    assert result["description_placeholders"] == {
        "added": "1",
        "updated": "2",
        "skipped": "3",
    }

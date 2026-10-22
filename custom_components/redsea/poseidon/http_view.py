"""Downloads of the options flow: keystore and rescue script.

Both are generated on each request and never written to disk; both hold the
keys in clear. The views require authentication (administrators only): a
signed link (``authSig``, a few minutes) is what lets a plain browser tab
download them.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aiohttp import web
from homeassistant.components.http.const import KEY_HASS_USER
from homeassistant.helpers.http import KEY_HASS, HomeAssistantView

from . import const
from .manager import get_poseidon


def _admin_poseidon(request: web.Request) -> tuple[Any, web.Response | None]:
    """The running Poseidon, or the response refusing the download."""
    user = request.get(KEY_HASS_USER)
    # Secrets: administrators only
    if user is None or not user.is_admin:
        return None, web.Response(status=HTTPStatus.FORBIDDEN)
    poseidon = get_poseidon(request.app[KEY_HASS])
    if poseidon is None:
        return None, web.Response(status=HTTPStatus.NOT_FOUND)
    return poseidon, None


def _attachment(body: str, content_type: str, filename: str) -> web.Response:
    return web.Response(
        body=body.encode("utf-8"),
        content_type=content_type,
        charset="utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


class PoseidonKeystoreView(HomeAssistantView):
    """GET: the keystore of the running Poseidon, as a JSON attachment."""

    url = const.EXPORT_VIEW_URL
    name = const.EXPORT_VIEW_NAME
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        poseidon, refused = _admin_poseidon(request)
        if refused is not None:
            return refused
        body = json.dumps(poseidon.keystore.as_json(), indent=2, ensure_ascii=False)
        return _attachment(body, "application/json", poseidon.export_filename())


class PoseidonRescueView(HomeAssistantView):
    """GET: the rescue script, with the devices and their keys embedded."""

    url = const.RESCUE_VIEW_URL
    name = const.RESCUE_VIEW_NAME
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        poseidon, refused = _admin_poseidon(request)
        if refused is not None:
            return refused
        body = await request.app[KEY_HASS].async_add_executor_job(
            poseidon.rescue_script
        )
        return _attachment(body, "text/x-python", const.RESCUE_FILE)

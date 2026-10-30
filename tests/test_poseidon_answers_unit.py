"""Messages of the commands of the ReefBeat app relayed by Poseidon."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import answers
from custom_components.redsea.poseidon.answers import RelayedCommands
from custom_components.redsea.poseidon.relay import DOWN, UP
from tests._poseidon_fakes import HWID
from tests.test_poseidon_spy_responses_unit import _state_frame
from tests.test_poseidon_spy_unit import _poseidon
from tests.test_reefbeat_api_unit import _FakeSession, _make_api

COMMAND = f"device/reef-dosing/{HWID}/command"
RESPONSE = f"device/reef-dosing/{HWID}/command-response"


def _command(uuid: str, method: str = "PUT", url: str = "/head/2/settings") -> dict:
    return {"uuid": uuid, "hwid": HWID, "method": method, "url": url, "body": {}}


def _answer(uuid: str, body: Any, status: int = 200) -> dict:
    return {"uuid": uuid, "hwid": HWID, "status": status, "body": body}


# -- commands waiting for their answer ---------------------------------------------


def test_write_commands_wait_for_their_answer() -> None:
    now = [0.0]
    pending = RelayedCommands(clock=lambda: now[0])
    pending.sent(HWID, COMMAND, _command("a"))
    # Reads, other topics, unreadable commands: not kept
    pending.sent(HWID, COMMAND, _command("b", method="GET", url="/dashboard"))
    pending.sent(HWID, RESPONSE, _command("c"))
    pending.sent(HWID, COMMAND, {"uuid": "d", "method": "POST"})
    pending.sent(HWID, COMMAND, {"method": "POST", "url": "/x"})
    pending.sent(HWID, COMMAND, "not a dict")
    pending.sent(HWID, "group/reef-wave/x", _command("e"))
    assert len(pending) == 1
    # Not an answer, or the answer of something else
    assert pending.answered(HWID, COMMAND, _answer("a", {})) is None
    assert pending.answered(HWID, RESPONSE, "x") is None
    assert pending.answered(HWID, RESPONSE, {"status": 200}) is None
    assert pending.answered("other", RESPONSE, _answer("a", {})) is None
    body = {"success": True, "message": "head settings successfully saved"}
    assert pending.answered(HWID, RESPONSE, _answer("a", body)) == (
        "PUT",
        "/head/2/settings",
        200,
        body,
    )
    # Answered once
    assert pending.answered(HWID, RESPONSE, _answer("a", body)) is None


def test_commands_never_answered_expire() -> None:
    now = [0.0]
    pending = RelayedCommands(clock=lambda: now[0])
    pending.sent(HWID, COMMAND, _command("old"))
    now[0] = answers.ANSWER_WAIT_S + 1
    assert pending.answered(HWID, RESPONSE, _answer("old", {})) is None
    for index in range(answers.PENDING_MAX + 5):
        pending.sent(HWID, COMMAND, _command(str(index)))
    assert len(pending) == answers.PENDING_MAX
    pending.clear()
    assert len(pending) == 0


# -- recorded like the answer to a push of Home Assistant ----------------------------


def test_message_of_the_app() -> None:
    api = _make_api(_FakeSession())
    recorded: list[dict[str, Any]] = []
    api.on_message = recorded.append
    body = {"success": True, "message": "settings updated successfully"}
    assert api.record_relayed_answer("POST", "/head/1/settings", 200, body)
    assert api.data["message"]["message"] == "settings updated successfully"
    meta = api.data["message_meta"]
    assert meta["last_message"] and meta["last_message_origin"] == "reefbeat"
    assert meta["last_alert_message"] is None
    [entry] = recorded
    assert (entry["type"], entry["method"], entry["path"], entry["status"]) == (
        "last_message",
        "post",
        "/head/1/settings",
        200,
    )
    assert entry["origin"] == "reefbeat"


def test_alert_of_the_app() -> None:
    api = _make_api(_FakeSession())
    recorded: list[dict[str, Any]] = []
    api.on_message = recorded.append
    alert = {"code": "NoMoreDoseAlert", "message": "the DD has been reached"}
    body = {"success": True, "message": "dose done", "alert": alert}
    assert api.record_relayed_answer("POST", "/head/1/manual", 200, body)
    assert api.data["message"]["alert"] == alert
    assert api.data["message"]["message"] == "dose done"
    assert api.data["message_meta"]["last_alert_message_origin"] == "reefbeat"
    assert [e["type"] for e in recorded] == ["last_alert_message", "last_message"]


def test_failures_of_the_app_are_alerts() -> None:
    api = _make_api(_FakeSession())
    recorded: list[dict[str, Any]] = []
    api.on_message = recorded.append
    # Refused by the firmware, with a message
    body = {"success": False, "message": "head is not calibrated"}
    assert api.record_relayed_answer("POST", "/head/3/manual", 200, body)
    # An error status, with a text or nothing
    assert api.record_relayed_answer("POST", "/x", 404, "Not Found")
    assert api.record_relayed_answer("POST", "/y", None, None)
    assert [(e["type"], e["text"], e["status"]) for e in recorded] == [
        ("last_alert_message", "head is not calibrated", 200),
        ("last_alert_message", "Not Found", 404),
        ("last_alert_message", "0", 0),
    ]
    assert api.data["message"]["alert"] == {"message": "0"}
    # Nothing to tell: a success without a message
    assert not api.record_relayed_answer("POST", "/time", 200, {"epoch": 1})
    assert not api.record_relayed_answer("POST", "/time", 200, {"message": ""})
    assert len(recorded) == 3


def test_clean_message_forgets_the_origin() -> None:
    api = _make_api(_FakeSession())
    api.record_relayed_answer("POST", "/a", 200, {"message": "m"})
    api.record_relayed_answer("POST", "/a", 500, {"message": "e"})
    api.clean_message("All")
    meta = api.data["message_meta"]
    assert meta["last_message_origin"] is None
    assert meta["last_alert_message_origin"] is None


# -- in the manager --------------------------------------------------------------------


class _Api:
    def __init__(self, answer: bool = True, fail: bool = False) -> None:
        self.data: dict[str, Any] = {"sources": []}
        self.calls: list[tuple[Any, ...]] = []
        self.answer = answer
        self.fail = fail

    def record_relayed_answer(self, *args: Any) -> bool:
        self.calls.append(args)
        if self.fail:
            raise RuntimeError("boom")
        return self.answer


def _dosing(hass: HomeAssistant) -> tuple[Any, Any]:
    poseidon, coordinator = _poseidon(hass)
    poseidon.keystore.devices[HWID].type = "reef-dosing"
    poseidon._apply_polling()
    return poseidon, coordinator


async def test_answers_of_the_app_reach_the_message_sensors(
    hass: HomeAssistant,
) -> None:
    poseidon, coordinator = _dosing(hass)
    api = coordinator.my_api = _Api()
    polled: list[str] = []
    coordinator.async_add_listener(lambda: polled.append("listener"))
    body = {"success": True, "message": "head settings successfully saved"}
    poseidon._on_frame(HWID, DOWN, _state_frame(_command("u1"), COMMAND))
    poseidon._on_frame(HWID, UP, _state_frame(_answer("u1", body), RESPONSE))
    assert api.calls == [("PUT", "/head/2/settings", 200, body)]
    # The entities are told, as for a merge: no poll to compare
    assert "listener" in polled and not poseidon._merging
    # A read of the app, an answer to nothing: no message
    poseidon._on_frame(HWID, DOWN, _state_frame(_command("u2", "GET"), COMMAND))
    poseidon._on_frame(HWID, UP, _state_frame(_answer("u2", {"a": 1}), RESPONSE))
    assert len(api.calls) == 1
    await poseidon.async_stop()


async def test_answers_without_message_or_api(hass: HomeAssistant) -> None:
    poseidon, coordinator = _dosing(hass)
    polled: list[str] = []
    coordinator.async_add_listener(lambda: polled.append("listener"))
    for api in (_Api(answer=False), _Api(fail=True), None):
        coordinator.my_api = api
        poseidon._on_frame(HWID, DOWN, _state_frame(_command("u"), COMMAND))
        poseidon._on_frame(HWID, UP, _state_frame(_answer("u", {}), RESPONSE))
    assert polled == []
    await poseidon.async_stop()
    assert len(poseidon._relayed) == 0

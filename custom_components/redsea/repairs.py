"""Repairs of the device groups (virtual LED): see groups.py.

- group_no_cloud: no cloud account lists the lamps of a group the ReefBeat
  app could hold. Fixed by adding the account (the issue then goes by
  itself), or by keeping the group in Home Assistant only (this flow).
- group_mixed_models: a group of several models (G1 and G2, or two G2
  models), some of its lamps still grouped in the ReefBeat app, which would
  drive them apart. Fixed by ungrouping them there (this flow).
- group_conflict: the group changed both in Home Assistant and in the
  ReefBeat app since they were last synchronized. Fixed by choosing which
  one is kept (this flow).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .groups import ISSUE_CONFLICT, ISSUE_MIXED, ISSUE_NO_CLOUD

# Step of each issue, and what its confirmation does on the group
_CONFIRM_STEPS = {
    ISSUE_NO_CLOUD: ("keep_local", "async_keep_local"),
    ISSUE_MIXED: ("ungroup", "async_ungroup_in_cloud"),
}
KEEP_HOME_ASSISTANT = "keep_home_assistant"
KEEP_REEFBEAT = "keep_reefbeat"


class GroupRepairFlow(RepairsFlow):
    """Fix an issue of a group."""

    def __init__(self, kind: str, entry_id: str) -> None:
        self._kind = kind
        self._entry_id = entry_id

    def _group(self) -> Any | None:
        """The group's coordinator, None when it is not loaded."""
        group = self.hass.data.get(DOMAIN, {}).get(self._entry_id)
        return group if hasattr(group, "member_ids") else None

    def _placeholders(self) -> dict[str, str]:
        """The issue's placeholders ({group}, {leds}): a fix flow step shows
        the issue's text, which HA does not fill in by itself."""
        issue = ir.async_get(self.hass).async_get_issue(DOMAIN, self.issue_id)
        return dict(issue.translation_placeholders or {}) if issue else {}

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        if self._group() is None:
            return self.async_abort(reason="group_not_loaded")
        if self._kind == ISSUE_CONFLICT:
            return self.async_show_menu(
                step_id="init",
                menu_options=[KEEP_HOME_ASSISTANT, KEEP_REEFBEAT],
                description_placeholders=self._placeholders(),
            )
        step, _action = _CONFIRM_STEPS[self._kind]
        return self.async_show_form(
            step_id=step, description_placeholders=self._placeholders()
        )

    async def _confirmed(self) -> RepairsFlowResult:
        group = self._group()
        if group is None:
            return self.async_abort(reason="group_not_loaded")
        await getattr(group, _CONFIRM_STEPS[self._kind][1])()
        return self.async_create_entry(data={})

    async def async_step_keep_local(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Keep the group in Home Assistant only."""
        return await self._confirmed()

    async def async_step_ungroup(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Ungroup the lamps in the ReefBeat app."""
        return await self._confirmed()

    async def _resolve(self, keep_home_assistant: bool) -> RepairsFlowResult:
        group = self._group()
        if group is None:
            return self.async_abort(reason="group_not_loaded")
        await group.async_resolve_conflict(keep_home_assistant)
        return self.async_create_entry(data={})

    async def async_step_keep_home_assistant(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """The group of Home Assistant is written to the cloud."""
        return await self._resolve(True)

    async def async_step_keep_reefbeat(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """The group of the ReefBeat app is taken."""
        return await self._resolve(False)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """The fix flow of a group issue."""
    data = data or {}
    return GroupRepairFlow(str(data.get("kind")), str(data.get("entry_id")))

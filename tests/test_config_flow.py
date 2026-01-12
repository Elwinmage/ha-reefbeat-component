
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.redsea.const import (
    ADD_CLOUD_API,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    DOMAIN,
)


async def test_config_flow_cloud_creates_entry(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cloud config flow should create an entry when creds validate."""
    from custom_components.redsea import config_flow as cf

    async def _ok(*args, **kwargs) -> bool:
        return True

    monkeypatch.setattr(cf, "validate_cloud_input", _ok)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == FlowResultType.FORM

    # Step 1: select add type
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONFIG_FLOW_ADD_TYPE: ADD_CLOUD_API},
    )

    assert result2["type"] == FlowResultType.FORM

    # Step 2: provide cloud credentials
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            CONFIG_FLOW_CLOUD_USERNAME: "test@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "pw",
        },
    )

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"]
    # Entry keys are component-defined; just assert username-like value exists.
    assert "test@example.com" in str(result3["data"]).lower()

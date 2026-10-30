/**
 * Message banner date, message history view and its dialog.
 */
import { render } from "lit";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RSMessages } from "../src/base/messages";
import {
  format_long,
  format_short,
  parse_ts,
} from "../src/base/messages_format";
import { RSMessagesHistory } from "../src/base/messages_history";
import { run_action } from "../src/devices/actions";
import { dialogs_device } from "../src/devices/device.dialogs";
import { messages_history } from "../src/devices/messages_history.dialog_func_ext";

class StubBanner extends RSMessages {
  protected override _render(_s = "") {
    return super._render(_s);
  }
}
if (!customElements.get("stub-messages-history-banner"))
  customElements.define("stub-messages-history-banner", StubBanner);

const TS = "2026-10-29T08:22:00+00:00";

function makeDevice(ts: Record<string, string | null> = {}): any {
  return {
    entities: {
      last_message: { entity_id: "sensor.dev_last_message" },
      last_alert_message: { entity_id: "sensor.dev_last_alert_message" },
    },
    device: { elements: [{ primary_config_entry: "entry_1" }] },
    masterOn: true,
    is_on: () => true,
    config: { color: "0,0,0" },
    _ts: ts,
  };
}

function makeHass(
  answer: any = { response: { messages: [], retention_days: 31 } },
  ts: Record<string, string> = {},
): any {
  return {
    language: "fr",
    locale: { language: "fr" },
    states: {
      "sensor.dev_last_message": {
        entity_id: "sensor.dev_last_message",
        state: "ok",
        attributes: { timestamp: ts.last_message ?? TS },
      },
      "sensor.dev_last_alert_message": {
        entity_id: "sensor.dev_last_alert_message",
        state: "",
        attributes: { timestamp: ts.last_alert_message ?? null },
      },
    },
    callService: vi.fn(),
    callWS: vi.fn(async () => answer),
  };
}

async function settle(): Promise<void> {
  for (let i = 0; i < 5; i++) await Promise.resolve();
}

describe("messages_format", () => {
  it("parses ISO timestamps and rejects junk", () => {
    expect(parse_ts(TS)?.toISOString()).toBe("2026-10-29T08:22:00.000Z");
    expect(parse_ts("nope")).toBeNull();
    expect(parse_ts(null)).toBeNull();
    expect(parse_ts("")).toBeNull();
  });

  it("formats short and long dates", () => {
    const hass = { locale: { language: "fr" } };
    const short = format_short(TS, hass);
    expect(short).toMatch(/29/);
    expect(short).toMatch(/10/);
    expect(short).not.toMatch(/2026/);
    expect(format_long(TS, hass)).toMatch(/2026/);
    expect(format_short(undefined, hass)).toBe("");
    expect(format_long("junk", hass)).toBe("");
  });

  it("falls back when the locale is invalid", () => {
    const hass = { locale: { language: "!!" } };
    expect(format_short(TS, hass)).toBe("10-29 08:22");
    expect(format_long(TS, hass)).toBe("2026-10-29 08:22:00");
  });
});

describe("RSMessages banner", () => {
  let container: HTMLDivElement;
  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });
  afterEach(() => container.remove());

  function banner(attrs: Record<string, any>, label?: string): any {
    const m = new StubBanner() as any;
    m.conf = label
      ? { name: "last_alert_message", label }
      : { name: "last_message" };
    m.stateObj = {
      entity_id: "sensor.dev_last_message",
      state: "Done",
      attributes: attrs,
    };
    m._hass = null;
    m.device = makeDevice();
    return m;
  }

  it("starts the text with the date of the message", () => {
    const m = banner({ timestamp: TS });
    render(m._render(""), container);
    const text = container.querySelector("marquee")?.textContent?.trim() ?? "";
    expect(text).toMatch(/29\/10|10\/29/);
    expect(text).toMatch(/· Done$/);
  });

  it("puts the date before the label of an alert", () => {
    const m = banner({ timestamp: TS }, "'⚠'");
    render(m._render(""), container);
    const text = container.querySelector("marquee")?.textContent?.trim();
    expect(text).toMatch(/ · '⚠'Done'⚠'$/);
  });

  it("shows the bare text without a timestamp", () => {
    const m = banner({});
    render(m._render(""), container);
    expect(container.querySelector("marquee")?.textContent?.trim()).toBe(
      "Done",
    );
  });

  it("opens the history dialog on click, even when the device is off", () => {
    const m = banner({ timestamp: TS });
    m.device.masterOn = false;
    const seen: any[] = [];
    m.addEventListener("display-dialog", (e: CustomEvent) =>
      seen.push(e.detail),
    );
    render(m._render(""), container);
    const marquee = container.querySelector("marquee") as HTMLElement;
    const host = vi.fn();
    container.addEventListener("click", host);
    marquee.click();
    expect(seen).toHaveLength(1);
    expect(seen[0].type).toBe("messages_history");
    expect(seen[0].elt).toBe(m);
    // The element's own tap handling does not see the click
    expect(host).not.toHaveBeenCalled();
  });
});

describe("wifi dialog", () => {
  it("shows the cloud aquarium after the cloud account", () => {
    const names = (dialogs_device as any).wifi.content[0].conf.entities.map(
      (e: any) => e.entity,
    );
    expect(names.indexOf("aquarium")).toBe(names.indexOf("cloud_account") + 1);
  });
});

describe("messages_history dialog", () => {
  it("is part of the common device dialogs", () => {
    const d = (dialogs_device as any).messages_history;
    expect(d).toBeDefined();
    expect(d.content[0]).toMatchObject({
      view: "extend",
      extend: "messages_dialog_func_ext",
      re_render: true,
    });
  });

  it("is registered for the extend view", () => {
    const root = document.createElement("div").attachShadow({ mode: "open" });
    root.innerHTML = '<div id="dialog-content"></div>';
    const hass = makeHass();
    const device = makeDevice();
    run_action(
      "messages_dialog_func_ext",
      "messages_history",
      {
        device,
        conf: { name: "last_alert_message" },
      },
      hass,
      root,
    );
    const view = root.querySelector(
      "#device-messages-history",
    ) as RSMessagesHistory;
    expect(view).toBeInstanceOf(RSMessagesHistory);
    expect(view.kind).toBe("last_alert_message");
  });

  it("builds the view once, then only passes hass on", () => {
    const root = document.createElement("div").attachShadow({ mode: "open" });
    root.innerHTML = '<div id="dialog-content"></div>';
    const device = makeDevice();
    const elt = { device, conf: { name: "last_message" } };
    messages_history(elt, makeHass(), root);
    const first = root.querySelector("#device-messages-history") as any;
    const hass2 = makeHass();
    messages_history(elt, hass2, root);
    expect(root.querySelectorAll("#device-messages-history")).toHaveLength(1);
    expect(first.hass).toBe(hass2);
  });

  it("does nothing without a device or a content box", () => {
    const root = document.createElement("div").attachShadow({ mode: "open" });
    messages_history({ device: makeDevice() }, makeHass(), root);
    messages_history({}, makeHass(), root);
    expect(root.querySelector("#device-messages-history")).toBeNull();
  });
});

describe("RSMessagesHistory", () => {
  let view: RSMessagesHistory;
  beforeEach(() => {
    view = document.createElement(
      "redsea-messages-history",
    ) as RSMessagesHistory;
    view.device = makeDevice();
    document.body.appendChild(view);
  });
  afterEach(() => view.remove());

  const ENTRIES = [
    {
      ts: "2026-10-29T08:22:00+00:00",
      type: "last_alert_message",
      text: "Pump stalled",
      method: "post",
      path: "/mode",
      status: 400,
    },
    {
      ts: "2026-10-28T07:00:00+00:00",
      type: "last_message",
      text: "Done",
    },
  ];

  it("asks the integration for the device's entries and lists them", async () => {
    const hass = makeHass({
      response: { messages: ENTRIES, retention_days: 31 },
    });
    view.hass = hass;
    await settle();
    await view.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: "call_service",
      domain: "redsea",
      service: "get_messages",
      service_data: { device_id: "entry_1", msg_type: "All", days: 7 },
      return_response: true,
    });
    const items = view.shadowRoot!.querySelectorAll("li.entry");
    expect(items).toHaveLength(2);
    expect(items[0]!.classList.contains("alert")).toBe(true);
    expect(items[0]!.querySelector(".text")!.textContent).toBe("Pump stalled");
    expect(items[0]!.querySelector(".detail")!.textContent).toBe(
      "POST /mode · 400",
    );
    expect(items[1]!.querySelector(".detail")).toBeNull();
    expect(view.retention).toBe(31);
  });

  it("reloads on a filter, a period or a new message, not on other updates", async () => {
    const hass = makeHass();
    view.hass = hass;
    await settle();
    await view.updateComplete;
    expect(hass.callWS).toHaveBeenCalledTimes(1);

    // Same timestamps: no reload
    view.hass = hass;
    await settle();
    expect(hass.callWS).toHaveBeenCalledTimes(1);

    const buttons = view.shadowRoot!.querySelectorAll(".kinds button");
    (buttons[2] as HTMLButtonElement).click();
    await settle();
    expect(view.kind).toBe("last_alert_message");
    expect(hass.callWS).toHaveBeenCalledTimes(2);

    // Same filter again: nothing
    (buttons[2] as HTMLButtonElement).click();
    await settle();
    expect(hass.callWS).toHaveBeenCalledTimes(2);

    await view.updateComplete;
    const select = view.shadowRoot!.querySelector(
      "select.period",
    ) as HTMLSelectElement;
    select.value = "0";
    select.dispatchEvent(new Event("change"));
    await settle();
    expect(view.period).toBe(0);
    const last = hass.callWS.mock.calls.at(-1)[0];
    expect(last.service_data).toEqual({
      device_id: "entry_1",
      msg_type: "last_alert_message",
    });

    const hass2 = makeHass(undefined, {
      last_alert_message: "2026-10-29T09:00:00+00:00",
    });
    view.hass = hass2;
    await settle();
    expect(hass2.callWS).toHaveBeenCalledTimes(1);
  });

  it("refresh button reloads", async () => {
    const hass = makeHass();
    view.hass = hass;
    await settle();
    await view.updateComplete;
    (view.shadowRoot!.querySelector(".refresh") as HTMLButtonElement).click();
    await settle();
    expect(hass.callWS).toHaveBeenCalledTimes(2);
  });

  it("shows the service error", async () => {
    view.hass = makeHass({
      response: { error: "Device not enabled", messages: [] },
    });
    await settle();
    await view.updateComplete;
    expect(view.shadowRoot!.querySelector(".error")!.textContent).toBe(
      "Device not enabled",
    );
  });

  it("shows a failed call", async () => {
    const hass = makeHass();
    hass.callWS = vi.fn(async () => {
      throw new Error("boom");
    });
    view.hass = hass;
    await settle();
    await view.updateComplete;
    expect(view.error).toBe("boom");
    expect(view.entries).toEqual([]);
  });

  it("shows an empty list", async () => {
    view.hass = makeHass();
    await settle();
    await view.updateComplete;
    expect(view.shadowRoot!.querySelector(".empty")).not.toBeNull();
  });

  it("keeps the newest answer when two requests cross", async () => {
    let first_resolve: (v: any) => void = () => {};
    const hass = makeHass();
    hass.callWS = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            first_resolve = r;
          }),
      )
      .mockImplementationOnce(async () => ({
        response: { messages: [ENTRIES[1]] },
      }));
    view.hass = hass;
    await view.load();
    first_resolve({ response: { messages: ENTRIES } });
    await settle();
    expect(view.entries).toHaveLength(1);
  });

  it("cannot load without Home Assistant or a config entry", async () => {
    view.device = { device: { elements: [] } };
    view.hass = makeHass();
    await settle();
    expect(view.error).not.toBe("");
  });
});

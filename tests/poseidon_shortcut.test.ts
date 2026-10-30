// Tests for the per-device Poseidon shortcut (trident) and its dialog.

import { describe, expect, it, vi } from "vitest";

import { MyElement } from "../src/base/element";
import "../src/base/index";
import { RSDevice } from "../src/devices/device";
import { dialogs_device } from "../src/devices/device.dialogs";
import { COLOR_ERROR_HEX, COLOR_ORANGE_HEX } from "../src/utils/colors";
import {
  POSEIDON_MODE,
  POSEIDON_OFF_COLOR,
  POSEIDON_SHORTCUT,
  poseidon_shortcut,
} from "../src/devices/redsea/poseidon/poseidon.shortcut";

import { config as rsato } from "../src/devices/redsea/rsato/rsato.mapping";
import { config as rscontrol_lite } from "../src/devices/redsea/rscontrol/rscontrollite.mapping";
import { config2 as rscontrol_pro } from "../src/devices/redsea/rscontrol/rscontrolpro.mapping";
import { config2 as rsdose2 } from "../src/devices/redsea/rsdose/rsdose2.mapping";
import { config4 as rsdose4 } from "../src/devices/redsea/rsdose/rsdose4.mapping";
import { config as rsled_g1 } from "../src/devices/redsea/rsled/rsled_g1.mapping";
import { config2 as rsled_g2 } from "../src/devices/redsea/rsled/rsled_g2.mapping";
import { config as rsmat } from "../src/devices/redsea/rsmat/rsmat.mapping";
import { config as rspower6 } from "../src/devices/redsea/rspower/rspower6.mapping";
import { config2 as rspower8 } from "../src/devices/redsea/rspower/rspower8.mapping";
import { config as rsrun } from "../src/devices/redsea/rsrun/rsrun.mapping";
import { config as rswave } from "../src/devices/redsea/rswave/rswave.mapping";

// ── Fixtures ─────────────────────────────────────────────────────────────────

/** A device with (or without) its Poseidon mode switch. */
function makeDevice(mode?: { state: string; silent?: boolean }): any {
  const states: Record<string, any> = {};
  const entities: Record<string, any> = {};
  if (mode) {
    states["switch.dev_poseidon_mode"] = {
      entity_id: "switch.dev_poseidon_mode",
      state: mode.state,
      attributes: { silent: mode.silent ?? false },
    };
  }
  const hass: any = { states, entities, callService: vi.fn() };
  const dev = new RSDevice() as any;
  dev._hass = hass;
  dev.device = { name: "dev", elements: [{ id: "dev", disabled_by: null }] };
  dev.config = { color: "0,0,0", alpha: 1 };
  if (mode) {
    dev.entities = {
      [POSEIDON_MODE]: {
        entity_id: "switch.dev_poseidon_mode",
        translation_key: POSEIDON_MODE,
      },
    };
  }
  dev.masterOn = false;
  return { hass, dev };
}

/** The shortcut as the card draws it. */
function drawn(mode?: { state: string; silent?: boolean }, off?: string) {
  const { hass, dev } = makeDevice(mode);
  const conf: any = poseidon_shortcut({}, off);
  const elt: any = MyElement.create_element(hass, conf, dev);
  return {
    elt,
    hass,
    conf,
    color: elt.evaluate(conf.icon_color),
    cls: elt.get_class(),
    hidden: elt.evaluateCondition(conf.disabled_if),
  };
}

// ── Shortcut element ─────────────────────────────────────────────────────────

describe("poseidon_shortcut", () => {
  it("toggles the mode on hold and opens the dialog on tap", () => {
    const css = { position: "absolute", top: "1%", left: "2%" };
    const conf = poseidon_shortcut(css);
    expect(conf.name).toBe(POSEIDON_SHORTCUT);
    expect(conf.type).toBe("click-image");
    expect(conf.icon).toBe("redsea:trident");
    expect(conf.stateObj).toBeNull();
    expect(conf.off_clickable).toBe(true);
    expect(conf.no_br_if_disabled).toBe(true);
    expect(conf.tap_action).toEqual({
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "poseidon" },
    });
    expect(conf.hold_action).toEqual({
      domain: "switch",
      action: "toggle",
      data: { entity_id: "poseidon_mode" },
    });
    expect(conf.css).toBe(css);
  });

  it("is hidden on a device without the Poseidon switch", () => {
    expect(drawn().hidden).toBe(true);
    expect(drawn({ state: "off" }).hidden).toBe(false);
  });

  it("takes the mapping's colour in Poseidon mode", () => {
    expect(drawn({ state: "on" })).toMatchObject({
      color: COLOR_ERROR_HEX,
      cls: "",
    });
  });

  it("takes the off colour out of it or while unavailable", () => {
    expect(drawn({ state: "off" }).color).toBe(POSEIDON_OFF_COLOR);
    expect(drawn({ state: "unavailable" }).color).toBe(POSEIDON_OFF_COLOR);
    expect(drawn({ state: "off" }, "#fff").color).toBe("#fff");
  });

  it("turns orange and blinks when nothing goes through the relay", () => {
    expect(drawn({ state: "on", silent: true })).toMatchObject({
      color: COLOR_ORANGE_HEX,
      cls: "blink",
    });
    // A silent flag out of Poseidon mode means nothing
    expect(drawn({ state: "off", silent: true })).toMatchObject({
      color: POSEIDON_OFF_COLOR,
      cls: "",
    });
  });

  it("switches the mode on hold, even with the device switched off", async () => {
    const { elt, hass } = drawn({ state: "off" });
    expect(elt.accepts_actions()).toBe(true);
    await elt.run_actions(elt.conf.hold_action);
    expect(hass.callService).toHaveBeenCalledWith("switch", "toggle", {
      entity_id: "switch.dev_poseidon_mode",
    });
  });

  it("opens the poseidon dialog on tap", async () => {
    const { elt } = drawn({ state: "on" });
    const seen: any[] = [];
    elt.addEventListener("display-dialog", (e: CustomEvent) =>
      seen.push(e.detail),
    );
    await elt.run_actions(elt.conf.tap_action);
    expect(seen).toHaveLength(1);
    expect(seen[0].type).toBe("poseidon");
  });

  it("targets a dialog every device loads, with the Poseidon entities", () => {
    const dialog = (dialogs_device as any)[POSEIDON_SHORTCUT];
    expect(dialog.name).toBe(POSEIDON_SHORTCUT);
    const names = dialog.content[0].conf.entities.map((e: any) => e.entity);
    expect(names).toEqual([
      "poseidon_mode",
      "poseidon_strategy",
      "poseidon_poll_pause",
    ]);
    expect((new RSDevice() as any).dialogs[POSEIDON_SHORTCUT]).toBeDefined();
  });

  const MAPPINGS: Record<string, any> = {
    rsato,
    rscontrol_lite,
    rscontrol_pro,
    rsdose2,
    rsdose4,
    rsled_g1,
    rsled_g2,
    rsmat,
    rspower6,
    rspower8,
    rsrun,
    rswave,
  };

  it.each(Object.keys(MAPPINGS))("is placed on the %s view", (model) => {
    const elt = MAPPINGS[model].elements[POSEIDON_SHORTCUT];
    expect(elt).toBeDefined();
    expect(elt.icon).toBe("redsea:trident");
    expect(elt.css.position).toBe("absolute");
    expect(elt.css.top).toMatch(/%$/);
    expect(elt.css.left ?? elt.css.right).toMatch(/%$/);
  });

  it.each(Object.keys(MAPPINGS))(
    "does not sit on another icon of the %s view",
    (model) => {
      const elements = MAPPINGS[model].elements;
      const mine = elements[POSEIDON_SHORTCUT].css;
      for (const key in elements) {
        if (key === POSEIDON_SHORTCUT) continue;
        const css = elements[key]?.css;
        if (!css || css.top !== mine.top) continue;
        const same_left = mine.left !== undefined && css.left === mine.left;
        const same_right = mine.right !== undefined && css.right === mine.right;
        expect(same_left || same_right, key).toBe(false);
      }
    },
  );
});

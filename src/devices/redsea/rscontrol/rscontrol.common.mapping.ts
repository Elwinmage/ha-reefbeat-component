/**
 * Mapping parts shared by the ReefControl Lite and Pro.
 *
 * Every overlay is a full-canvas PNG (same size as the background picture),
 * stacked in declaration order. They are bound to `disabled_if` predicates on
 * the device, which also forces a re-render on every Home Assistant update —
 * that is what keeps their `class` expressions fresh.
 *
 * Probes are laid out in slots under the extension boxes. A slot is placed
 * in % of the hub picture; inside it, the probe picture is placed by
 * `img_css` (in % of the slot width) and everything drawn on it — values,
 * situation bars, cog — is placed in % of that picture, so it stays on the
 * same spot of the probe whatever the card size.
 */

import {
  COLOR_ERROR_HEX,
  COLOR_LEVEL_DANGER_HEX,
  COLOR_LEVEL_DESIRED_HEX,
  COLOR_RS_RGBSTR,
} from "../../../utils/colors";
import { maintenance_shortcut } from "../maintenance/maintenance.shortcut";
import { poseidon_shortcut } from "../poseidon/poseidon.shortcut";

/** Full-canvas overlay, never catching clicks aimed at what lies below. */
const OVERLAY_CSS = {
  position: "absolute",
  top: "0",
  left: "0",
  width: "100%",
  "pointer-events": "none",
};

const OVERLAY_ELT_CSS = {
  display: "block",
  width: "100%",
};

/**
 * Build a full-canvas overlay element.
 * @param name: the entity it is bound to (only used as a render trigger)
 * @param image: the overlay picture
 * @param disabled_if: when to hide it
 * @param cls: optional class expression (blink on fault)
 * @return the element configuration
 */
function overlay(
  name: string,
  image: URL,
  disabled_if: string,
  cls: string = "",
): Record<string, any> {
  const conf: Record<string, any> = {
    name: name,
    type: "click-image",
    image: image,
    disabled_if: disabled_if,
    no_br_if_disabled: true,
    css: OVERLAY_CSS,
    elt_css: OVERLAY_ELT_CSS,
  };
  if (cls) {
    conf.class = cls;
  }
  return conf;
}

/** Blink while the paired power strip is unreachable. */
const POWER_ALERT = "${device.power_link_alert() ? 'blink-alert' : ''}";

/** Blink while the ATO module reports a fault (on a port, or any). */
const ato_alert = (port?: number): string =>
  port === undefined
    ? "${device.ato_fault() ? 'blink-alert' : ''}"
    : `\${device.ato_module_fault(${port}) ? 'blink-alert' : ''}`;

// ── Extension boxes, one set per model ─────────────────────────────────────

export const lite_extends = {
  port_extend_lite: overlay(
    "device_state",
    new URL(
      "../../../img/redsea/RSCONTROL/prot_extend_lite.png",
      import.meta.url,
    ),
    "device.probes_nb() < 1",
  ),
};

export const pro_extends = {
  port_extend_1: overlay(
    "device_state",
    new URL(
      "../../../img/redsea/RSCONTROL/port_exetend_1.png",
      import.meta.url,
    ),
    "device.probes_nb() < 1",
  ),
  port_extend_2: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/port_extend_2.png", import.meta.url),
    "device.max_slot() <= 4",
  ),
};

// ── Links and indicators, identical on both models ─────────────────────────

export const links = {
  link_sense_1: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_1.png", import.meta.url),
    "!device.slot_used(1)",
  ),
  link_sense_2: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_2.png", import.meta.url),
    "!device.slot_used(2)",
  ),
  link_sense_3: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_3.png", import.meta.url),
    "!device.slot_used(3)",
  ),
  // One cable per occupied slot. The fourth takes another route when the
  // second box is drawn (a slot beyond 4 in use), to go around it.
  link_sense_4: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_4.png", import.meta.url),
    "!device.slot_used(4) || device.max_slot() > 4",
  ),
  link_sense_4E: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_4E.png", import.meta.url),
    "!device.slot_used(4) || device.max_slot() <= 4",
  ),
  link_sense_5: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_5.png", import.meta.url),
    "!device.slot_used(5)",
  ),
  link_sense_6: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_6.png", import.meta.url),
    "!device.slot_used(6)",
  ),
  link_sense_7: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_sense_7.png", import.meta.url),
    "!device.slot_used(7)",
  ),
  link_power: overlay(
    "connected_power",
    new URL("../../../img/redsea/RSCONTROL/link_power.png", import.meta.url),
    "!device.has_power_link()",
    POWER_ALERT,
  ),
  is_on_power: overlay(
    "connected_power",
    new URL("../../../img/redsea/RSCONTROL/is_on_power.png", import.meta.url),
    "!device.has_power_link()",
    POWER_ALERT,
  ),
  is_on_sensors: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/is_on_sensors.png", import.meta.url),
    "device.probes_nb() < 1",
  ),
  link_ato_1: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_ato_1.png", import.meta.url),
    "!device.is_ato_port(1)",
    ato_alert(1),
  ),
  link_ato_2: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/link_ato_2.png", import.meta.url),
    "!device.is_ato_port(2)",
    ato_alert(2),
  ),
  // One pump, whichever port drives it.
  ato_pump: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/ato.png", import.meta.url),
    "!device.has_ato_link()",
    ato_alert(),
  ),
  // Water pouring from the outlet while the ATO pump runs, as on the
  // RSATO+: from the nozzle clipped on the wall, x 1575..1597, down to the
  // bottom of the tank, y 1295..2172 of 1952 x 2196. Placed with margins
  // (% of the width) and an aspect ratio, like the reservoir below.
  ato_flow: {
    // The port's own state is on/off, not a speed: the stream runs at the
    // slowest speed of the RSATO+ outlet while the hub is on
    name: "device_state",
    type: "flow-image",
    image: new URL(
      "../../../img/redsea/RSRUN/water_seamless.png",
      import.meta.url,
    ),
    disabled_if: "!device.ato_pump_on()",
    no_br_if_disabled: true,
    hide_when_stopped: true,
    min_duration: 2,
    max_duration: 6,
    css: {
      position: "absolute",
      top: "0",
      left: "80.7%",
      "margin-top": "66.3%",
      width: "1.15%",
      "aspect-ratio": "22 / 877",
      "pointer-events": "none",
    },
    elt_css: {
      // Same tint and direction as the RSATO+ outlet (see its mapping)
      filter: "sepia(1) saturate(4) hue-rotate(175deg) brightness(1.05)",
      "animation-direction": "reverse",
    },
  },
  // Water in the ATO reservoir while the pump runs, as on the RSATO+.
  // Right of the sump wall: x 1689..1948, y 1300..2172 of 1952 x 2196.
  // Placed with margins (% of the width) and an aspect ratio, so it keeps
  // to the picture even when the device box grows taller than it.
  ato_reservoir: {
    name: "device_state",
    type: "water-level",
    disabled_if: "!device.ato_pump_on()",
    no_br_if_disabled: true,
    // Water line over the pump, below the top of the wall
    level: 83,
    show_value: false,
    wave: true,
    css: {
      position: "absolute",
      top: "0",
      left: "86.5%",
      "margin-top": "66.6%",
      width: "13.3%",
      "aspect-ratio": "259 / 872",
      "pointer-events": "none",
    },
  },
  is_on_12v_1: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/is_on_12v_1.png", import.meta.url),
    "!device.is_port_on(1)",
  ),
  is_on_12v_2: overlay(
    "device_state",
    new URL("../../../img/redsea/RSCONTROL/is_on_12v_2.png", import.meta.url),
    "!device.is_port_on(2)",
  ),
  rspower6: overlay(
    "connected_power",
    new URL("../../../img/redsea/RSCONTROL/rspower6.png", import.meta.url),
    "!device.has_power_link() || device.linked_power_model() !== 'RSPOWER6'",
    POWER_ALERT,
  ),
  // Click area over the paired power strip, opening its own card. Placed
  // with margins (% of the width) so it keeps to the picture even when the
  // device box grows taller than it.
  rspower_link: {
    name: "connected_power",
    type: "common-button",
    stateObj: null,
    disabled_if: "!device.has_power_link()",
    no_br_if_disabled: true,
    tap_action: {
      domain: "redsea_ui",
      action: "show_device",
      data: { hwid: "${device.linked_power_hwid()}" },
    },
    css: {
      position: "absolute",
      top: "0",
      left: "0",
      // Strip picture: x 104..1118, y 245..453 of 1952 x 2196
      "margin-left": "5.3%",
      "margin-top": "12.6%",
      width: "52%",
      "aspect-ratio": "1014 / 208",
      cursor: "pointer",
      // Invisible: the strip picture is drawn by the overlays
      "--button-bg-color": "transparent",
    },
  },
  rspower8: overlay(
    "connected_power",
    new URL("../../../img/redsea/RSCONTROL/rspower8.png", import.meta.url),
    "!device.has_power_link() || device.linked_power_model() !== 'RSPOWER8'",
    POWER_ALERT,
  ),
};

/**
 * What stays on the card while the hub is switched off: its on/off switch
 * and the pictures of the hardware (extension boxes, cables, the paired
 * strip, an ATO pump). Readings, settings, the buzzer and every "powered"
 * light go, since the hub measures and drives nothing. Keys a model does not
 * declare are simply ignored.
 */
export const off_keep: string[] = [
  "device_state",
  "port_extend_lite",
  "port_extend_1",
  "port_extend_2",
  "link_sense_1",
  "link_sense_2",
  "link_sense_3",
  "link_sense_4",
  "link_sense_4E",
  "link_sense_5",
  "link_sense_6",
  "link_sense_7",
  "link_power",
  "link_ato_1",
  "link_ato_2",
  "ato_pump",
  "rspower6",
  "rspower8",
];

// ── Device-level widgets ───────────────────────────────────────────────────

export const widgets = {
  last_message: {
    name: "last_message",
    type: "redsea-messages",
    // Absolutely positioned: never emit a <br> that shifts the flow
    no_br_if_disabled: true,
    // Above the power strip, left of the hub
    css: {
      flex: "0 0 auto",
      position: "absolute",
      width: "60%",
      height: "15px",
      top: "1%",
      left: "0.5%",
    },
    "elt.css": {
      "background-color": "rgba(220,220,220,0.7)",
    },
  },
  last_alert_message: {
    name: "last_alert_message",
    type: "redsea-messages",
    // Absolutely positioned: never emit a <br> that shifts the flow
    no_br_if_disabled: true,
    label: "'⚠'",
    css: {
      color: "red",
      flex: "0 0 auto",
      position: "absolute",
      width: "60%",
      height: "20px",
      top: "4.5%",
      left: "0.5%",
    },
    "elt.css": {
      "background-color": "rgba(240,200,200,0.7)",
    },
  },
  device_state: {
    name: "device_state",
    type: "click-image",
    icon: "state",
    icon_color: "red",
    master: true,
    tap_action: {
      domain: "switch",
      action: "toggle",
      data: "default",
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "2%",
      right: "28%",
    },
  },
  maintenance: {
    name: "maintenance",
    type: "click-image",
    icon: "state",
    icon_color: "red",
    master: true,
    tap_action: {
      domain: "switch",
      action: "toggle",
      data: "default",
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "2%",
      right: "23%",
    },
  },
  configuration: {
    name: "configuration",
    type: "click-image",
    icon: "mdi:cog",
    icon_color: COLOR_ERROR_HEX,
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: {
        type: "config",
      },
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "2%",
      right: "18%",
    },
  },

  wifi_quality: {
    name: "wifi_quality",
    type: "common-sensor",
    master: true,
    label: false,
    icon: true,
    icon_color: COLOR_ERROR_HEX,
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "wifi" },
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      width: "5.5%",
      height: "2%",
      top: "2%",
      right: "12%",
    },
  },
  // Hub-wide buzzer, on the hub's status LED. Opens its settings.
  // Maintenance tasks of the hub: under the settings cog, level with the mode
  maintenance_tasks: maintenance_shortcut({
    flex: "0 0 auto",
    position: "absolute",
    top: "1.8%",
    right: "7%",
  }),
  // Poseidon mode: hold to switch it, tap for its settings. Under the
  // wifi, left of the buzzer LED
  poseidon: poseidon_shortcut(
    {
      flex: "0 0 auto",
      position: "absolute",
      top: "6%",
      right: "12%",
    },
    "rgba(255,255,255,0.55)",
  ),
  buzzer: {
    name: "buzzer_active",
    type: "click-image",
    icon: "mdi:bell-alert",
    // Green while quiet, red and blinking while it sounds, steady red once
    // the alarm was dismissed
    icon_color: `\${state === 'on' || entity.buzzer_dismissed?.state === 'on' ? '${COLOR_LEVEL_DANGER_HEX}' : '${COLOR_LEVEL_DESIRED_HEX}'}`,
    class: "${state === 'on' ? 'blink-alert' : ''}",
    // Re-rendered on every update: the colour also follows buzzer_dismissed
    disabled_if: "false",
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "buzzer_conf" },
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      // The LED, right of the knob: x 1780, y 170 of 1952 x 2196
      top: "7.7%",
      left: "91.2%",
      transform: "translate(-50%, -50%)",
      "line-height": "0",
      cursor: "pointer",
    },
  },
  mode: {
    name: "mode",
    type: "common-sensor",
    translate_values: true,
    css: {
      position: "absolute",
      "text-align": "center",
      "padding-left": "20px",
      "padding-right": "20px",
      "padding-top": "4px",
      "padding-bottom": "4px",
      top: "7%",
      right: "15%",
      width: "19%",
      color: "rgba(255,255,255,0.5)",
      "font-weight": "bolder",
    },
  },
};

// ── Picture layer ──────────────────────────────────────────────────────────
//
// Everything below is placed in % of the hub picture (1952 x 2196), in a
// layer tied to its size, so it stays on the picture whatever the card size.

/**
 * Sockets of the paired power strip, per model: left edges, top, width and
 * height of each socket frame. A powered socket gets a light red mask.
 */
export const power_sockets = {
  RSPOWER6: {
    lefts: [207, 352, 496, 640, 785, 929].map((x) => (x / 1952) * 100),
    top: (306 / 2196) * 100,
    width: (125 / 1952) * 100,
    height: (130 / 2196) * 100,
  },
  RSPOWER8: {
    lefts: [195, 305, 415, 525, 635, 745, 853, 962].map(
      (x) => (x / 1952) * 100,
    ),
    top: (320 / 2196) * 100,
    width: (97 / 1952) * 100,
    // Lengthened downwards in the same proportion as the 6-socket strip
    // (109 -> 130)
    height: (98 / 2196) * 100,
  },
};

/** Recap of the readings, between the power strip and the probes. */
export const summary = {
  css: {
    top: "29%",
    left: "1%",
    width: "68%",
    height: "3.6%",
  },
};

/**
 * 12V ports: a square box centred on each port connector, holding the
 * settings cog (on the connector) and the consumption (above it, on the hub
 * face). Inside, % are of the box, and sizes follow its width (cqw).
 */
const port_common = {
  css: {
    position: "absolute",
    top: "24.1%",
    width: "5.2%",
    transform: "translate(-50%, -50%)",
  },
  elements: {
    port_conf: {
      name: "port_mode",
      type: "click-image",
      icon: "mdi:cog",
      icon_color: COLOR_RS_RGBSTR,
      // Shown for every port, a port not installed yet included (its editor
      // installs it on save), but the ATO module's: see ato_conf
      disabled_if: "!!entity.port_ato_status",
      no_br_if_disabled: true,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: { type: "port_conf" },
      },
      css: {
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        "line-height": "0",
        "--mdc-icon-size": "70cqw",
        cursor: "pointer",
      },
    },
    // The ATO module (Red Sea ATO kit) in place of the cog on its port: red
    // and blinking while a fault stops it. Opens its settings.
    ato_conf: {
      name: "port_ato_status",
      type: "click-image",
      icon: "mdi:water-pump",
      icon_color: `\${entity.port_ato_fault?.state === 'on' ? '${COLOR_LEVEL_DANGER_HEX}' : '${COLOR_RS_RGBSTR}'}`,
      class: "${entity.port_ato_fault?.state === 'on' ? 'blink-alert' : ''}",
      disabled_if: "!entity.port_ato_status",
      no_br_if_disabled: true,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: { type: "ato_conf" },
      },
      css: {
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        "line-height": "0",
        "--mdc-icon-size": "70cqw",
        cursor: "pointer",
      },
    },
    port_consumption: {
      name: "port_consumption",
      type: "common-sensor",
      round: 1,
      disabled_if: "!entity.port_consumption",
      no_br_if_disabled: true,
      tap_action: {
        domain: "redsea_ui",
        action: "more-info",
        data: "port_consumption",
      },
      css: {
        position: "absolute",
        top: "-130%",
        left: "-50%",
        width: "200%",
        transform: "translateY(-50%)",
        "text-align": "center",
        "white-space": "nowrap",
        "font-size": "clamp(7px, 32cqw, 14px)",
        "font-weight": "bold",
        color: "rgba(255,255,255,0.8)",
        "text-shadow": "0 0 3px rgba(0,0,0,0.9)",
        cursor: "pointer",
      },
    },
  },
};

/** The Lite's single port, under its "12V" mark. */
export const lite_ports = {
  nb: 1,
  common: port_common,
  port_1: { id: 1, css: { left: "83.7%" } },
};

/** The Pro's two ports; each cog carries its port number. */
export const pro_ports = {
  nb: 2,
  common: port_common,
  port_1: {
    id: 1,
    css: { left: "82.8%" },
    elements: { port_conf: { icon: "redsea:cog-1" } },
  },
  port_2: {
    id: 2,
    css: { left: "88.7%" },
    elements: { port_conf: { icon: "mdi:cog-pause" } },
  },
};

// ── Probe slots ────────────────────────────────────────────────────────────

/**
 * Shared look of a value printed on a probe. `top` is the centre of the
 * text in % of the probe picture: the text is centred on it, so a font
 * clamped at its minimum or maximum size still sits on the same spot.
 * The font follows the probe width (cqw of the probe box).
 */
const VALUE_CSS = {
  position: "absolute",
  left: "-20%",
  width: "140%",
  transform: "translateY(-50%)",
  "text-align": "center",
  "font-size": "clamp(9px, 17cqw, 16px)",
  "font-weight": "bold",
  "line-height": "1.1",
  "white-space": "nowrap",
  "text-shadow": "0 0 3px rgba(0,0,0,0.9)",
  cursor: "pointer",
};

/**
 * Cog opening the probe settings, centred on the small dot of the probe
 * head (`top` / `left` are that dot, in % of the picture).
 */
const COG_CSS = {
  position: "absolute",
  "aspect-ratio": "1/1",
  "line-height": "0",
  "--mdc-icon-size": "60cqw",
  cursor: "pointer",
};

/**
 * Slot 1 is the rightmost one, next to the hub; the following ones go left.
 * Centres come from the ReefSense cable ends of the link pictures.
 */
const SLOT_LEFTS = [
  "70.9%",
  "59.1%",
  "48.1%",
  "37.1%",
  "25.1%",
  "14.3%",
  "2.2%",
];

const slots: Record<string, any> = {};
SLOT_LEFTS.forEach((left, idx) => {
  slots["probe_" + (idx + 1)] = { id: idx + 1, css: { left: left } };
});

export const probes = {
  // A 7th probe is the most the two extension boxes can take.
  max: SLOT_LEFTS.length,
  common: {
    css: {
      position: "absolute",
      // Cable ends of the link pictures, in % of the hub picture
      top: "47.6%",
      width: "8%",
    },
    elements: {
      primary_value: {
        name: "probe_primary",
        type: "common-sensor",
        // Also forces a re-render on every update, which keeps the colour
        // in step with the level entity.
        disabled_if: "!device.show_primary()",
        no_br_if_disabled: true,
        text_color: "${device.primary_color()}",
        tap_action: {
          domain: "redsea_ui",
          action: "more-info",
          data: "probe_primary",
        },
        css: { ...VALUE_CSS, top: "17%" },
      },
      secondary_value: {
        name: "probe_secondary",
        type: "common-sensor",
        disabled_if: "!device.has_secondary()",
        no_br_if_disabled: true,
        round: 1,
        text_color: "${device.secondary_color()}",
        tap_action: {
          domain: "redsea_ui",
          action: "more-info",
          data: "probe_secondary",
        },
        // Right under the main reading
        css: { ...VALUE_CSS, top: "22.5%" },
      },
      probe_conf: {
        // Bound to the status so the element exists for every probe type
        name: "probe_status",
        type: "click-image",
        icon: "mdi:cog",
        icon_color: COLOR_RS_RGBSTR,
        tap_action: {
          domain: "redsea_ui",
          action: "dialog",
          data: { type: "probe_conf" },
        },
        css: { ...COG_CSS, top: "47%", left: "48%" },
      },
    },
    // Per probe type:
    //   img_css: picture placement in the slot (% of the slot width)
    //   aspect:  picture height / width, to keep the bar cursor square
    //   bar:     situation bars, in % of the picture: the main reading goes
    //            on the `left` bar, the temperature on the `right` one (a
    //            temperature probe only has a `right` bar, its main reading
    //            being a temperature); `left` is only drawn
    //            when the probe has two readings (main value on the left,
    //            temperature on the right), a single reading goes right
    //   dots:    compact mode, one dot per reading under the cog, main one
    //            first: centre of the first at `top`, the next `gap` lower,
    //            on `left` (default 50), all in % of the picture
    types: {
      ph: {
        image: new URL(
          "../../../img/redsea/RSSENSE/rssense-ph-temperature.png",
          import.meta.url,
        ),
        img_css: { width: "106.7%", left: "-3.3%" },
        aspect: 7.72,
        bar: { top: 50, bottom: 99, left: [9.4, 25], right: [79.7, 95.3] },
        dots: { top: 54, gap: 7 },
        // A pH probe without embedded temperature has a picture of its own
        no_temp: {
          image: new URL(
            "../../../img/redsea/RSSENSE/rssense-ph.png",
            import.meta.url,
          ),
          img_css: { width: "100%", left: "0%" },
          aspect: 8.27,
          bar: { top: 50, bottom: 99, left: [4, 20] },
          dots: { top: 54 },
        },
        elements: {
          primary_value: { round: 2, unit: "'pH'" },
          secondary_value: { css: { top: "20%" } },
          probe_conf: { css: { top: "42%", left: "20%" } },
        },
      },
      orp: {
        image: new URL(
          "../../../img/redsea/RSSENSE/rssense-orp.png",
          import.meta.url,
        ),
        img_css: { width: "100%", left: "0%" },
        aspect: 8.27,
        bar: { top: 50, bottom: 99, left: [5, 21] },
        dots: { top: 54 },
        elements: {
          primary_value: { round: 0 },
          probe_conf: { css: { top: "42%", left: "20%" } },
        },
      },
      ec: {
        image: new URL(
          "../../../img/redsea/RSSENSE/rssense-salinity-temperature.png",
          import.meta.url,
        ),
        img_css: { width: "100%", left: "0%" },
        aspect: 8.26,
        bar: { top: 50, bottom: 99, left: [-8, 7], right: [93, 108] },
        dots: { top: 54, gap: 7 },
        elements: {
          primary_value: { round: 1 },
          secondary_value: { css: { top: "20%" } },
          probe_conf: { css: { top: "42%", left: "20%" } },
        },
      },
      temperature: {
        image: new URL(
          "../../../img/redsea/RSSENSE/temperature.png",
          import.meta.url,
        ),
        img_css: { width: "110%", left: "0%" },
        aspect: 6.43,
        bar: { top: 61, bottom: 99, right: [80, 96] },
        dots: { top: 64.5 },
        elements: {
          primary_value: { round: 1, css: { top: "21%" } },
          probe_conf: { css: { top: "50%", left: "20%" } },
        },
      },
      ato: {
        image: new URL(
          "../../../img/redsea/RSSENSE/rssense-ato.png",
          import.meta.url,
        ),
        img_css: { width: "100%", left: "0%" },
        aspect: 8.27,
        // Temperature only: the water level will get a visual of its own
        bar: { top: 47, bottom: 99, right: [89, 104] },
        dots: { top: 73 },
        elements: {
          // On the black body, just under the connector
          secondary_value: { css: { top: "51%" } },
          probe_conf: { css: { top: "57.5%", left: "20%" } },
          // The sump water around the probe, at the mark the probe reports,
          // as on the RSATO+. The box covers the red part of the probe
          // (70% to 100% of the picture); each level is the water line in %
          // of the box from its bottom, read off the holes of the picture.
          // "error" has no level: it renders the no-reading mark.
          water_level: {
            name: "probe_primary",
            type: "water-level",
            levels: {
              below: 13,
              desired_level_1: 33,
              desired_level_2: 47,
              above: 87,
            },
            min_percent: 0,
            max_percent: 100,
            warn_states: ["below", "above"],
            show_value: false,
            wave: true,
            css: {
              position: "absolute",
              top: "70%",
              left: "-20%",
              width: "140%",
              height: "30%",
              "pointer-events": "none",
            },
          },
        },
      },
      leak: {
        image: new URL(
          "../../../img/redsea/RSSENSE/rssense-leak.png",
          import.meta.url,
        ),
        img_css: { width: "123.3%", left: "-11.7%" },
        aspect: 6.7,
        elements: {
          probe_conf: { css: { top: "75%", left: "20%" } },
          // Puddle under the probe when it is wet, as on the RSATO+
          leak_puddle: {
            name: "probe_primary",
            type: "water-level",
            disabled_if: "!device.leak_detected()",
            no_br_if_disabled: true,
            level: 100,
            show_value: false,
            wave: true,
            css: {
              position: "absolute",
              top: "97%",
              left: "-20%",
              width: "140%",
              height: "3%",
              "pointer-events": "none",
            },
          },
          // Where the water comes from, blinking red: a fish for the tank,
          // a cup of water for the ATO reservoir
          leak_source: {
            name: "probe_primary",
            type: "click-image",
            icon: "${device.leak_icon()}",
            icon_color: COLOR_LEVEL_DANGER_HEX,
            class: "blink-alert",
            disabled_if: "!device.leak_icon()",
            no_br_if_disabled: true,
            css: {
              ...COG_CSS,
              top: "86%",
              left: "20%",
              cursor: "default",
            },
          },
        },
      },
    },
  },
  ...slots,
};

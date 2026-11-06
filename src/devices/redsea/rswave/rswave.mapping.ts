/**
 * ReefWave view.
 *
 * Positions are percentages of the background picture (688×800): the pump
 * fills the upper half, the day program the lower one.
 *
 *   ┌──────────────────────────────┐
 *   │  messages                    │  last_message / last_alert_message
 *   │   ● ◉ ●         ● ● ●        │  state, preview, maintenance | settings, tasks, wifi
 *   │  ══[ mode ]══════════════(%) │  LED strip: mode + name, end cap: speed
 *   │  ◣ flow                      │  animated at the pump speed
 *   │  ┌────────────────────────┐  │
 *   │  │ day program            │  │  click: program view
 *   │  └────────────────────────┘  │
 *   └──────────────────────────────┘
 */
import { COLOR_ERROR_HEX, COLOR_RS_RGB } from "../../../utils/colors";
import { maintenance_shortcut } from "../maintenance/maintenance.shortcut";
import { poseidon_shortcut } from "../poseidon/poseidon.shortcut";

/** CSS of an overlay covering the whole picture. */
export const FULL_CANVAS = {
  position: "absolute",
  top: "0%",
  left: "0%",
  width: "100%",
  height: "100%",
  "pointer-events": "none",
};

/** Colour of a state icon that is off: light enough for the dark clips. */
const OFF_ON_PUMP = "rgba(255,255,255,0.55)";

/**
 * CSS of an icon centred on a point of the picture.
 * @param left: x of its centre, in %
 * @param top: y of its centre, in %
 */
export function icon_at(left: string, top: string) {
  return {
    flex: "0 0 auto",
    position: "absolute",
    left,
    top,
    transform: "translate(-50%,-50%)",
  };
}

/** Where the icons sit on the mounting clips, as [left, top] of their centre. */
export const CLIPS = {
  device_state: ["31.7%", "14%"],
  // Over the green LED of the picture, between on/off and maintenance
  preview: ["36%", "14%"],
  maintenance: ["40%", "15.7%"],
  configuration: ["73.3%", "25%"],
  // On the right clip, halfway between the settings cog and the wifi
  maintenance_tasks: ["78.7%", "25.9%"],
  wifi_quality: ["84%", "28.5%"],
  // On the right clip, before the settings cog
  poseidon: ["67.9%", "24.1%"],
} as const;

export const config = {
  name: null,
  model: "RSWAVE",
  background_img: new URL(
    "../../../img/redsea/RSWAVE/RSWAVE.png",
    import.meta.url,
  ),
  css: {
    width: "100%",
  },
  color: COLOR_RS_RGB,
  alpha: 0.7,
  elements: {
    // ── Messages (top band) ──────────────────────────────────────────
    last_message: {
      name: "last_message",
      type: "redsea-messages",
      // Absolutely positioned: never emit a <br> that shifts the flow
      no_br_if_disabled: true,
      css: {
        flex: "0 0 auto",
        position: "absolute",
        width: "97.5%",
        height: "15px",
        top: "1%",
        left: "1.25%",
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
        width: "97.5%",
        height: "20px",
        top: "5%",
        left: "1.25%",
      },
      "elt.css": {
        "background-color": "rgba(240,200,200,0.7)",
      },
    },

    // ── Mounting clips: common buttons ───────────────────────────────
    device_state: {
      name: "device_state",
      type: "click-image",
      icon: "state",
      icon_color: "red",
      off_color: OFF_ON_PUMP,
      master: true,
      tap_action: { domain: "switch", action: "toggle", data: "default" },
      css: icon_at(...CLIPS.device_state),
    },
    maintenance: {
      name: "maintenance",
      type: "click-image",
      icon: "state",
      icon_color: "red",
      off_color: OFF_ON_PUMP,
      master: true,
      tap_action: { domain: "switch", action: "toggle", data: "default" },
      css: icon_at(...CLIPS.maintenance),
    },
    // Preview of a wave and maintenance switch, in their own dialog
    preview: {
      name: "preview",
      type: "click-image",
      // No entity behind it: the dialog holds the preview entities
      stateObj: null,
      icon: "mdi:eye",
      icon_color: COLOR_ERROR_HEX,
      // The maintenance switch of the dialog is wanted on a stopped pump too
      off_clickable: true,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: { type: "preview" },
      },
      // Slightly smaller than its neighbours: the LED leaves little room
      css: icon_at(...CLIPS.preview),
      elt_css: { "--mdc-icon-size": "20px" },
    },
    configuration: {
      name: "configuration",
      type: "click-image",
      icon: "mdi:cog",
      icon_color: COLOR_ERROR_HEX,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: { type: "config" },
      },
      css: icon_at(...CLIPS.configuration),
    },
    // Maintenance tasks of the pump
    maintenance_tasks: maintenance_shortcut(
      icon_at(...CLIPS.maintenance_tasks),
    ),
    // Poseidon mode: hold to switch it, tap for its settings
    poseidon: poseidon_shortcut(icon_at(...CLIPS.poseidon), OFF_ON_PUMP),
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
      css: icon_at(...CLIPS.wifi_quality),
    },

    // ── Flow under the pump, animated at its speed ───────────────────
    flow: {
      name: "flow",
      type: "rswave-flow",
      stateObj: null,
      css: FULL_CANVAS,
    },

    // ── LED strip: mode, and the name of the pump under it ───────────
    mode_name: {
      name: "mode_name",
      type: "rswave-label",
      stateObj: null,
      css: FULL_CANVAS,
    },

    // ── End cap: speed ───────────────────────────────────────────────
    speed: {
      name: "sensor.wave_forward_intensity",
      type: "rswave-speed",
      target: 100,
      force_integer: true,
      // Ring fitted on the end cap, drawn over the whole picture
      css: FULL_CANVAS,
    },

    // ── Pumps of the group, under the flow: tap to show their card ───
    linked: {
      name: "linked_waves",
      type: "rswave-linked",
      stateObj: null,
      // A full-width row between the flow and the program
      css: {
        position: "absolute",
        left: "2%",
        top: "49%",
        width: "96%",
        height: "11%",
      },
    },

    // ── Wave library: its editor, from an icon over the program ──────
    library: {
      name: "library",
      type: "rswave-library",
      stateObj: null,
      // No transform here: it would trap the editor's fixed overlay inside
      // the icon instead of covering the screen
      css: {
        position: "absolute",
        right: "7.9%",
        top: "calc(61.9% - 12px)",
      },
    },

    // ── Day program, click opens the program editor ──────────────────
    schedule: {
      name: "schedule",
      type: "rswave-schedule",
      stateObj: null,
      css: {
        flex: "0 0 auto",
        position: "absolute",
        left: "10.5%",
        top: "60.2%",
        width: "81.8%",
        height: "37.6%",
      },
    },
  },
};

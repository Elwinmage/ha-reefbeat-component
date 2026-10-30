/**
 * Mapping parts shared by the RSPower 6 and 8.
 *
 * Both models draw the same device-level widgets at the same places (the
 * pictures share their layout) and the same socket; they differ only by
 * the number of sockets, their spacing and the shape of the socket button.
 */

import {
  COLOR_ERROR_HEX,
  COLOR_RS_RGBSTR,
  COLOR_WHITE_60,
} from "../../../utils/colors";
import { maintenance_shortcut } from "../maintenance/maintenance.shortcut";
import { poseidon_shortcut } from "../poseidon/poseidon.shortcut";

/** Device-level widgets, identical on both models. */
export const elements = {
  rssense_temperature: {
    name: "rssense_temperature",
    type: "click-image",
    // A paired hub takes the probe's slot: the two pictures occupy the
    // same corner, so the probe steps aside rather than overlapping.
    disabled_if: "!device.has_temperature_link()",
    no_br_if_disabled: true,
    class:
      "${device.is_on() && device.temperature_link_alert() ? 'blink-alert' : ''}",
    image: new URL(
      "../../../img/redsea/RSPOWER/rssense-temperature-power.png",
      import.meta.url,
    ),
    css: {
      flex: "0 0 auto",
      position: "absolute",
      width: "100%",
      top: "0%",
      left: "0%",
    },
  },
  rscontrol_link: {
    // Bound to the pairing flag so the element re-renders when a hub is
    // paired or dropped; `disabled_if` forces a refresh on every update,
    // which also catches the link going up and down underneath.
    name: "control_paired",
    type: "click-image",
    disabled_if: "!device.has_control_link()",
    no_br_if_disabled: true,
    // Paired but unreachable: blink under a light red tint (not while the
    // strip is off: it reads nothing from the hub then)
    class:
      "${device.is_on() && device.control_link_alert() ? 'blink-alert' : ''}",
    image: new URL(
      "../../../img/redsea/RSPOWER/rscontrol_rspower_link.png",
      import.meta.url,
    ),
    css: {
      flex: "0 0 auto",
      position: "absolute",
      width: "100%",
      top: "0%",
      left: "0%",
      // A full-canvas image would otherwise swallow clicks aimed at the
      // controls underneath, including over its transparent areas — the
      // hub name sits inside this picture's box.
      "pointer-events": "none",
    },
  },
  rscontrol_name: {
    // Bound to the pairing flag like the picture above: its `disabled_if`
    // forces a re-render on every update, which is what keeps the `value`
    // expression fresh when the hub is renamed or swapped.
    name: "control_paired",
    type: "common-sensor",
    value: "${device.linked_control_name()}",
    // Hidden unless the hub resolves to a device Home Assistant knows:
    // a name that cannot be resolved has nothing to navigate to, and a
    // clickable label leading nowhere is worse than no label.
    disabled_if: "!device.linked_control_name()",
    no_br_if_disabled: true,
    // A link to another device: still followed while the strip is off
    off_clickable: true,
    tap_action: {
      domain: "redsea_ui",
      action: "show_device",
      data: { hwid: "${device.linked_control_hwid()}" },
    },
    css: {
      position: "absolute",
      top: "31.5%",
      left: "2.5%",
      cursor: "pointer",
      "writing-mode": "vertical-rl",
      "text-orientation": "mixed",
      transform: "rotate(180deg)",
      color: COLOR_WHITE_60,
      // Scales with the card width — a fixed rem overflows on mobile and
      // reads too small in a browser.
      "font-size": "var(--rs-label-font)",
      "white-space": "nowrap",
      overflow: "hidden",
      "max-height": "26%",
    },
  },
  power_temperature: {
    name: "power_temperature",
    type: "common-sensor",
    round: 1,
    disabled_if: "device.has_control_link() || ${state} === 'unknown'",
    // Coloured by its level, as the ReefControl probes are
    text_color: "${device.temperature_color()}",
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "33%",
      color: COLOR_WHITE_60,
      left: "0.5%",
      "font-size": "0.65rem",
    },
    tap_action: {
      domain: "redsea_ui",
      action: "more-info",
      data: "power_temperature",
    },
  },
  // Where the local temperature stands against its bounds: a situation
  // bar, or a dot in the compact mode of the card editor. Opens its last
  // 24 hours.
  power_temperature_level: {
    name: "power_temperature",
    type: "level-indicator",
    compact: "${device.config.compact_probes === true}",
    disabled_if: "device.has_control_link() || !device.has_temperature_link()",
    no_br_if_disabled: true,
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "power_temperature_history" },
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      // Under the cog, along the probe
      top: "51%",
      left: "0.4%",
      width: "1.2%",
      height: "14%",
    },
    // The dot goes on the tube, under the cog, and low enough for a "+"
    // above it to clear the cog: margins in % of the bar's width
    dot_css: { "margin-left": "180%", "margin-top": "150%" },
  },
  power_temperature_conf: {
    name: "power_temperature_conf",
    type: "click-image",
    icon: "mdi:cog",
    icon_color: COLOR_RS_RGBSTR,
    disabled_if: "device.has_control_link() || device.temperature_link_alert()",
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "46.5%",
      left: "1%",
      "font-size": "0.65rem",
    },
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "power_temperature_conf" },
    },
  },
  last_message: {
    name: "last_message",
    type: "redsea-messages",
    no_br_if_disabled: true,
    css: {
      flex: "0 0 auto",
      position: "absolute",
      width: "100%",
      height: "15px",
      top: "70%",
      left: "0px",
    },
    "elt.css": {
      "background-color": "rgba(220,220,220,0.7)",
    },
  },
  last_alert_message: {
    name: "last_alert_message",
    type: "redsea-messages",
    no_br_if_disabled: true,
    label: "'⚠'",
    css: {
      color: "red",
      flex: "0 0 auto",
      position: "absolute",
      width: "100%",
      height: "20px",
      top: "74%",
      left: "0px",
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
      left: "10%",
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
      left: "16%",
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
      right: "22%",
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
      top: "2%",
      right: "16%",
    },
  },
  // Maintenance tasks of the strip: left of the settings cog
  maintenance_tasks: maintenance_shortcut({
    flex: "0 0 auto",
    position: "absolute",
    top: "2%",
    right: "28%",
  }),
  // Poseidon mode: hold to switch it, tap for its settings
  poseidon: poseidon_shortcut(
    {
      flex: "0 0 auto",
      position: "absolute",
      top: "2%",
      right: "34%",
    },
    "rgba(255,255,255,0.55)",
  ),
  battery_level: {
    name: "battery_level",
    type: "common-sensor",
    master: true,
    label: false,
    icon: true,
    icon_color: "red",
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "2%",
      right: "10%",
    },
  },
  mode: {
    name: "mode",
    type: "common-sensor",
    translate_values: true,
    css: {
      flex: "0 0 auto",
      position: "absolute",
      color: COLOR_WHITE_60,
      width: "5.3%",
      top: "6.5%",
      left: "45%",
      "font-size": "0.9rem",
    },
  },
  total_consumption: {
    name: "total_consumption",
    type: "common-sensor",
    round: 1,
    unit: "'W'",
    tap_action: {
      domain: "redsea_ui",
      action: "more-info",
      data: "total_consumption",
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      color: COLOR_WHITE_60,
      top: "6.5%",
      left: "64%",
      "font-size": "0.9rem",
      cursor: "pointer",
    },
  },
  rscontrol_connectivity: {
    name: "connected_control",
    type: "click-image",
    icon: "mdi:web",
    icon_color: COLOR_RS_RGBSTR,
    disabled_if: "!device.has_control_link()",
    no_br_if_disabled: true,
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "rscontrol_connectivity" },
    },
    css: {
      flex: "0 0 auto",
      position: "absolute",
      top: "10%",
      left: "3.5%",
    },
  },
};

/**
 * What stays on the card while the strip is switched off: its on/off switch,
 * the picture of its local probe or of the paired hub, and the link to that
 * hub. Readings, settings and the sockets' controls go.
 */
export const off_keep: string[] = [
  "device_state",
  "rssense_temperature",
  "rscontrol_link",
  "rscontrol_name",
];

/** What sets the sockets of a model apart. */
export interface SocketGeometry {
  /** Width of a socket, in % of the picture */
  width: string;
  /** Top of the socket name, in % of the socket */
  name_top: string;
  /** Top of the on/off button, in % of the socket */
  button_top: string;
  /** Border radius of the on/off button: round or square outlet */
  button_radius: string;
}

/**
 * Settings shared by every socket of a model.
 * @param geometry: what sets the model's sockets apart
 * @return the `sockets.common` configuration
 */
export function socket_common(geometry: SocketGeometry): Record<string, any> {
  return {
    alpha: "0.2",
    // Strip switched off: a socket only keeps the device plugged into it
    off_keep: ["linked_thumbnail"],
    css: {
      top: "9.5%",
      position: "absolute",
      flex: "0 0 auto",
      width: geometry.width,
      height: "13.5%",
    },
    elements: {
      socket_name_label: {
        name: "socket_name",
        type: "common-sensor",
        disabled_if: "entity.socket_mode?.state === 'setup'",
        no_br_if_disabled: true,
        css: {
          position: "absolute",
          top: geometry.name_top,
          left: "0%",
          width: "100%",
          "text-align": "center",
          "font-size": "0.7em",
          "font-weight": "bold",
          color: "white",
          "text-shadow": "0 0 3px rgba(0,0,0,0.7)",
          overflow: "hidden",
          "text-overflow": "ellipsis",
          "white-space": "nowrap",
        },
      },
      socket_consumption_label: {
        name: "socket_consumption",
        type: "common-sensor",
        round: 1,
        unit: "'W'",
        disabled_if: "entity.socket_mode?.state === 'setup'",
        no_br_if_disabled: true,
        tap_action: {
          domain: "redsea_ui",
          action: "more-info",
          data: "socket_consumption",
        },
        css: {
          position: "absolute",
          bottom: "0.1%",
          left: "0%",
          "text-align": "center",
          "font-size": "0.55em",
          color: "rgba(255,255,255,0.8)",
        },
      },
      socket_on_off: {
        name: "socket_on_off",
        type: "click-image",
        // The linked appliance's own icon (redsea:pump-on/off...) when it has
        // one, the switch state icon otherwise
        icon: "${device.socket_icon()}",
        icon_color:
          "${entity.socket_on_off?.state === 'off' ? '#666666' : '" +
          COLOR_RS_RGBSTR +
          "'}",
        class: "on_off",
        style: "button",
        disabled_if: "entity.socket_mode?.state === 'setup'",
        no_br_if_disabled: true,
        tap_action: {
          domain: "redsea_ui",
          action: "dialog",
          data: { type: "socket_config" },
        },
        hold_action: {
          domain: "switch",
          action: "toggle",
          data: "default",
        },
        css: {
          position: "absolute",
          width: "70%",
          "aspect-ratio": "1/1",
          top: geometry.button_top,
          left: "15%",
          "border-radius": geometry.button_radius,
          "--mdc-icon-size": "100%",
          "border-width": "2px",
          "border-style": "solid",
          "border-color": "$DEVICE-COLOR-ALPHA$",
          "background-color": "$DEVICE-COLOR-ALPHA$",
        },
      },
      linked_thumbnail: {
        // The strip holds the link, the socket only draws it. Bound to the
        // socket mode so it refreshes with the rest, and disabled when no
        // appliance is linked or its model has no picture to borrow.
        name: "socket_mode",
        type: "click-image",
        image: "${device.linked_image()}",
        disabled_if: "!device.linked_image()",
        no_br_if_disabled: true,
        class: "${device.linked_class()}",
        // A link to another device: still followed while the strip is off
        off_clickable: true,
        tap_action: {
          domain: "redsea_ui",
          action: "show_device",
          data: { hwid: "${device.linked_hwid()}" },
        },
        css: {
          position: "absolute",
          width: "90%",
          left: "5%",
          cursor: "pointer",
          // Thumbnails hang below the strip in two staggered rows so
          // neighbours do not overlap. Odd sockets take the near row; the
          // even ones override this to the far row.
          top: "110%",
          "border-style": "solid",
          "border-radius": "30%",
          "border-color": "$DEVICE-COLOR-ALPHA$",
          "background-color": "$DEVICE-COLOR-ALPHA$",
        },
      },
      socket_mode_icon: {
        name: "socket_mode",
        type: "common-sensor",
        icon: "'mdi:clock-time-nine-outline'",
        icon_color: "rgba(255,255,255,0.5)",
        disabled_if: "device.auto_mode() !== 'schedule'",
        no_br_if_disabled: true,
        // The schedule is edited in the socket's unified mode editor
        tap_action: {
          domain: "redsea_ui",
          action: "dialog",
          data: { type: "socket_config" },
        },
        // The box is the icon itself (40% of the former 70% box, same
        // top-left corner): a larger box covered the bottom of the on/off
        // button and the consumption label, and stole their clicks.
        css: {
          position: "absolute",
          width: "28%",
          "aspect-ratio": "1/1",
          top: "60%",
          left: "15%",
          "--mdc-icon-size": "100%",
          cursor: "pointer",
        },
      },
      socket_mode_icon_static: {
        name: "socket_mode",
        type: "common-sensor",
        icon: "device.auto_mode() === 'sensor' ? ({'temperature': 'mdi:thermometer','ph': 'mdi:ph','ec': 'mdi:water-percent','orp': 'mdi:flash-triangle','leak': 'mdi:water-alert','ato': 'mdi:cup-water'}[device.sensor_reading()] || 'mdi:power'): 'mdi:power'",
        icon_color: "rgba(255,255,255,0.5)",
        disabled_if:
          "entity.socket_mode?.state === 'setup' || device.auto_mode() === 'schedule'",
        no_br_if_disabled: true,
        css: {
          position: "absolute",
          width: "70%",
          "aspect-ratio": "1/1",
          top: "60%",
          left: "15%",
          "--mdc-icon-size": "40%",
          "pointer-events": "none",
        },
      },
      // A socket is only ever suspended by being switched off by hand: a
      // manual "on" out of an automatic mode is a mode change, not a pause.
      socket_manual_override: {
        name: "socket_prev_mode",
        type: "common-sensor",
        icon: "'mdi:hand-back-left-outline'",
        icon_color: "rgba(255,255,255,0.5)",
        disabled_if:
          "entity.socket_mode?.state !== 'off' || (entity.socket_prev_mode?.state !== 'schedule' && entity.socket_prev_mode?.state !== 'sensor')",
        no_br_if_disabled: true,
        css: {
          position: "absolute",
          top: "60%",
          left: "70%",
          "--mdc-icon-size": "75%",
          "pointer-events": "none",
        },
      },
      socket_setup: {
        name: "socket_mode",
        type: "click-image",
        icon: "mdi:plus",
        icon_color: "rgba(255,255,255,0.35)",
        disabled_if: "entity.socket_mode?.state !== 'setup'",
        no_br_if_disabled: true,
        tap_action: {
          domain: "redsea_ui",
          action: "dialog",
          data: { type: "socket_config" },
        },
        css: {
          position: "absolute",
          width: "70%",
          "aspect-ratio": "1/1",
          top: geometry.button_top,
          left: "15%",
          "--mdc-icon-size": "100%",
          cursor: "pointer",
        },
      },
    },
  };
}

/** Colour of each socket, in socket order. */
export const SOCKET_COLORS: readonly string[] = [
  "255,0,0",
  "0,255,0",
  "0,0,255",
  "255,255,0",
  "255,0,255",
  "0,255,255",
  "125,125,255",
  "255,100,20",
];

/**
 * One entry per socket, placed from the left.
 *
 * Linked thumbnails hang below the strip in two staggered rows so that
 * neighbours do not overlap: odd sockets take the near row, even ones the
 * far row.
 * @param lefts: left edge of each socket, in % of the picture
 * @return the `socket_N` configurations
 */
export function socket_slots(lefts: string[]): Record<string, any> {
  const slots: Record<string, any> = {};
  lefts.forEach((left, idx) => {
    const id = idx + 1;
    const slot: Record<string, any> = {
      id: id,
      color: SOCKET_COLORS[idx],
      css: { left: left },
    };
    if (id % 2 === 0) {
      slot.elements = { linked_thumbnail: { css: { top: "225%" } } };
    }
    slots["socket_" + id] = slot;
  });
  return slots;
}

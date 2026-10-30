import { COLOR_WHITE_60 } from "../../../utils/colors";
import { maintenance_shortcut } from "../maintenance/maintenance.shortcut";
import { poseidon_shortcut } from "../poseidon/poseidon.shortcut";

export const config = {
  name: null,
  model: "RSRUN",
  background_img: new URL(
    "../../../img/redsea/RSRUN/reefrun.png",
    import.meta.url,
  ),
  css: {
    width: "100%",
  },
  elements: {
    last_message: {
      name: "last_message",
      type: "redsea-messages",
      // Absolutely positioned: never emit a <br> that shifts the flow
      no_br_if_disabled: true,
      css: {
        flex: "0 0 auto",
        position: "absolute",
        width: "100%",
        height: "15px",
        top: "88%",
        left: "0px",
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
        width: "100%",
        height: "20px",
        top: "93%",
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
        top: "0%",
        left: "0%",
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
        top: "0%",
        left: "6%",
      },
    },
    // Maintenance tasks of the controller and its pumps: third icon of the
    // top left row, after the maintenance mode switch
    maintenance_tasks: maintenance_shortcut({
      flex: "0 0 auto",
      position: "absolute",
      top: "0%",
      left: "12%",
    }),
    // Poseidon mode: hold to switch it, tap for its settings
    poseidon: poseidon_shortcut({
      flex: "0 0 auto",
      position: "absolute",
      top: "0%",
      right: "12%",
    }),
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
        top: "0%",
        right: "6%",
      },
    },
    wifi_quality: {
      name: "wifi_quality",
      type: "common-sensor",
      master: true,
      label: false,
      icon: true,
      icon_color: "red",
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
        top: "0%",
        right: "0%",
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
        top: "1%",
        left: "45%",
      },
    },
  },
};

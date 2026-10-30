import {
  COLOR_WHITE_60,
  COLOR_RS_HEX,
  COLOR_ORANGE_HEX,
  COLOR_ERROR_HEX,
} from "../../../utils/colors";
import { maintenance_shortcut } from "../maintenance/maintenance.shortcut";
import { poseidon_shortcut } from "../poseidon/poseidon.shortcut";

export const config = {
  name: null,
  model: "RSATO",
  background_img: new URL(
    "../../../img/redsea/RSATO/RSATO+.png",
    import.meta.url,
  ),
  css: {
    width: "100%",
  },

  elements: {
    // --- Optional accessories --------------------------------------------
    // Both overlays are full-canvas PNGs with a transparent background, so
    // they need no positioning: they are simply stacked over background_img.
    //
    // They are declared FIRST on purpose. Elements paint in declaration
    // order, so anything below stays visually and functionally on top of
    // them. pointer-events is disabled as well: a full-canvas image would
    // otherwise swallow every click aimed at the controls underneath,
    // including over its transparent areas.
    pump: {
      // Bound to `mode`: that is the entity carrying both presence and fault
      // for the pump, and a class holding a "${...}" expression is only
      // re-evaluated when the element's own stateObj changes.
      name: "mode",
      type: "click-image",
      image: new URL(
        "../../../img/redsea/RSATO/rsato_pump.png",
        import.meta.url,
      ),
      // No pump paired: draw nothing at all.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      // Paired but faulty: blink under a light red tint.
      class: "${device.pump_alert() ? 'blink-alert' : ''}",
      css: {
        position: "absolute",
        top: "0",
        left: "0",
        width: "100%",
        "pointer-events": "none",
      },
      elt_css: {
        display: "block",
        width: "100%",
      },
    },
    leak: {
      // Bound to the PROBLEM sensor so a leak re-renders the element on its
      // own. Presence is read from the probe's separate `connected` flag
      // inside has_leak_sensor(), and the disabled_if below already forces a
      // re-render on every update, so both transitions are covered.
      name: "status",
      type: "click-image",
      image: new URL("../../../img/redsea/RSATO/leak.png", import.meta.url),
      disabled_if: "!device.has_leak_sensor()",
      no_br_if_disabled: true,
      // Three states: leaking, plugged in but disarmed, normal.
      class:
        "${device.leak_alert() ? 'blink-alert' : " +
        "(device.leak_sensor_armed() ? '' : 'muted')}",
      css: {
        position: "absolute",
        top: "0",
        left: "0",
        width: "100%",
        "pointer-events": "none",
      },
      elt_css: {
        display: "block",
        width: "100%",
      },
    },
    // Water leaving the outlet during a fill.
    //
    // Declared right after the two full-canvas overlays: it must paint over
    // them, and under the controls that follow.
    //
    // Position: the nozzle clipped to the tank rim, down to the sump surface.
    // Measured off the background picture; nudge the four values if the
    // stream misses the outlet.
    pump_flow: {
      // The speed drives the animation rate. On the RSATO it is a setting,
      // not a measurement -- it never falls to zero -- so `running_if` adds
      // the flag that says water is actually moving.
      name: "pump_speed",
      running_if: "is_pump_on",
      // No fill in progress means no water at the outlet, not water standing
      // still: without this the stream would sit there frozen between fills.
      hide_when_stopped: true,
      type: "flow-image",
      image: new URL(
        "../../../img/redsea/RSRUN/water_seamless.png",
        import.meta.url,
      ),
      // Nothing to pour without a pump.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      // Slower than the defaults, which are tuned for a return pump pushing
      // hard through a tube. This is a trickle into a sump.
      min_duration: 2,
      max_duration: 6,
      elt_css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "41%",
        left: "52.5%",
        width: "4%",
        height: "32%",
        // The shared texture is nearly grey, which reads as a shadow rather
        // than as water. `saturate` alone cannot colour it -- it multiplies a
        // saturation that is close to zero -- so `sepia` puts a hue on it
        // first, then `hue-rotate` swings that hue round to blue.
        //
        // To tune: hue-rotate picks the shade, saturate its intensity.
        filter: "sepia(1) saturate(4) hue-rotate(175deg) brightness(1.05)",
        // The shared keyframe scrolls the texture upward, for a return pump
        // pushing water up a tube. Here the water falls out of an outlet, so
        // the same keyframe is played backwards rather than duplicated.
        "animation-direction": "reverse",
        "pointer-events": "none",
      },
    },

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
        top: "33%",
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
        top: "37%",
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
        top: "5.5%",
        left: "75%",
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
        top: "5.5%",
        left: "81%",
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
        top: "5.5%",
        left: "87%",
      },
    },
    wifi_quality: {
      name: "wifi_quality",
      type: "common-sensor",
      master: true,
      label: false,
      icon: true,
      icon_color: "#ec2330",
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
        top: "5.5%",
        left: "93%",
      },
    },
    // Maintenance tasks of the ATO: under the wifi, on the second row of the
    // icon block
    maintenance_tasks: maintenance_shortcut({
      flex: "0 0 auto",
      position: "absolute",
      top: "10%",
      left: "93%",
    }),
    // Poseidon mode: hold to switch it, tap for its settings
    poseidon: poseidon_shortcut(
      {
        flex: "0 0 auto",
        position: "absolute",
        top: "10%",
        left: "87%",
      },
      "rgba(255,255,255,0.55)",
    ),
    auto_fill: {
      name: "auto_fill",
      type: "click-image",
      // Meaningless without a pump: no_br_if_disabled is required because the
      // element is absolutely positioned — a bare <br> would fall back into
      // the normal flow and shift the rest of the card.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
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
        top: "10%",
        left: "81%",
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
        width: "27.3%",
        top: "1.5%",
        left: "74%",
      },
    },
    fill: {
      name: "fill",
      type: "click-image",
      // Meaningless without a pump: no_br_if_disabled is required because the
      // element is absolutely positioned — a bare <br> would fall back into
      // the normal flow and shift the rest of the card.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      icon: "state",
      icon_color: "red",
      master: true,
      tap_action: {
        domain: "button",
        action: "press",
        data: "default",
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "43%",
        left: "12%",
      },
    },
    stop_fill: {
      name: "stop_fill",
      type: "click-image",
      // Meaningless without a pump: no_br_if_disabled is required because the
      // element is absolutely positioned — a bare <br> would fall back into
      // the normal flow and shift the rest of the card.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      icon: "state",
      icon_color: "red",
      master: true,
      tap_action: {
        domain: "button",
        action: "press",
        data: "default",
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "43%",
        left: "20%",
      },
    },
    resume: {
      name: "resume",
      type: "click-image",
      // Meaningless without a pump: no_br_if_disabled is required because the
      // element is absolutely positioned — a bare <br> would fall back into
      // the normal flow and shift the rest of the card.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      icon: "state",
      icon_color: "red",
      master: true,
      tap_action: {
        domain: "button",
        action: "press",
        data: "default",
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "54%",
        left: "17%",
      },
    },
    // RO reservoir: a genuine volume ratio. volume_left is in mL and
    // ato_tank_volume in L, hence target_factor. min_percent is the residue
    // the pump cannot siphon, so an "empty" tank still shows a water line;
    // max_percent is the container rim in the background picture.
    volume_left: {
      name: "volume_left",
      type: "water-level",
      // Meaningless without a pump: no_br_if_disabled is required because the
      // element is absolutely positioned — a bare <br> would fall back into
      // the normal flow and shift the rest of the card.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      target: "ato_tank_volume",
      target_factor: 1000,
      min_percent: 10,
      max_percent: 95,
      warn_below: 10,
      wave: true,
      css: {
        position: "absolute",
        top: "59.5%",
        left: "0%",
        width: "26%",
        height: "36%",
      },
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: {
          type: "ato_tank",
        },
      },
    },

    // Sump probe: the state names a hole on the probe bar, not a fraction of
    // a volume, so each value maps to a fixed height. min/max stay 0/100 so
    // the levels below are read directly as a percentage of the box, which
    // makes them measurable straight off the background picture.
    // "error" is deliberately absent: it renders the no-reading mark.
    water_level: {
      name: "sensor.water_level",
      type: "water-level",
      levels: {
        below: 50.3,
        desired_level_1: 58.3,
        desired_level_2: 64.7,
        above: 80,
      },
      min_percent: 0,
      max_percent: 100,
      // Both ends of the probe are abnormal: below means the ATO is not
      // keeping up, above means it overfilled. "error" never reaches here —
      // it has no level, so it renders the blinking no-reading mark.
      warn_states: ["below", "above"],
      wave: true,
      // The level comes from sensor.water_level; the overlay shows the
      // binary_sensor instead. Both register as "water_level", hence the
      // domain prefix.
      value_entity: "binary_sensor.water_level",
      css: {
        position: "absolute",
        top: "49.5%",
        left: "51.5%",
        width: "48.5%",
        height: "45%",
      },
    },
    // Daily ATO consumption against its running average, drawn on a canvas
    // rather than through a native statistics card: no card chrome, no header
    // and above all no minimum height, so the chart holds its proportions
    // whatever the card width. That last point is why the
    // hui-statistics-graph-card version was dropped — it refused to shrink
    // below a pixel floor and spilled over the picture on a narrow card.
    today_usage_sparkline: {
      name: "today_volume_usage",
      type: "history-chart",
      // Pinned to the calendar day: today_volume_usage resets at midnight, so
      // a rolling 24h window would straddle two days and show the reset as a
      // cliff in the middle of the chart.
      window: "today",
      // Set to true to print the resolved entity ids and the number of points
      // read into the browser console, when the chart stays empty.
      debug: false,
      // Demo aid, off in normal use. Set to 30 and run scripts/ato_timelapse
      // to watch a full day draw itself in 30 seconds: the recorder cannot be
      // back-dated, so the seconds actually written are stretched across the
      // whole axis instead.
      demo_seconds: 30,
      step: true,
      baseline: "zero",
      unit: "",
      // Light panel behind the chart, so the grid reads over the sump water.
      bg_color: "255,255,255,0.35",
      axis_color: "40,40,40",
      // Axis label size. A box under 160px wide drops two pixels off it on
      // its own, so this is the size on a wide card.
      font_size: 10,
      entities: [
        {
          entity: "today_volume_usage",
          color: COLOR_ORANGE_HEX,
          fill: true,
          fill_color: "rgba(255, 152, 0, 0.25)",
        },
        { entity: "daily_volume_average", color: COLOR_RS_HEX },
      ],
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      // The chart already shows two of the six consumption figures; tapping
      // it opens the other four rather than crowding the picture with them.
      //
      // pointer-events stays enabled here, unlike the overlays above: the
      // only element underneath is the sump water-level, which carries no
      // tap_action of its own, so nothing is swallowed.
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: {
          type: "usage",
        },
      },
      css: {
        position: "absolute",
        top: "61%",
        left: "61%",
        width: "39%",
        height: "30%",
      },
    },
    // Puddle on the floor when the leak probe is wet.
    //
    // The firmware says which side the water came from, and that is the half
    // of the information worth showing: salt water on the floor is not the
    // same problem as fresh water. Rather than writing it out — the strip is
    // three percent of the card high, no label fits — the puddle is drawn on
    // the matching side of the picture: on the left under the RO reservoir,
    // on the right under the sump. Position carries the meaning, which is
    // what a photo-realistic card is for.
    //
    // Rendered as a water-level rather than a flat rectangle so it gets the
    // same wave and the same tint as the water in the two tanks. `level` is a
    // constant: the probe is a threshold, not a gauge, so only the presence
    // carries information, and show_value is off because a percentage of a
    // puddle means nothing.
    leak_puddle_rodi: {
      name: "status",
      type: "water-level",
      disabled_if: "device.leak_source() !== 'rodi'",
      no_br_if_disabled: true,
      level: 100,
      show_value: false,
      wave: true,
      css: {
        position: "absolute",
        top: "93%",
        left: "26.5%",
        width: "11.5%",
        height: "3%",
        "pointer-events": "none",
      },
    },
    leak_puddle_aquarium: {
      name: "status",
      type: "water-level",
      disabled_if: "device.leak_source() !== 'aquarium'",
      no_br_if_disabled: true,
      level: 100,
      show_value: false,
      wave: true,
      css: {
        position: "absolute",
        top: "93%",
        left: "38%",
        width: "11.5%",
        height: "3%",
        "pointer-events": "none",
      },
    },
    // Water reported without a readable side: spread over the whole strip
    // rather than guessing one, so the picture never claims to know more than
    // the device said.
    leak_puddle_unknown: {
      name: "status",
      type: "water-level",
      disabled_if: "device.leak_source() !== 'unknown'",
      no_br_if_disabled: true,
      level: 100,
      show_value: false,
      wave: true,
      css: {
        position: "absolute",
        top: "93%",
        left: "26.5%",
        width: "23%",
        height: "3%",
        "pointer-events": "none",
      },
    },
    // One cog per accessory socket on the controller, in the same column
    // grid as the header icons above (75/81/87%). Each opens the sensors
    // attached to that accessory, which the picture can only hint at.
    //
    // Left to right: pump, leak probe, water-level probe — the order of the
    // three sockets on the front panel.
    //
    // Bound to a plain name rather than an entity: the icon is fixed, so no
    // stateObj is needed, exactly like the `configuration` cog above.
    pump_settings: {
      name: "pump_settings",
      type: "click-image",
      // Nothing to show about a pump that is not paired.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      icon: "mdi:pump",
      icon_color: COLOR_ERROR_HEX,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: {
          type: "pump",
        },
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "16%",
        left: "87%",
      },
    },
    leak_settings: {
      name: "leak_settings",
      type: "click-image",
      // The probe is optional: no socket used, no cog.
      disabled_if: "!device.has_leak_sensor()",
      no_br_if_disabled: true,
      icon: "mdi:pipe-leak",
      icon_color: COLOR_ERROR_HEX,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: {
          type: "leak",
        },
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "16%",
        left: "75%",
      },
    },
    ato_sensor_settings: {
      name: "ato_sensor_settings",
      type: "click-image",
      disabled_if: "!device.has_ato_sensor()",
      no_br_if_disabled: true,
      icon: "mdi:hydraulic-oil-level",
      icon_color: COLOR_ERROR_HEX,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: {
          type: "ato_sensor",
        },
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "16%",
        left: "81%",
      },
    },
    // Device buzzer, placed between the RO reservoir and the sump.
    //
    // Not the leak alarm alone: the setting lives at the top level of
    // /configuration, not under its `leak` object, so a probe-less device can
    // still sound it. The icon therefore follows the switch and nothing else.
    //
    // Tap opens the buzzer dialog, hold toggles it: the switch is a safety
    // setting, so turning it off is deliberately the gesture you cannot make
    // by mistake while reaching for the details.
    buzzer: {
      // Domain-prefixed on purpose: integration versions before the switch
      // exposed a read-only binary_sensor of the same name, and a bare key
      // resolves to whichever the registry walk stored last.
      name: "switch.buzzer_enabled",
      type: "click-image",
      // Hidden rather than broken on an integration that predates the switch.
      disabled_if: "!device.has_buzzer()",
      no_br_if_disabled: true,
      // `state` follows the entity icon, which the integration flips between
      // mdi:bell-ring and mdi:bell-off, and greys it out when off. There is
      // no off variant of mdi:alarm-bell, hence the bell-ring/bell-off pair.
      icon: "state",
      icon_color: COLOR_ERROR_HEX,
      master: true,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: {
          type: "buzzer",
        },
      },
      hold_action: {
        domain: "switch",
        action: "toggle",
        data: "default",
      },
      css: {
        flex: "0 0 auto",
        position: "absolute",
        top: "77%",
        left: "32%",
      },
    },
    current_read: {
      name: "current_read",
      type: "common-sensor",
      text_color: "rgb(240,240,240)",
      round: 1,
      css: {
        position: "absolute",
        top: "91%",
        left: "54%",
        width: "40%",
      },
    },
    days_till_empty: {
      name: "days_till_empty",
      type: "common-sensor",
      // Meaningless without a pump: no_br_if_disabled is required because the
      // element is absolutely positioned — a bare <br> would fall back into
      // the normal flow and shift the rest of the card.
      disabled_if: "!device.has_pump()",
      no_br_if_disabled: true,
      text_color: "rgb(240,240,240)",
      round: 0,
      unit: "${i18n._('days')}",
      css: {
        position: "absolute",
        top: "80%",
        left: "3%",
        // Kept narrow: the label sits over the RO reservoir and a wider box
        // spills past it. 15% is the ceiling that still fits the longest
        // translations of the "days" unit.
        width: "15%",
      },
      tap_action: {
        domain: "redsea_ui",
        action: "more-info",
        data: "days_till_empty",
      },
    },
  },
};

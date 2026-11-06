/**
 * Mapping parts shared by every ReefLED (G1, G2 and the ones to come).
 *
 * Positions are percentages of the ReefLED design space (591×860, see
 * RSLED_CANVAS). The background pictures are drawn on that whole space,
 * margins included: the sky above the lamp, the beam, the sliders and the
 * messages under it. The models share every element; only the icons on the
 * faces of the lamp, and the sky over its top, move with the shape of each
 * generation. rsled_config() builds a model's mapping from those.
 */
import { COLOR_ERROR_HEX } from "../../../utils/colors";
import { maintenance_shortcut } from "../maintenance/maintenance.shortcut";
import { poseidon_shortcut } from "../poseidon/poseidon.shortcut";

/** CSS of an overlay covering the whole design space. */
const FULL_CANVAS = {
  position: "absolute",
  top: "0%",
  left: "0%",
  width: "100%",
  height: "100%",
  "pointer-events": "none",
};

/** Colour of a state icon that is off: light enough for the dark lamp. */
const OFF_ON_LAMP = "rgba(255,255,255,0.45)";

/** Where the icons sit on the faces of a lamp, as [left, top] in %. */
export interface FaceLayout {
  device_state: [string, string];
  maintenance: [string, string];
  configuration: [string, string];
  battery_level: [string, string];
  wifi_quality: [string, string];
  /** Maintenance shortcut, last of the left face, after the wifi */
  maintenance_tasks: [string, string];
  /** Poseidon shortcut, first of the right face, before identify */
  poseidon: [string, string];
  identify: [string, string];
  moon_phase: [string, string];
  acclimation: [string, string];
  /** Top-left corner of the two acclimation lines */
  acclimation_text: [string, string];
  /** Slant of the right face, for the acclimation lines */
  right_skew: string;
  /** Centre of the manual mode countdown, under the right face icons */
  countdown: [string, string];
  /** Extra turn of the countdown, so it lines up with the face's edge */
  countdown_rotate: string;
}

/**
 * CSS of an icon centred on a point of the design space.
 * @param pos: [left, top] of its centre, in %
 */
function icon_at(pos: [string, string]) {
  return {
    flex: "0 0 auto",
    position: "absolute",
    left: pos[0],
    top: pos[1],
    transform: "translate(-50%,-50%)",
  };
}

/**
 * CSS of one line of text on the right face.
 * @param face: the face layout
 * @param line: 0 for the first line, 1 for the second
 */
function face_text(face: FaceLayout, line: number) {
  return {
    position: "absolute",
    left: face.acclimation_text[0],
    top: `calc(${face.acclimation_text[1]} + ${line * 2.2}%)`,
    color: "rgba(255,255,255,0.85)",
    "font-size": "var(--rs-label-font)",
    "white-space": "nowrap",
    transform: `skewY(${face.right_skew})`,
  };
}

/**
 * Icons on the front faces of a lamp.
 * @param face: where they sit on this model
 */
export function face_elements(face: FaceLayout) {
  return {
    // ── Left face: common switches and status ─────────────────────────
    device_state: {
      name: "device_state",
      type: "click-image",
      icon: "state",
      icon_color: "red",
      off_color: OFF_ON_LAMP,
      master: true,
      tap_action: { domain: "switch", action: "toggle", data: "default" },
      css: icon_at(face.device_state),
    },
    maintenance: {
      name: "maintenance",
      type: "click-image",
      icon: "state",
      icon_color: "red",
      off_color: OFF_ON_LAMP,
      master: true,
      tap_action: { domain: "switch", action: "toggle", data: "default" },
      css: icon_at(face.maintenance),
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
      css: icon_at(face.configuration),
    },
    battery_level: {
      name: "battery_level",
      type: "common-sensor",
      master: true,
      label: false,
      icon: true,
      icon_color: COLOR_ERROR_HEX,
      css: icon_at(face.battery_level),
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
      css: icon_at(face.wifi_quality),
    },
    // Maintenance tasks of the lamp
    maintenance_tasks: maintenance_shortcut(icon_at(face.maintenance_tasks)),
    // Poseidon mode: hold to switch it, tap for its settings
    poseidon: poseidon_shortcut(icon_at(face.poseidon), OFF_ON_LAMP),

    // ── Right face: ReefLED specific ──────────────────────────────────
    identify: {
      name: "led_identify",
      type: "click-image",
      icon: "mdi:lightbulb-question-outline",
      icon_color: "rgba(255,255,255,0.8)",
      // The lamp blinks, and so does its beam on the card
      tap_action: [
        { domain: "button", action: "press", data: "default" },
        {
          domain: "redsea_ui",
          action: "device_event",
          data: { event: "rsled_identify" },
        },
      ],
      css: icon_at(face.identify),
    },
    moon_phase: {
      name: "moon_phase",
      type: "click-image",
      icon: "state",
      icon_color: "rgb(170,120,255)",
      off_color: OFF_ON_LAMP,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: { type: "led_moon" },
      },
      css: icon_at(face.moon_phase),
    },
    acclimation: {
      name: "acclimation",
      type: "click-image",
      icon: "state",
      icon_color: "rgb(90,170,255)",
      off_color: OFF_ON_LAMP,
      tap_action: {
        domain: "redsea_ui",
        action: "dialog",
        data: { type: "led_acclimation" },
      },
      css: icon_at(face.acclimation),
    },
    // Time left of a manual mode run for a set time, under the icons
    manual_countdown: {
      name: "manual_countdown",
      type: "rsled-countdown",
      stateObj: null,
      // Nothing to show outside the manual mode: never a <br>
      no_br_if_disabled: true,
      css: {
        position: "absolute",
        left: face.countdown[0],
        top: face.countdown[1],
        // Sheared like the face and a little narrowed by its perspective,
        // so the text looks printed on it
        transform: `translate(-50%,-50%) rotate(${face.countdown_rotate}) skewY(${face.right_skew}) scaleX(0.9)`,
      },
    },
    // Acclimation progress, only while it runs
    acclimation_days: {
      name: "acclimation_remaining_days",
      type: "common-sensor",
      force_integer: true,
      unit: "${i18n._('days_short')}",
      disabled_if: "entity.acclimation?.state !== 'on'",
      no_br_if_disabled: true,
      css: face_text(face, 0),
    },
    acclimation_factor: {
      name: "acclimation_current_intensity_factor",
      type: "common-sensor",
      force_integer: true,
      disabled_if: "entity.acclimation?.state !== 'on'",
      no_br_if_disabled: true,
      css: face_text(face, 1),
    },
  };
}

/**
 * CSS of one of the three sliders grouped on the left.
 * @param column: 0, 1 or 2 from the left
 */
function slider_at(column: number) {
  return {
    position: "absolute",
    left: `${1.4 + column * 6.4}%`,
    top: "55.8%",
    width: "4%",
    height: "23.2%",
  };
}

/**
 * Weather icon, bottom right, beside the beam (free on every model, under
 * the lamps of a virtual LED), as [left, top] in %.
 */
export const WEATHER_ICON: [string, string] = ["91.5%", "88.3%"];

/** A G1 switched to white/blue sliders (K | W/B switch on the card). */
const WHITE_BLUE = "device.white_blue() === true";

/** Sky, beam, sliders and messages: shared by every ReefLED. */
export const view_elements = {
  // Arc and sun/moon: behind the lamp, the arc ends sink behind it
  sky_back: {
    name: "sky_back",
    type: "rsled-sky",
    stateObj: null,
    layer: "back",
    put_in: "back",
    css: FULL_CANVAS,
  },
  beam: {
    name: "beam",
    type: "rsled-beam",
    stateObj: null,
    css: FULL_CANVAS,
  },
  // Name of the lamp, on its upper left face
  lamp_name: {
    name: "lamp_name",
    type: "rsled-name",
    stateObj: null,
    css: FULL_CANVAS,
  },
  // Times, mode and clouds: over the lamp
  sky_front: {
    name: "sky_front",
    type: "rsled-sky",
    stateObj: null,
    layer: "front",
    css: FULL_CANVAS,
  },

  // ── Sliders: intensity + colour, or white + blue; moon always ─────────
  intensity_slider: {
    name: "light.kelvin_intensity",
    type: "rsled-slider",
    attribute: "brightness",
    icon: "mdi:brightness-6",
    step: 1,
    disabled_if: WHITE_BLUE,
    no_br_if_disabled: true,
    css: slider_at(0),
  },
  color_slider: {
    name: "light.kelvin_intensity",
    type: "rsled-slider",
    attribute: "color_temp_kelvin",
    icon: "mdi:palette",
    step: 100,
    disabled_if: WHITE_BLUE,
    no_br_if_disabled: true,
    css: slider_at(1),
  },
  white_slider: {
    name: "light.white",
    type: "rsled-slider",
    attribute: "brightness",
    track: "white",
    icon: "mdi:lightbulb-outline",
    step: 1,
    disabled_if: `!(${WHITE_BLUE})`,
    no_br_if_disabled: true,
    css: slider_at(0),
  },
  blue_slider: {
    name: "light.blue",
    type: "rsled-slider",
    attribute: "brightness",
    track: "blue",
    icon: "mdi:lightbulb",
    step: 1,
    disabled_if: `!(${WHITE_BLUE})`,
    no_br_if_disabled: true,
    css: slider_at(1),
  },
  // Weather program (GPS weather), for information only (the mode is chosen
  // in the program editor): lit while the lamp follows the weather, blue
  // while a weather week is being written to the lamp
  weather: {
    name: "weather_sync",
    type: "click-image",
    icon: "mdi:weather-partly-cloudy",
    icon_color:
      "${entity.weather_program?.attributes?.writing ? '#3fa9f5' : entity.weather_sync?.state === 'on' ? '#f2c230' : 'rgba(127,127,127,0.55)'}",
    // Only with an integration offering the weather program
    disabled_if: "!entity.weather_sync",
    no_br_if_disabled: true,
    // No tap, hold nor double tap action
    css: { ...icon_at(WEATHER_ICON), cursor: "default" },
  },
  moon_slider: {
    name: "light.moon",
    type: "rsled-slider",
    attribute: "brightness",
    track: "moon",
    icon: "mdi:weather-night",
    step: 1,
    css: slider_at(2),
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
      top: "93.6%",
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
      top: "96.4%",
      left: "0px",
    },
    "elt.css": {
      "background-color": "rgba(240,200,200,0.7)",
    },
  },
};

/** Lamps of a group (virtual LED, or a lamp of a group): bottom right. */
export const linked_element = {
  name: "linked_leds",
  type: "rsled-linked",
  stateObj: null,
  css: {
    position: "absolute",
    left: "83%",
    top: "55.8%",
    width: "15.6%",
    // Leaves the bottom right corner to the weather icon
    height: "28%",
  },
};

/** Switched off, the lamp keeps its sky, its switch and its messages. */
export const off_keep: string[] = [
  "sky_back",
  "beam",
  "sky_front",
  "lamp_name",
  "weather",
  "device_state",
  // Maintenance is mostly done with the lamp switched off
  "maintenance_tasks",
  "last_message",
  "last_alert_message",
];

/** What sets a ReefLED model apart in its mapping. */
export interface RSLedModel {
  /** Background picture, drawn on the whole design space */
  image: URL;
  /** Where the icons sit on the faces of the lamp */
  face: FaceLayout;
  /** Geometry of the sky's front layer (mode, clouds), over the defaults */
  sky?: Record<string, unknown>;
  /** Where the name sits and its slant, over the defaults (G1) */
  name?: Record<string, unknown>;
  /** Geometry of the beam (lens, cone), over the defaults (G1) */
  beam?: Record<string, unknown>;
  /**
   * Whether the lamp can be driven channel by channel (G1): the K | W/B
   * switch then swaps intensity/colour for white/blue sliders.
   */
  white_blue: boolean;
}

/**
 * Remove the switch condition of an intensity/colour slider: without the
 * white/blue mode, they always show.
 * @param slider: the slider mapping
 */
function always(slider: any) {
  const { disabled_if: _d, ...rest } = slider;
  return rest;
}

/**
 * Mapping of a ReefLED model.
 * @param model: what sets the model apart
 */
export function rsled_config(model: RSLedModel) {
  const { white_slider, blue_slider, ...view } = view_elements;
  const elements: Record<string, any> = model.white_blue
    ? { ...view, white_slider, blue_slider }
    : {
        ...view,
        intensity_slider: always(view.intensity_slider),
        color_slider: always(view.color_slider),
      };
  if (model.sky) {
    elements.sky_front = { ...view.sky_front, geometry: model.sky };
  }
  if (model.name) {
    elements.lamp_name = { ...view.lamp_name, geometry: model.name };
  }
  if (model.beam) {
    elements.beam = { ...view.beam, geometry: model.beam };
  }
  return {
    name: null,
    model: "RSLED",
    background_img: model.image,
    css: {
      width: "100%",
    },
    off_keep: [...off_keep, "linked"],
    elements: {
      ...elements,
      ...face_elements(model.face),
      // The lamps of its group, when the lamp is in one
      linked: linked_element,
    },
  };
}

/**
 * Elements a virtual ReefLED has no entity for: its switches, identify and
 * acclimation are broadcast to its lamps, but it has no battery, wifi nor
 * messages of its own.
 */
export const VIRTUAL_MISSING: string[] = [
  "battery_level",
  "wifi_quality",
  "last_message",
  "last_alert_message",
];

/**
 * Mapping of a virtual ReefLED: the view of the generation it drives (G2 as
 * soon as one of its lamps is a G2), without what only a real lamp has,
 * plus the list of its lamps.
 * @param model: the generation shown
 */
export function rsled_virtual_config(model: RSLedModel) {
  const base = rsled_config(model);
  const elements: Record<string, any> = {};
  for (const [key, elt] of Object.entries(base.elements)) {
    if (!VIRTUAL_MISSING.includes(key)) elements[key] = elt;
  }
  return {
    ...base,
    model: "virtual_led",
    off_keep: base.off_keep.filter((key) => !VIRTUAL_MISSING.includes(key)),
    elements,
  };
}

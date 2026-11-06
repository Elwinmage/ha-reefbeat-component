/**
 * ReefLED G2 (RSLED60, RSLED115, RSLED170) mapping: see
 * rsled.common.mapping.ts for the view every ReefLED shares. The rounder lamp
 * moves the icons on its faces and its higher top pushes the mode up. The G2
 * has no white/blue lights: its colour only goes through kelvin and
 * intensity, so the white/blue sliders never show.
 */
import { FaceLayout, rsled_config } from "./rsled.common.mapping";

/**
 * G2: rounded lamp, faces on the smooth band under the vents. The left face
 * holds six icons, 6.6% apart: they start close to its left edge so the last
 * one stays on the flat of the face, clear of the front corner. The band is
 * too narrow on the right face for a line under icons in its middle: they
 * sit in its upper third, leaving the lower one to the countdown.
 */
export const G2_FACE: FaceLayout = {
  device_state: ["5.5%", "39.6%"],
  maintenance: ["12.1%", "37.5%"],
  configuration: ["18.7%", "35.4%"],
  battery_level: ["25.3%", "33.2%"],
  wifi_quality: ["31.9%", "31.1%"],
  maintenance_tasks: ["38.5%", "29%"],
  poseidon: ["48.3%", "28.8%"],
  // Right face: icons in the upper third of the band, the manual mode
  // countdown under them
  identify: ["58.4%", "25.8%"],
  moon_phase: ["68.5%", "29.9%"],
  acclimation: ["78.7%", "33.7%"],
  acclimation_text: ["85.5%", "34.7%"],
  right_skew: "21deg",
  countdown: ["68.5%", "33.6%"],
  countdown_rotate: "7deg",
};

/** The G2 top rises higher than the G1's: the mode goes up with it. */
export const G2_SKY = {
  mode: { x: 295.5, y: 84 },
  clouds: { x: 405, y: 78 },
};

/** The G2's face is less steep and higher than the G1's. */
export const G2_NAME = { x: 118, y: 278, angle: -27 };

/** The G2's lens is a little higher and rounder than the G1's. */
export const G2_BEAM = {
  lens: { cx: 300, cy: 418, rx: 152, ry: 70 },
};

export const config2 = rsled_config({
  image: new URL("../../../img/redsea/RSLED/rsled_g2.png", import.meta.url),
  face: G2_FACE,
  sky: G2_SKY,
  name: G2_NAME,
  beam: G2_BEAM,
  white_blue: false,
});

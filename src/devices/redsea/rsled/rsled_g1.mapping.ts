/**
 * ReefLED G1 (RSLED50, RSLED90, RSLED160) mapping: see rsled.common.mapping.ts
 * for the view every ReefLED shares.
 */
import { FaceLayout, rsled_config } from "./rsled.common.mapping";

/**
 * G1: square lamp, faces along the lower edge of the vents. The left face
 * holds six icons, 6.8% apart: they start close to its left edge so the last
 * one stays on the flat of the face, clear of the front corner.
 */
export const G1_FACE: FaceLayout = {
  device_state: ["5.5%", "45.2%"],
  maintenance: ["12.3%", "41.9%"],
  configuration: ["19.1%", "38.5%"],
  battery_level: ["25.9%", "35.2%"],
  wifi_quality: ["32.7%", "31.8%"],
  maintenance_tasks: ["39.5%", "28.5%"],
  poseidon: ["47%", "27.8%"],
  identify: ["56%", "27.9%"],
  moon_phase: ["67%", "31.2%"],
  acclimation: ["78%", "34.5%"],
  acclimation_text: ["84.5%", "34.2%"],
  right_skew: "19deg",
  // Under the moon, on the face below the icons
  countdown: ["67%", "35.2%"],
  countdown_rotate: "4deg",
};

export const config = rsled_config({
  image: new URL("../../../img/redsea/RSLED/rsled_g1.png", import.meta.url),
  face: G1_FACE,
  white_blue: true,
});

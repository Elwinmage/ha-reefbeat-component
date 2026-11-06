/**
 * Poseidon shortcut of a device.
 *
 * A trident icon every Red Sea mapping places on its own picture, shown once
 * the device has the Poseidon entities of the redsea integration (its keys
 * are known): `poseidon_mode` (switch), `poseidon_strategy` (select) and
 * `poseidon_poll_pause` (switch). The icon hides itself on a device without
 * them, so a mapping can declare it unconditionally.
 *
 *   - colour: the mapping's "on" colour in Poseidon mode, its "off" colour
 *     out of it or while the mode cannot be read (unavailable), orange and
 *     blinking when the device is in Poseidon mode but nothing went through
 *     the relay for a while (`silent` attribute);
 *   - hold: switches the Poseidon mode on or off. Not on a tap: the mode
 *     moves the device to another broker, it must not change by accident;
 *   - tap: opens the `poseidon` dialog (mode, strategy, polling pause).
 *
 * Works whether the device is on or off: the mode has nothing to do with
 * the device's own on/off switch.
 */
import { COLOR_ERROR_HEX, COLOR_ORANGE_HEX } from "../../../utils/colors";

/** Key of the shortcut in the `elements` of a mapping. */
export const POSEIDON_SHORTCUT = "poseidon";

/** Translation key of the Poseidon mode switch. */
export const POSEIDON_MODE = "poseidon_mode";

/** Colour of the icon out of Poseidon mode, when the mapping gives none. */
export const POSEIDON_OFF_COLOR = "#666666";

/**
 * Mapping entry of the Poseidon shortcut.
 * @param css: where the mapping puts the icon on its picture
 * @param off_color: colour of the icon out of Poseidon mode (a dark picture
 *                   needs a lighter one to stay visible)
 * @param icon_color: colour of the icon in Poseidon mode
 * @return the element configuration
 */
export function poseidon_shortcut(
  css: Record<string, string>,
  off_color: string = POSEIDON_OFF_COLOR,
  icon_color: string = COLOR_ERROR_HEX,
) {
  const mode = `entity.${POSEIDON_MODE}`;
  return {
    name: POSEIDON_SHORTCUT,
    type: "click-image",
    // The state is read through `entity`: the element itself is bound to
    // nothing, so a device without the switch never resolves a missing one
    stateObj: null,
    icon: "redsea:trident",
    icon_color:
      "${" +
      `${mode}?.state !== 'on' ? '${off_color}' : ` +
      `(${mode}?.attributes?.silent ? '${COLOR_ORANGE_HEX}' : '${icon_color}')` +
      "}",
    // In Poseidon mode with no traffic through the relay: blink
    class:
      "${" +
      `${mode}?.state === 'on' && ${mode}?.attributes?.silent ? 'blink' : ''` +
      "}",
    off_clickable: true,
    disabled_if: `!${mode}`,
    // Absolutely positioned: never emit a <br> that shifts the flow
    no_br_if_disabled: true,
    tap_action: {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: POSEIDON_SHORTCUT },
    },
    hold_action: {
      domain: "switch",
      action: "toggle",
      data: { entity_id: POSEIDON_MODE },
    },
    css,
  };
}

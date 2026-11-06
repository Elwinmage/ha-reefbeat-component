/**
 * Content of the `messages_history` dialog (see device.dialogs.ts).
 *
 * The dialog shows the history of the messages and alerts of the device it
 * was opened from (a click on its scrolling message banner). The history is
 * a Lit element of its own: built once when the dialog opens, then only
 * handed the new hass on every update (`re_render: true` on the extend
 * view), so the chosen filter and period survive state changes.
 */

import "../base/messages_history";
import type { MessageKind, RSMessagesHistory } from "../base/messages_history";

/** Id of the history element inside #dialog-content. */
const VIEW_ID = "device-messages-history";

/**
 * Fill the messages_history dialog with the history of the device.
 *
 * Called once when the dialog opens, then on every hass update.
 * @param elt: the element that opened the dialog (the message banner)
 * @param hass: the current Home Assistant object
 * @param shadowRoot: the dialog shadow root
 * @return nothing
 */
export function messages_history(elt: any, hass: any, shadowRoot: any): void {
  const device = elt?.device;
  const container = shadowRoot?.querySelector("#dialog-content");
  if (!device || !container) return;

  const previous = shadowRoot.querySelector(
    "#" + VIEW_ID,
  ) as RSMessagesHistory | null;
  if (previous) {
    previous.hass = hass;
    return;
  }

  const view = document.createElement(
    "redsea-messages-history",
  ) as RSMessagesHistory;
  view.id = VIEW_ID;
  view.device = device;
  // Opened from the alert banner: show the alerts first
  const name = elt?.conf?.name;
  if (name === "last_message" || name === "last_alert_message") {
    view.kind = name as MessageKind;
  }
  view.hass = hass;
  container.appendChild(view);
}

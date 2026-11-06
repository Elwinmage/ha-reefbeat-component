/**
 * An auto scrolling text implemntation
 *
 * The text starts with the date of the message (sensor attribute
 * `timestamp`). A click on the text opens the message history of the device
 * (dialog `messages_history`, see device.dialogs.ts).
 */

//----------------------------------------------------------------------------//
//   IMPORT
//----------------------------------------------------------------------------//
import { html } from "lit";

import type { Action, ElementConfig } from "../types/element";
import { MyElement } from "./element";
import { format_short } from "./messages_format";
import i18n from "../translations/myi18n.js";

import style_messages from "./messages.styles";

//----------------------------------------------------------------------------//
export class RSMessages extends MyElement {
  static override styles = style_messages;

  /**
   * Constructor
   */
  constructor() {
    super();
  }

  /**
   * Render
   * @param _style: Not used here
   */
  protected override _render(_style?: string): any {
    const sclass = this.conf?.class || "";
    let trash: any = null;
    const computed_style = this.get_style("elt.css");

    if (!this.stateObj) {
      return html``;
    }

    let value = this.stateObj.state;
    if (value === "unavailable" || value === "unknown" || value.length === 0) {
      // Nothing to show: render no content at all, so the band overlaps its
      // neighbours without taking their clicks.
      return html``;
    }
    if (this.conf && "label" in this.conf) {
      value = this.conf.label + value + this.conf.label;
    }
    const date = format_short(this.stateObj.attributes?.timestamp, this._hass);
    if (date) {
      value = `${date} · ${value}`;
    }
    // Add a trash button to clean the message queue
    const conf: ElementConfig = {
      type: "click-image",
      name: "trash",
      stateObj: false,
      image: "/hacsfiles/ha-reef-card/img/trash.svg",
      tap_action: {
        domain: "redsea",
        action: "clean_message",
        data: {
          device_id: this.device?.device?.elements?.[0]?.primary_config_entry,
          msg_type: this.conf?.name,
        },
      },
      css: {
        display: "inline-block",
        position: "absolute",
        right: "0px",
      },
    };

    if (this._hass && this.device) {
      trash = MyElement.create_element(this._hass, conf, this.device);
    }

    return html`
      <div class="messages_content" style=${computed_style}>
        <marquee
          class="${sclass} messages_text"
          title="${i18n._("messages_history_open")}"
          @click=${(e: Event) => this._open_history(e)}
        >
          ${value}
        </marquee>
        ${trash}
      </div>
    `;
  }

  /**
   * Open the message history of the device.
   *
   * Works whether the device is on or off: reading the history acts on
   * nothing.
   * @param e: the click event, kept from the element's own tap handling
   */
  protected _open_history(e: Event): void {
    e.stopPropagation();
    const action: Action = {
      domain: "redsea_ui",
      action: "dialog",
      data: { type: "messages_history" },
    };
    this.run_actions(action);
  }
}

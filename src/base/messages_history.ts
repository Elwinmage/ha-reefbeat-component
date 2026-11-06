/**
 * History of the messages and alerts of a device.
 *
 * Shown in the `messages_history` dialog (see device.dialogs.ts), opened by a
 * click on the scrolling message banner. The entries come from the
 * integration's `redsea.get_messages` service; the view reloads them when a
 * new message or alert arrives (the `timestamp` attribute of the message
 * sensors changes) while it is open.
 */

//----------------------------------------------------------------------------//
//   IMPORT
//----------------------------------------------------------------------------//
import { LitElement, html, nothing } from "lit";

import i18n from "../translations/myi18n.js";
import { format_long } from "./messages_format";
import style_messages_history from "./messages_history.styles";

//----------------------------------------------------------------------------//

/** Kind of message, named after its sensor. */
export type MessageKind = "All" | "last_message" | "last_alert_message";

/** One entry of the history, as sent by the integration. */
export interface MessageEntry {
  ts: string;
  type: "last_message" | "last_alert_message";
  text: string;
  method?: string;
  path?: string;
  status?: number;
}

/** Periods offered, in days (0: everything kept). */
export const PERIODS: number[] = [1, 7, 31, 0];

/** Sensors whose timestamp tells a new entry came. */
const SENSORS: string[] = ["last_message", "last_alert_message"];

export class RSMessagesHistory extends LitElement {
  static override styles = style_messages_history;

  static override get properties() {
    return {
      kind: { state: true },
      period: { state: true },
      entries: { state: true },
      loading: { state: true },
      error: { state: true },
      retention: { state: true },
    };
  }

  /** The device the history is of (an RSDevice). */
  device: any = null;
  /** Which kind of entries are shown. */
  kind: MessageKind = "All";
  /** Period shown, in days (0: everything kept). */
  period: number = 7;
  entries: MessageEntry[] = [];
  loading: boolean = false;
  error: string = "";
  /** Retention of the integration, in days (from the last answer). */
  retention: number | null = null;

  private _hass: any = null;
  // Timestamps of the message sensors at the last load
  private _signature: string | null = null;
  // Rank of the last request: an older answer never replaces a newer one
  private _request: number = 0;

  /**
   * Home Assistant object. A new message or alert reloads the list.
   */
  set hass(hass: any) {
    this._hass = hass;
    const signature = this._sensors_signature();
    if (signature !== this._signature) {
      this._signature = signature;
      void this.load();
    }
  }

  get hass(): any {
    return this._hass;
  }

  /**
   * Config entry of the device (the service's device_id).
   */
  private _entry_id(): string | undefined {
    return (
      this.device?.device?.elements?.[0]?.primary_config_entry ?? undefined
    );
  }

  /**
   * Timestamps of the device's message sensors, joined.
   */
  private _sensors_signature(): string {
    const states = this._hass?.states ?? {};
    return SENSORS.map((name) => {
      const ent =
        this.device?.entities?.[name] ?? this.device?.parent_entities?.[name];
      const st = ent?.entity_id ? states[ent.entity_id] : undefined;
      return String(st?.attributes?.timestamp ?? "");
    }).join("|");
  }

  /**
   * Load the entries of the current kind and period.
   */
  async load(): Promise<void> {
    const hass = this._hass;
    const device_id = this._entry_id();
    if (!device_id || typeof hass?.callWS !== "function") {
      this.error = i18n._("messages_history_unavailable");
      return;
    }
    const request = ++this._request;
    this.loading = true;
    const service_data: Record<string, unknown> = {
      device_id,
      msg_type: this.kind,
    };
    if (this.period > 0) service_data.days = this.period;
    try {
      const answer = await hass.callWS({
        type: "call_service",
        domain: "redsea",
        service: "get_messages",
        service_data,
        return_response: true,
      });
      if (request !== this._request) return;
      const response = answer?.response ?? {};
      if (response.error) {
        this.error = String(response.error);
        this.entries = [];
      } else {
        this.error = "";
        this.entries = Array.isArray(response.messages)
          ? (response.messages as MessageEntry[])
          : [];
        this.retention =
          typeof response.retention_days === "number"
            ? response.retention_days
            : null;
      }
    } catch (err: any) {
      if (request !== this._request) return;
      this.error = String(err?.message ?? err);
      this.entries = [];
    } finally {
      if (request === this._request) this.loading = false;
    }
  }

  /**
   * Show another kind of entries.
   * @param kind: the kind to show
   */
  private _set_kind(kind: MessageKind): void {
    if (kind === this.kind) return;
    this.kind = kind;
    void this.load();
  }

  /**
   * Show another period.
   * @param e: change event of the period select
   */
  private _set_period(e: Event): void {
    const value = Number((e.target as HTMLSelectElement).value);
    if (Number.isNaN(value) || value === this.period) return;
    this.period = value;
    void this.load();
  }

  /**
   * Label of a period.
   * @param days: the period, 0 for everything kept
   */
  private _period_label(days: number): string {
    if (days === 0) return i18n._("messages_history_all_kept");
    if (days === 1) return i18n._("messages_history_24h");
    return i18n._("messages_history_days", { days });
  }

  private _render_entry(entry: MessageEntry) {
    const alert = entry.type === "last_alert_message";
    const where = [entry.method?.toUpperCase(), entry.path]
      .filter((x) => x)
      .join(" ");
    const detail = [where, entry.status ? String(entry.status) : ""]
      .filter((x) => x)
      .join(" · ");
    return html`
      <li class="entry ${alert ? "alert" : "message"}">
        <span class="kind" aria-hidden="true">${alert ? "⚠" : "✓"}</span>
        <div class="body">
          <div class="head">
            <time datetime="${entry.ts}"
              >${format_long(entry.ts, this._hass)}</time
            >
            ${detail ? html`<span class="detail">${detail}</span>` : nothing}
          </div>
          <div class="text">${entry.text}</div>
        </div>
      </li>
    `;
  }

  override render() {
    const kinds: { kind: MessageKind; key: string }[] = [
      { kind: "All", key: "messages_history_filter_all" },
      { kind: "last_message", key: "messages_history_filter_messages" },
      { kind: "last_alert_message", key: "messages_history_filter_alerts" },
    ];
    return html`
      <div class="root">
        <div class="toolbar">
          <div class="kinds" role="group">
            ${kinds.map(
              (k) => html`
                <button
                  class="${k.kind === this.kind ? "active" : ""}"
                  aria-pressed="${k.kind === this.kind}"
                  @click=${() => this._set_kind(k.kind)}
                >
                  ${i18n._(k.key)}
                </button>
              `,
            )}
          </div>
          <select
            class="period"
            aria-label="${i18n._("messages_history_period")}"
            @change=${(e: Event) => this._set_period(e)}
          >
            ${PERIODS.map(
              (d) =>
                html`<option value="${d}" ?selected=${d === this.period}>
                  ${this._period_label(d)}
                </option>`,
            )}
          </select>
          <button
            class="refresh"
            title="${i18n._("messages_history_refresh")}"
            aria-label="${i18n._("messages_history_refresh")}"
            ?disabled=${this.loading}
            @click=${() => void this.load()}
          >
            ⟳
          </button>
        </div>
        ${
          this.error
            ? html`<div class="error">${this.error}</div>`
            : this.entries.length === 0
              ? html`<div class="empty">
                  ${
                    this.loading
                      ? i18n._("messages_history_loading")
                      : i18n._("messages_history_empty")
                  }
                </div>`
              : html`<ul class="list">
                  ${this.entries.map((e) => this._render_entry(e))}
                </ul>`
        }
        <div class="footer">
          ${i18n._("messages_history_count", { count: this.entries.length })}
          ${
            this.retention
              ? html` ·
                ${i18n._("messages_history_retention", {
                  days: this.retention,
                })}`
              : nothing
          }
        </div>
      </div>
    `;
  }
}

if (!customElements.get("redsea-messages-history"))
  customElements.define("redsea-messages-history", RSMessagesHistory);

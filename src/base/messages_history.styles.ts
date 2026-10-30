import { css } from "lit";

/**
 * Styles of the message history (dialog `messages_history`).
 *
 * Colors follow the active Home Assistant theme, with fallbacks for a
 * standalone rendering.
 */
export default css`
  :host {
    --mh-text: var(--primary-text-color, #e1e1e1);
    --mh-text-soft: var(--secondary-text-color, #9b9b9b);
    --mh-divider: var(--divider-color, rgba(127, 127, 127, 0.3));
    --mh-accent: var(--primary-color, #03a9f4);
    --mh-alert: var(--error-color, #db4437);
    --mh-ok: var(--success-color, #43a047);
    display: block;
  }

  .root {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 4px 12px 4px;
    color: var(--mh-text);
    font-size: 14px;
    min-width: min(480px, 80vw);
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .kinds {
    display: inline-flex;
    border: 1px solid var(--mh-divider);
    border-radius: 16px;
    overflow: hidden;
  }

  .kinds button {
    border: none;
    background: transparent;
    color: var(--mh-text);
    padding: 4px 12px;
    font: inherit;
    cursor: pointer;
  }

  .kinds button + button {
    border-left: 1px solid var(--mh-divider);
  }

  .kinds button.active {
    background: var(--mh-accent);
    color: var(--text-primary-color, #fff);
  }

  .period {
    font: inherit;
    color: var(--mh-text);
    background: var(--card-background-color, transparent);
    border: 1px solid var(--mh-divider);
    border-radius: 4px;
    padding: 3px 6px;
  }

  .refresh {
    margin-left: auto;
    border: 1px solid var(--mh-divider);
    border-radius: 50%;
    width: 28px;
    height: 28px;
    background: transparent;
    color: var(--mh-text);
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
  }

  .refresh[disabled] {
    opacity: 0.5;
    cursor: default;
  }

  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 60vh;
    overflow-y: auto;
  }

  .entry {
    display: flex;
    gap: 8px;
    padding: 6px 2px;
    border-bottom: 1px solid var(--mh-divider);
  }

  .entry:last-child {
    border-bottom: none;
  }

  .kind {
    flex: 0 0 auto;
    width: 1.2em;
    text-align: center;
    color: var(--mh-ok);
  }

  .entry.alert .kind,
  .entry.alert .text {
    color: var(--mh-alert);
  }

  .body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .head {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    font-size: 12px;
    color: var(--mh-text-soft);
  }

  time {
    font-variant-numeric: tabular-nums;
  }

  .text {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .empty,
  .error {
    padding: 16px 4px;
    text-align: center;
    color: var(--mh-text-soft);
  }

  .error {
    color: var(--mh-alert);
  }

  .footer {
    font-size: 12px;
    color: var(--mh-text-soft);
    text-align: right;
  }
`;

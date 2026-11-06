/**
 * Date formatting of the device messages (banner and history).
 */

import i18n from "../translations/myi18n.js";

/**
 * Locale to format dates with: Home Assistant's, else the card's language.
 * @param hass: the Home Assistant object (may be null)
 */
function locale_of(hass: any): string {
  return hass?.locale?.language || hass?.language || i18n.getLanguage() || "en";
}

/**
 * Parse an ISO timestamp.
 * @param ts: the timestamp sent by the integration
 * @return the date, or null when missing or unreadable
 */
export function parse_ts(ts: unknown): Date | null {
  if (typeof ts !== "string" || !ts) return null;
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Short date and time for the scrolling banner (day, month, hour, minute).
 * @param ts: ISO timestamp
 * @param hass: the Home Assistant object
 * @return the formatted date, or "" when there is none
 */
export function format_short(ts: unknown, hass: any): string {
  const d = parse_ts(ts);
  if (!d) return "";
  try {
    return d.toLocaleString(locale_of(hass), {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return d.toISOString().slice(5, 16).replace("T", " ");
  }
}

/**
 * Full date and time for the history (with year and seconds).
 * @param ts: ISO timestamp
 * @param hass: the Home Assistant object
 * @return the formatted date, or "" when there is none
 */
export function format_long(ts: unknown, hass: any): string {
  const d = parse_ts(ts);
  if (!d) return "";
  try {
    return d.toLocaleString(locale_of(hass), {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return d.toISOString().slice(0, 19).replace("T", " ");
  }
}

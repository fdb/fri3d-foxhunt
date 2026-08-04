const NAME_MAX = 32;

// Name: 1-32 code points, base UTF-8 (accents, Cyrillic, CJK fine) but no
// emoji: reject astral-plane code points, misc symbols/dingbats, variation
// selectors, zero-width joiners and control characters.
export function validateName(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const name = raw.trim();
  const chars = [...name];
  if (chars.length === 0 || chars.length > NAME_MAX) return null;
  for (const ch of chars) {
    const cp = ch.codePointAt(0)!;
    if (cp < 0x20 || cp === 0x7f) return null; // control chars
    if (cp > 0xffff) return null; // astral plane (emoji, etc.)
    if (cp >= 0x2600 && cp <= 0x27bf) return null; // misc symbols, dingbats
    if (cp >= 0xfe00 && cp <= 0xfe0f) return null; // variation selectors
    if (cp === 0x200d) return null; // zero-width joiner
  }
  return name;
}

// Badge id: machine.unique_id() rendered as hex (colons/dashes tolerated).
export function validateBadgeId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const badgeId = raw.trim().toLowerCase();
  if (!/^[0-9a-f:-]{6,64}$/.test(badgeId)) return null;
  return badgeId;
}

// Hunter id: the LoRa address, 0-9999 — one per badge at the camp, so it has
// to hold hundreds, not the 32 that fox_id gets away with. Four digits keeps
// the "JGR-0042" label fixed-width and fits a uint16 on the wire. Returns the
// number, null when absent/cleared, or "invalid".
export const HUNTER_ID_MAX = 9999;

export function validateHunterId(raw: unknown): number | null | "invalid" {
  if (raw === undefined || raw === null) return null;
  if (typeof raw !== "number" || !Number.isInteger(raw)) return "invalid";
  if (raw < 0 || raw > HUNTER_ID_MAX) return "invalid";
  return raw;
}

// Profile pic: the companion shortcode "H<head>A<mask>C<colour>", e.g. "H1A003C1"
// — head and backdrop are 1-based indices, mask is a 12-bit accessory bitmask
// in hex (see companion.py, which owns the format). Stored as-is; the badge is
// the only thing that renders it, and it tolerates indices it doesn't know.
const COMPANION_RE = /^H[1-9]A[0-9A-F]{3}C[1-9]$/;

export function validateProfilePic(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const code = raw.trim().toUpperCase();
  if (!COMPANION_RE.test(code)) return null;
  return code;
}

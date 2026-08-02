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

// Hunter id: 5-bit LoRa id. Returns the number, null when absent/cleared,
// or "invalid".
export function validateHunterId(raw: unknown): number | null | "invalid" {
  if (raw === undefined || raw === null) return null;
  if (typeof raw !== "number" || !Number.isInteger(raw)) return "invalid";
  if (raw < 0 || raw > 31) return "invalid";
  return raw;
}

export function validateProfilePic(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  if (raw.length > 255) return null;
  return raw;
}

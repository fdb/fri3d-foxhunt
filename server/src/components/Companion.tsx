import { decodeCompanion } from "../lib/companion";
import { COMPANION_ART } from "../lib/companion-art";

/**
 * The player's companion, drawn the way the badge draws it: the backdrop
 * colour, then the head, then every accessory the player wears, stacked in
 * ACCS order — never in the order they were picked, so the same shortcode
 * always produces the same picture on both screens.
 *
 * On the badge that stack is LVGL layers inside a 16*scale box
 * (companion.draw); here it is absolutely-positioned <img> in a square. The
 * source art is 16x16, so `size` should stay a multiple of 16 and
 * `image-rendering: pixelated` does the nearest-neighbour scaling. The badge
 * cannot lean on that — LVGL's software transform mangles scaled sprites, so
 * art.sprite_img pre-scales by pixel replication — but a browser gets it
 * right, and one 16px PNG serves every size.
 *
 * The sterren twinkle is deliberately not ported: it is a payoff for the
 * player looking at their own maatje, not something a debug list needs.
 */
export const Companion = ({
  code,
  size = 64,
  title,
}: {
  code: string | null;
  size?: number;
  title?: string;
}) => {
  const c = decodeCompanion(code);
  const layers = [c.head, ...c.accs].filter((id) => COMPANION_ART[id]);
  return (
    <span
      class="maatje"
      title={title ?? code ?? undefined}
      style={`width:${size}px;height:${size}px;background:${c.bg}`}
    >
      {layers.map((id) => (
        <img src={COMPANION_ART[id]} alt="" width={size} height={size} />
      ))}
    </span>
  );
};

import { ICON_ART } from "../lib/icon-art";

/**
 * One of the badge's own UI icons, drawn as SVG.
 *
 * The site's cards used to be labelled with emoji, which read as decoration
 * borrowed from somewhere else. These are the same pictures the badge draws
 * on its own screens — the antenna from the jager check, the two noses from
 * snuffelen, the hand plucking a berry — so a card and the screen it
 * describes now carry one image.
 *
 * The source is a grid of palette characters (art.py ICONS), baked to
 * horizontal runs by scripts/bake_server_icons.sh. Every run is one <rect> of
 * height 1 in grid units; the viewBox does the scaling, so the pixels stay
 * square at any card size. `shape-rendering: crispEdges` is what keeps the
 * seams between neighbouring runs from showing as hairlines — a fill and its
 * neighbour meet on an exact pixel boundary, and antialiasing would draw a
 * pale line down the middle of the antenna mast.
 *
 * Grids differ (5x5 to 16x16), so the drawn box is fixed and the art centres
 * inside it: a set of icons has to look like a set.
 */
export const Icon = ({ name }: { name: string }) => {
  const art = ICON_ART[name];
  if (!art) return null;
  return (
    <svg
      class="icon-art"
      viewBox={`0 0 ${art.w} ${art.h}`}
      aria-hidden="true"
      shape-rendering="crispEdges"
    >
      {art.runs.map(([x, y, w, fill]) => (
        <rect x={x} y={y} width={w} height="1" fill={fill} />
      ))}
    </svg>
  );
};

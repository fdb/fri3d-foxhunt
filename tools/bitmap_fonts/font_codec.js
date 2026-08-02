// font_codec.js — BDF <-> glyph model <-> LVGL .bin, no dependencies.
// Isomorphic: attaches to window in the browser, exports in node.
//
// Glyph model:
//   font = { meta:{ name, size, ascent, descent, defaultChar, props{} },
//            glyphs:[ { code, name, advanceWidth, bbox:{x,y,width,height},
//                       pixels:[[0|1,...] x width] x height } ] }   (rows top->bottom)
//
// The LVGL .bin layout (tables head/cmap/loca/glyf) is ported faithfully from
// lv_font_conv so output is byte-identical to `lv_font_conv --bpp 1 --no-compress`.
(function (root) {
  "use strict";

  // ---- bit helpers (ported from lv_font_conv utils) ----
  function count_bits(val) {
    let c = 0; val = Math.trunc(val);
    while (val) { c++; val >>= 1; }
    return c;
  }
  const unsigned_bits = count_bits;
  function signed_bits(val) {
    if (val >= 0) return count_bits(val) + 1;
    return count_bits(Math.abs(val) - 1) + 1;
  }
  const align4 = (n) => (n % 4 === 0 ? n : n + 4 - (n % 4));

  // MSB-first big-endian bit writer; finish() pads to a whole byte.
  class BitW {
    constructor() { this.bytes = []; this.cur = 0; this.n = 0; }
    writeBits(val, bits) {
      for (let i = bits - 1; i >= 0; i--) {
        this.cur = (this.cur << 1) | ((val >> i) & 1);
        if (++this.n === 8) { this.bytes.push(this.cur & 0xff); this.cur = 0; this.n = 0; }
      }
    }
    finish() {
      if (this.n > 0) { this.bytes.push((this.cur << (8 - this.n)) & 0xff); this.cur = 0; this.n = 0; }
      return this.bytes;
    }
  }

  // little-endian byte emitters into a plain number[]
  const u8 = (a, v) => a.push(v & 0xff);
  const u16 = (a, v) => { a.push(v & 0xff, (v >>> 8) & 0xff); };
  const i16 = u16;
  const u32 = (a, v) => { a.push(v & 0xff, (v >>> 8) & 0xff, (v >>> 16) & 0xff, (v >>> 24) & 0xff); };
  const tag = (a, s) => { for (let i = 0; i < 4; i++) a.push(s.charCodeAt(i)); };
  const pad4 = (a) => { while (a.length % 4) a.push(0); };

  // =====================================================================
  // BDF parsing
  // =====================================================================
  function parseBDF(text) {
    const meta = { name: "", size: 0, ascent: 0, descent: 0, defaultChar: 0, props: {} };
    const glyphs = [];
    const lines = text.split(/\r?\n/);
    let i = 0, cur = null, inProps = false;
    while (i < lines.length) {
      const line = lines[i].trim(); i++;
      const sp = line.indexOf(" ");
      const key = sp < 0 ? line : line.slice(0, sp);
      const rest = sp < 0 ? "" : line.slice(sp + 1);
      if (key === "FONT") meta.name = rest;
      else if (key === "SIZE") meta.size = parseInt(rest);
      else if (key === "FONT_ASCENT") meta.ascent = parseInt(rest);
      else if (key === "FONT_DESCENT") meta.descent = -Math.abs(parseInt(rest)); // baseline-relative (negative below baseline)
      else if (key === "DEFAULT_CHAR") meta.defaultChar = parseInt(rest);
      else if (key === "STARTPROPERTIES") inProps = true;
      else if (key === "ENDPROPERTIES") inProps = false;
      else if (key === "STARTCHAR") cur = { name: rest, code: -1, advanceWidth: 0, bbox: { x: 0, y: 0, width: 0, height: 0 }, pixels: [] };
      else if (key === "ENCODING") cur.code = parseInt(rest);
      else if (key === "DWIDTH") cur.advanceWidth = parseInt(rest);
      else if (key === "BBX") { const [w, h, x, y] = rest.split(/\s+/).map(Number); cur.bbox = { x, y, width: w, height: h }; }
      else if (key === "BITMAP") {
        const { width: w, height: h } = cur.bbox;
        for (let r = 0; r < h; r++) {
          const hex = (lines[i] || "").trim(); i++;
          let bigint = BigInt("0x" + (hex || "0"));
          const bitsInRow = Math.ceil(w / 8) * 8;
          const rowbits = [];
          for (let c = bitsInRow - 1; c >= 0; c--) rowbits[c] = Number((bigint >> BigInt(bitsInRow - 1 - c)) & 1n);
          cur.pixels.push(rowbits.slice(0, w));
        }
      } else if (key === "ENDCHAR") { if (cur && cur.code >= 0) glyphs.push(cur); cur = null; }
      else if (inProps && key) meta.props[key] = rest;
    }
    glyphs.sort((a, b) => a.code - b.code);
    return { meta, glyphs };
  }

  // =====================================================================
  // BDF serialization
  // =====================================================================
  function serializeBDF(font) {
    const { meta, glyphs } = font;
    const sorted = [...glyphs].sort((a, b) => a.code - b.code);
    // font bounding box
    let fbbW = 1, fbbH = 1, fbbX = 0, fbbY = 0;
    for (const g of sorted) if (g.bbox.height) {
      fbbW = Math.max(fbbW, g.bbox.width); fbbH = Math.max(fbbH, g.bbox.height);
      fbbX = Math.min(fbbX, g.bbox.x); fbbY = Math.min(fbbY, g.bbox.y);
    }
    const out = [];
    out.push("STARTFONT 2.1");
    out.push(`FONT ${meta.name || "-bitmap-Medium-R-Normal--" + meta.size + "-100-75-75-P-100-ISO10646-1"}`);
    out.push(`SIZE ${meta.size || (meta.ascent - meta.descent)} 75 75`);
    out.push(`FONTBOUNDINGBOX ${fbbW} ${fbbH} ${fbbX} ${fbbY}`);
    out.push("STARTPROPERTIES 3");
    out.push(`FONT_ASCENT ${meta.ascent}`);
    out.push(`FONT_DESCENT ${Math.abs(meta.descent)}`);
    out.push(`DEFAULT_CHAR ${meta.defaultChar || 32}`);
    out.push("ENDPROPERTIES");
    out.push(`CHARS ${sorted.length}`);
    for (const g of sorted) {
      out.push(`STARTCHAR ${g.name || ("U+" + g.code.toString(16).toUpperCase().padStart(4, "0"))}`);
      out.push(`ENCODING ${g.code}`);
      out.push(`SWIDTH ${meta.size ? Math.round(g.advanceWidth / meta.size * 1000) : g.advanceWidth * 100} 0`);
      out.push(`DWIDTH ${g.advanceWidth} 0`);
      const { x, y, width: w, height: h } = g.bbox;
      out.push(`BBX ${w || 1} ${h || 1} ${x} ${y}`);
      out.push("BITMAP");
      const nyb = Math.ceil((w || 1) / 8) * 2;
      for (let r = 0; r < (h || 0); r++) {
        let bits = "";
        for (let c = 0; c < w; c++) bits += g.pixels[r][c] ? "1" : "0";
        bits = bits.padEnd(nyb * 4, "0");
        let s = "";
        for (let b = 0; b < bits.length; b += 8) s += parseInt(bits.slice(b, b + 8), 2).toString(16).padStart(2, "0");
        out.push(s.toUpperCase());
      }
      if (!h) out.push("00");
      out.push("ENDCHAR");
    }
    out.push("ENDFONT");
    return out.join("\n") + "\n";
  }

  // =====================================================================
  // LVGL .bin serialization (bpp=1, raw, no kerning) — byte-exact port
  // =====================================================================
  function lvBinFromGlyphs(font, opts = {}) {
    const bpp = opts.bpp || 1;
    const glyphs = [...font.glyphs].sort((a, b) => a.code - b.code);
    // ---- font-level derived metrics ----
    const ys = glyphs.map(g => g.bbox.y);
    const yhs = glyphs.map(g => g.bbox.y + g.bbox.height);
    const ascent = Math.max(...yhs);
    const descent = Math.min(...ys);
    const minY = descent, maxY = ascent;
    const size = font.meta.size || (ascent - descent);
    const typoAscent = (font.meta.typoAscent != null) ? font.meta.typoAscent : ascent;
    const typoDescent = (font.meta.typoDescent != null) ? font.meta.typoDescent : descent;
    const typoLineGap = font.meta.typoLineGap || 0;

    // ids: 1..N in sorted order (0 reserved)
    const idByCode = new Map();
    glyphs.forEach((g, k) => idByCode.set(g.code, k + 1));
    const lastId = glyphs.length + 1;

    const xy_bits = Math.max(...glyphs.map(g => Math.max(signed_bits(g.bbox.x), signed_bits(g.bbox.y))));
    const wh_bits = Math.max(...glyphs.map(g => Math.max(unsigned_bits(g.bbox.width), unsigned_bits(g.bbox.height))));
    const monospaced = glyphs.every(g => g.advanceWidth === glyphs[0].advanceWidth);
    const advanceWidthBits = Math.max(...glyphs.map(g => signed_bits(Math.round(g.advanceWidth))));

    // ---- glyf: per-glyph byte-aligned blobs (index 0 reserved/empty) ----
    const glyfBlobs = [[]];
    for (const g of glyphs) {
      const bs = new BitW();
      if (!monospaced) bs.writeBits(Math.round(g.advanceWidth), advanceWidthBits);
      bs.writeBits(g.bbox.x, xy_bits);
      bs.writeBits(g.bbox.y, xy_bits);
      bs.writeBits(g.bbox.width, wh_bits);
      bs.writeBits(g.bbox.height, wh_bits);
      const onVal = (1 << bpp) - 1;   // bpp=1 -> 1, fully-on pixel
      for (let r = 0; r < g.bbox.height; r++)
        for (let c = 0; c < g.bbox.width; c++)
          bs.writeBits((g.pixels[r] && g.pixels[r][c]) ? onVal : 0, bpp);
      glyfBlobs.push(bs.finish());
    }
    const GLYF_HEAD = 8;
    const glyfOffset = (id) => { let o = GLYF_HEAD; for (let k = 0; k < id; k++) o += glyfBlobs[k].length; return o; };
    const glyfTotal = glyfBlobs.reduce((s, b) => s + b.length, GLYF_HEAD);
    const indexToLocFormat = align4(glyfTotal) > 65535 ? 1 : 0;
    const glyphIdFormat = (lastId - 1) > 255 ? 1 : 0;

    // ---- head ----
    const head = [];
    u32(head, 0); tag(head, "head"); u32(head, 1);          // size(patch later), label, version
    const tablesCount = 3;                                  // cmap, loca, glyf (no kern)
    u16(head, tablesCount);
    u16(head, size);
    u16(head, ascent); i16(head, descent);
    u16(head, typoAscent); i16(head, typoDescent); u16(head, typoLineGap);
    i16(head, minY); i16(head, maxY);
    u16(head, monospaced ? Math.round(glyphs[0].advanceWidth) : 0);  // default_advance_width
    u16(head, 16);                                          // kerning scale FP12.4 = 1.0
    u8(head, indexToLocFormat); u8(head, glyphIdFormat); u8(head, 0); // advanceWidthFormat=0 (no kern)
    u8(head, bpp); u8(head, xy_bits); u8(head, wh_bits);
    u8(head, monospaced ? 0 : advanceWidthBits);
    u8(head, 0);   // compression id (bpp1 -> 0)
    u8(head, 0);   // subpixels mode
    u8(head, 0);   // reserved1
    i16(head, 0);  // underline position  (lv_font_conv overwrites this with thickness)
    u16(head, 0);  // underline thickness
    pad4(head);
    writeLenAt(head, 0);

    // ---- cmap ----
    const cmap = buildCmap(glyphs, idByCode);

    // ---- loca ----
    const loca = [];
    u32(loca, 0); tag(loca, "loca"); u32(loca, lastId);
    for (let id = 0; id < lastId; id++) {
      if (indexToLocFormat) u32(loca, glyfOffset(id)); else u16(loca, glyfOffset(id));
    }
    pad4(loca); writeLenAt(loca, 0);

    // ---- glyf ----
    const glyf = [];
    u32(glyf, 0); tag(glyf, "glyf");
    for (const b of glyfBlobs) for (const byte of b) glyf.push(byte);
    pad4(glyf); writeLenAt(glyf, 0);

    return Uint8Array.from([...head, ...cmap, ...loca, ...glyf]);
  }

  function writeLenAt(arr, off) {
    const n = arr.length;
    arr[off] = n & 0xff; arr[off + 1] = (n >>> 8) & 0xff;
    arr[off + 2] = (n >>> 16) & 0xff; arr[off + 3] = (n >>> 24) & 0xff;
  }

  // cmap: replicate lv_font_conv subtable planner + 4 formats
  function buildCmap(glyphs, idByCode) {
    const codes = glyphs.map(g => g.code).sort((a, b) => a - b);
    const plan = planSubtables(codes);
    const CMAP_HEAD = 12;
    const subHeads = [], subData = [];
    for (const [format, cps] of plan) {
      const startId = idByCode.get(cps[0]);
      const minc = cps[0], maxc = cps[cps.length - 1];
      let total, type, data = [];
      if (format === "format0_tiny") {
        type = 2; total = maxc - minc + 1; // data empty
      } else if (format === "format0") {
        type = 0; total = maxc - minc + 1;
        const have = new Map(glyphs.map(g => [g.code, idByCode.get(g.code)]));
        for (let c = minc; c <= maxc; c++) data.push(have.has(c) ? have.get(c) - startId : 0);
        while (data.length % 4) data.push(0);
      } else if (format === "sparse_tiny") {
        type = 3; total = cps.length;
        for (const c of cps) u16(data, c - minc);
        while (data.length % 4) data.push(0);
      } else { // sparse
        type = 1; total = cps.length;
        for (const c of cps) u16(data, c - minc);
        for (const c of cps) u16(data, idByCode.get(c) - startId);
        while (data.length % 4) data.push(0);
      }
      const h = [];
      u32(h, 0);                 // offset, patched below
      u32(h, minc);
      u16(h, maxc - minc + 1);
      u16(h, startId);
      u16(h, total);
      u8(h, type); u8(h, 0);
      subHeads.push(h); subData.push(data);
    }
    // patch offsets (relative to cmap table start)
    const headsLen = subHeads.reduce((s, h) => s + h.length, 0);
    let acc = 0;
    for (let i = 0; i < subHeads.length; i++) {
      const off = CMAP_HEAD + headsLen + acc;
      writeLenAt(subHeads[i], 0); // ensure 4 bytes exist
      subHeads[i][0] = off & 0xff; subHeads[i][1] = (off >>> 8) & 0xff;
      subHeads[i][2] = (off >>> 16) & 0xff; subHeads[i][3] = (off >>> 24) & 0xff;
      acc += subData[i].length;
    }
    const out = [];
    u32(out, 0); tag(out, "cmap"); u32(out, subHeads.length);
    for (const h of subHeads) out.push(...h);
    for (const d of subData) out.push(...d);
    writeLenAt(out, 0);
    return out;
  }

  // breadth-first subtable planner (ported)
  function planSubtables(all) {
    all = [...all].sort((a, b) => a - b);
    const f0 = (a, b) => 16 + (b - a + 1);
    const f0t = () => 16;
    const st = (n) => 16 + n * 2;
    const min_paths = [];
    for (let i = 0; i < all.length; i++) {
      let min = { dist: Infinity };
      for (let j = 0; j <= i; j++) {
        const prev = j - 1 >= 0 ? min_paths[j - 1].dist : 0;
        let s;
        if (all[i] - all[j] < 256) {
          s = f0(all[j], all[i]);
          if (prev + s < min.dist) min = { dist: prev + s, start: j, end: i, format: "format0" };
        }
        if (all[i] - all[j] < 256 && all[i] - i === all[j] - j) {
          s = f0t();
          if (prev + s < min.dist) min = { dist: prev + s, start: j, end: i, format: "format0_tiny" };
        }
        if (all[i] - all[j] < 65536) {
          s = st(i - j + 1);
          if (prev + s < min.dist) min = { dist: prev + s, start: j, end: i, format: "sparse_tiny" };
        }
      }
      min_paths[i] = min;
    }
    const result = [];
    for (let i = all.length - 1; i >= 0;) {
      const p = min_paths[i];
      result.unshift([p.format, all.slice(p.start, p.end + 1)]);
      i = p.start - 1;
    }
    return result;
  }

  // =====================================================================
  // LVGL .bin parsing (importer) — inverse of lvBinFromGlyphs
  // =====================================================================
  function parseLvBin(arrayBuffer) {
    const dv = new DataView(arrayBuffer instanceof ArrayBuffer ? arrayBuffer : arrayBuffer.buffer);
    const bytes = new Uint8Array(dv.buffer);
    // walk top-level tables
    const tabs = {};
    let p = 0;
    while (p < bytes.length) {
      const size = dv.getUint32(p, true);
      const label = String.fromCharCode(bytes[p + 4], bytes[p + 5], bytes[p + 6], bytes[p + 7]);
      tabs[label] = { off: p, size };
      if (!size) break;
      p += size;
    }
    if (!tabs.head || !tabs.cmap || !tabs.loca || !tabs.glyf) throw new Error("not an LVGL font .bin");
    const h = tabs.head.off;
    const meta = {
      name: "", size: dv.getUint16(h + 14, true),
      ascent: dv.getUint16(h + 16, true), descent: dv.getInt16(h + 18, true),
      typoAscent: dv.getInt16(h + 20, true), typoDescent: dv.getInt16(h + 22, true),
      typoLineGap: dv.getUint16(h + 24, true), defaultChar: 32, props: {},
    };
    const defAdvance = dv.getUint16(h + 30, true);
    const indexToLoc = bytes[h + 34], awFormat = bytes[h + 36], bpp = bytes[h + 37];
    const xy = bytes[h + 38], wh = bytes[h + 39], awBits = bytes[h + 40], compression = bytes[h + 41];
    if (compression !== 0) throw new Error("compressed fonts not supported by importer (use --no-compress / bpp 1)");

    // loca offsets
    const l = tabs.loca.off, count = dv.getUint32(l + 8, true), offs = [];
    for (let i = 0; i < count; i++) offs.push(indexToLoc ? dv.getUint32(l + 12 + i * 4, true) : dv.getUint16(l + 12 + i * 2, true));

    // cmap: build id -> code
    const codeById = new Map();
    const cm = tabs.cmap.off, subCount = dv.getUint32(cm + 8, true);
    for (let s = 0; s < subCount; s++) {
      const sh = cm + 12 + s * 16;
      const dataOff = cm + dv.getUint32(sh, true);
      const rangeStart = dv.getUint32(sh + 4, true);
      const rangeLen = dv.getUint16(sh + 8, true);
      const gidOff = dv.getUint16(sh + 10, true);
      const total = dv.getUint16(sh + 12, true);
      const type = bytes[sh + 14];
      if (type === 2) {                       // format0_tiny
        for (let i = 0; i < rangeLen; i++) codeById.set(gidOff + i, rangeStart + i);
      } else if (type === 0) {                // format0
        for (let i = 0; i < rangeLen; i++) { const d = bytes[dataOff + i]; if (d || i === 0) codeById.set(gidOff + d, rangeStart + i); }
      } else if (type === 3) {                // sparse_tiny
        for (let i = 0; i < total; i++) codeById.set(gidOff + i, rangeStart + dv.getUint16(dataOff + i * 2, true));
      } else if (type === 1) {                // sparse
        for (let i = 0; i < total; i++) { const cd = dv.getUint16(dataOff + i * 2, true); const idd = dv.getUint16(dataOff + total * 2 + i * 2, true); codeById.set(gidOff + idd, rangeStart + cd); }
      }
    }

    // decode glyph blobs
    const g0 = tabs.glyf.off;
    function readGlyph(off, code) {
      let bp = (g0 + off) * 8;
      const rd = (n) => { let v = 0; for (let i = 0; i < n; i++) { v = (v << 1) | ((bytes[bp >> 3] >> (7 - (bp & 7))) & 1); bp++; } return v; };
      const rds = (n) => { let v = rd(n); if (v >= (1 << (n - 1))) v -= (1 << n); return v; };
      // advanceWidthFormat 1 = FP4 fixed-point (lv_font_conv with kerning); snap to whole pixels
      const rawAdvance = awBits ? rds(awBits) : defAdvance;
      const advanceWidth = awFormat === 1 ? Math.round(rawAdvance / 16) : rawAdvance;
      const x = rds(xy), y = rds(xy), w = rd(wh), hh = rd(wh);
      const pixels = [];
      for (let r = 0; r < hh; r++) { const row = []; for (let c = 0; c < w; c++) row.push(rd(bpp) ? 1 : 0); pixels.push(row); }
      return { code, name: "U+" + code.toString(16).toUpperCase().padStart(4, "0"), advanceWidth, bbox: { x, y, width: w, height: hh }, pixels };
    }
    const glyphs = [];
    for (let id = 1; id < count; id++) { const code = codeById.get(id); if (code == null) continue; glyphs.push(readGlyph(offs[id], code)); }
    glyphs.sort((a, b) => a.code - b.code);
    return { meta, glyphs };
  }

  const API = { parseBDF, serializeBDF, lvBinFromGlyphs, parseLvBin, signed_bits, unsigned_bits, align4 };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.FontCodec = API;
})(typeof window !== "undefined" ? window : globalThis);

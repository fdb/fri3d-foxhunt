# art_fast.py — viper-accelerated pixel replication for the sprite atlas.
#
# The badge's firmware has the native emitter, the desktop build does not:
# importing this module there raises SyntaxError, and art.py catches it and
# keeps its pure-Python loop. Same bytes out either way — one BGRA source
# pixel becomes an exact scale x scale block.

import micropython


@micropython.viper
def _blit(src: ptr32, dst: ptr32, scale: int):
    # 16x16 BGRA frame: 256 dwords in, 256*scale*scale dwords out.
    drow = 16 * scale
    for y in range(16):
        so = y << 4
        do = y * scale * drow
        # write the first destination row of this source row
        for x in range(16):
            px = src[so + x]
            b = do + x * scale
            for i in range(scale):
                dst[b + i] = px
        # replicate it scale-1 times
        rd = do
        for _ in range(scale - 1):
            rd += drow
            for i in range(drow):
                dst[rd + i] = dst[do + i]


def upscale(src, scale):
    out = bytearray(1024 * scale * scale)
    _blit(src, out, scale)
    return out

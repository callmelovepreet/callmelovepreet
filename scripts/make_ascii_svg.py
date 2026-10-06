"""Convert source-prepped.png into a self-typing monochrome ASCII SVG.

Each row is revealed by a left-to-right clip wipe with a block cursor riding
its edge, staggered top to bottom. It prints once and freezes.

    python scripts/make_ascii_svg.py          # writes lovepreet-ascii.svg
    STATIC=1 python scripts/make_ascii_svg.py # frozen frame for previews
"""

import os
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "lovepreet-ascii.svg"

# Light text on a dark terminal, so a denser glyph means a brighter pixel.
RAMP = " .`:-=+*cs#%@"  # sparse -> dense
COLS = 84
CROP_TOP = 0.0  # fraction of the image height to keep, from the top
CROP_BOTTOM = 0.5  # upper body reads better than a full-length shot
FONT_SIZE = 8
CHAR_W = FONT_SIZE * 0.6
LINE_H = FONT_SIZE * 1.12
PAD = 18
FILL = "#c9d1d9"
BG = "#0d1117"
BORDER = "#30363d"
ROW_DELAY = 0.04  # seconds between rows starting
ROW_DUR = 0.35  # seconds for one row to wipe across
NBSP = "\u00a0"
STATIC = os.environ.get("STATIC") == "1"


def to_ascii() -> list[str]:
    img = Image.open(SRC).convert("LA")
    w, h = img.size
    img = img.crop((0, int(h * CROP_TOP), w, int(h * CROP_BOTTOM)))
    w, h = img.size
    # Terminal cells are about twice as tall as they are wide.
    rows = max(1, round(COLS * (h / w) * (CHAR_W / LINE_H)))
    small = np.array(img.resize((COLS, rows), Image.LANCZOS), dtype=np.float32)
    gray, alpha = small[:, :, 0] / 255.0, small[:, :, 1] / 255.0
    # Stretch the subject's tones to the full ramp.
    subject = gray[alpha >= 0.5]
    if subject.size:
        lo, hi = np.percentile(subject, [3, 97])
        gray = np.clip((gray - lo) / max(hi - lo, 1e-6), 0.0, 1.0)

    lines = []
    for y in range(rows):
        chars = []
        for x in range(COLS):
            if alpha[y, x] < 0.5:
                chars.append(" ")
                continue
            # Subject pixels always get at least the lightest visible glyph.
            idx = 1 + int(gray[y, x] * (len(RAMP) - 2) + 0.5)
            chars.append(RAMP[min(idx, len(RAMP) - 1)])
        lines.append("".join(chars).rstrip())
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def build_svg(lines: list[str]) -> str:
    width = PAD * 2 + COLS * CHAR_W
    height = PAD * 2 + len(lines) * LINE_H
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        f'<rect x="0.5" y="0.5" width="{width - 1:.0f}" height="{height - 1:.0f}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        "<defs>",
    ]
    row_w = COLS * CHAR_W
    for i, line in enumerate(lines):
        if not line or STATIC:
            continue
        y = PAD + i * LINE_H
        begin = i * ROW_DELAY
        out.append(
            f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" width="0" height="{LINE_H:.1f}">'
            f'<animate attributeName="width" from="0" to="{row_w:.1f}" begin="{begin:.2f}s" '
            f'dur="{ROW_DUR}s" fill="freeze"/></rect></clipPath>'
        )
    out.append("</defs>")
    out.append(
        f'<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
        f'font-size="{FONT_SIZE}" fill="{FILL}">'
    )
    for i, line in enumerate(lines):
        if not line:
            continue
        y = PAD + i * LINE_H + FONT_SIZE * 0.85
        text_len = len(line) * CHAR_W
        # Renderers collapse leading whitespace, so offset x instead and keep
        # inner gaps with non-breaking spaces.
        body = line.lstrip(" ")
        x = PAD + (len(line) - len(body)) * CHAR_W
        body_len = len(body) * CHAR_W
        clip = "" if STATIC else f' clip-path="url(#r{i})"'
        out.append(
            f'<text x="{x:.1f}" y="{y:.1f}" textLength="{body_len:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{clip}>{escape(body).replace(" ", NBSP)}</text>'
        )
        if not STATIC:
            begin = i * ROW_DELAY
            travel = ROW_DUR * text_len / row_w
            cy = PAD + i * LINE_H
            out.append(
                f'<rect x="{PAD}" y="{cy:.1f}" width="{CHAR_W:.1f}" height="{LINE_H:.1f}" '
                f'fill="{FILL}" opacity="0">'
                f'<set attributeName="opacity" to="0.85" begin="{begin:.2f}s"/>'
                f'<animate attributeName="x" from="{PAD}" to="{PAD + text_len:.1f}" '
                f'begin="{begin:.2f}s" dur="{travel:.2f}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0" begin="{begin + travel:.2f}s"/>'
                f"</rect>"
            )
    out.append("</g></svg>")
    return "\n".join(out)


def main() -> None:
    lines = to_ascii()
    OUT.write_text(build_svg(lines) + "\n")
    print(f"wrote {OUT.name} ({COLS}x{len(lines)})")


if __name__ == "__main__":
    main()

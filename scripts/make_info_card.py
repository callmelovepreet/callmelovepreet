"""Render data/profile_info.json as a neofetch-style info card SVG.

Each line fades and slides in on a short stagger, so the panel looks like it
is printing next to the portrait.

    python scripts/make_info_card.py          # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py # frozen frame for previews
"""

import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "profile_info.json"
OUT = ROOT / "info-card.svg"

WIDTH = 520
PAD_X = 24
TITLE_BAR = 34
TOP = TITLE_BAR + 22
LINE_H = 21
GAP_H = 12
FONT_SIZE = 13.5
KEY_COL = 112  # x offset of the value column from PAD_X
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

BG = "#0d1117"
BAR = "#161b22"
BORDER = "#30363d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
KEY = "#39d353"
ACCENT = "#58a6ff"
SECTION = "#d2a8ff"
PALETTE = ["#0d1117", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0", "#58a6ff", "#d2a8ff"]

START = 0.6  # seconds before the first line prints
STEP = 0.11  # seconds between lines
STATIC = os.environ.get("STATIC") == "1"


def line_group(y: float, index: int, body: str) -> str:
    if STATIC:
        return f"<g>{body}</g>"
    begin = START + index * STEP
    return (
        f'<g opacity="0" transform="translate(-8 0)">'
        f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.2f}s" dur="0.3s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="-8 0" to="0 0" '
        f'begin="{begin:.2f}s" dur="0.3s" fill="freeze"/>'
        f"{body}</g>"
    )


def main() -> None:
    info = json.loads(SRC.read_text())
    user, host = info["user"], info["host"]

    body, y, index = [], TOP, 0
    for row in info["rows"]:
        kind = row["type"]
        if kind == "gap":
            y += GAP_H
            continue
        baseline = y + FONT_SIZE
        if kind == "header":
            text = (
                f'<text x="{PAD_X}" y="{baseline}"><tspan fill="{KEY}" font-weight="700">{escape(user)}</tspan>'
                f'<tspan fill="{TEXT}">@</tspan><tspan fill="{KEY}" font-weight="700">{escape(host)}</tspan></text>'
            )
        elif kind == "divider":
            dashes = "-" * (len(user) + len(host) + 1)
            text = f'<text x="{PAD_X}" y="{baseline}" fill="{MUTED}">{dashes}</text>'
        elif kind == "section":
            text = (
                f'<text x="{PAD_X}" y="{baseline}" fill="{SECTION}" font-weight="700">'
                f'{escape(row["title"])}</text>'
            )
        elif kind == "kv":
            text = (
                f'<text x="{PAD_X}" y="{baseline}" fill="{KEY}" font-weight="700">{escape(row["key"])}</text>'
                f'<text x="{PAD_X + KEY_COL}" y="{baseline}" fill="{TEXT}">{escape(row["value"])}</text>'
            )
        elif kind == "palette":
            size = 18
            text = "".join(
                f'<rect x="{PAD_X + i * (size + 4)}" y="{y + 2}" width="{size}" height="{size - 4}" '
                f'rx="3" fill="{c}" stroke="{BORDER}"/>'
                for i, c in enumerate(PALETTE)
            )
        else:
            raise ValueError(f"unknown row type: {kind}")
        body.append(line_group(y, index, text))
        y += LINE_H
        index += 1

    height = y + 18
    cursor_y = height - 18 - LINE_H + 3
    blink = "" if STATIC else (
        f'<animate attributeName="opacity" values="0;0;1;0" keyTimes="0;0.01;0.5;1" '
        f'begin="{START + index * STEP:.2f}s" dur="1.1s" repeatCount="indefinite"/>'
    )

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<path d="M0.5 10.5a10 10 0 0 1 10-10h{WIDTH - 21}a10 10 0 0 1 10 10v{TITLE_BAR - 10}h-{WIDTH - 1}z" '
        f'fill="{BAR}" stroke="{BORDER}"/>',
        '<circle cx="20" cy="17" r="6" fill="#ff5f56"/>',
        '<circle cx="40" cy="17" r="6" fill="#ffbd2e"/>',
        '<circle cx="60" cy="17" r="6" fill="#27c93f"/>',
        f'<text x="{WIDTH / 2}" y="22" text-anchor="middle" font-family="{FONT}" font-size="12" '
        f'fill="{MUTED}">{escape(user)}@{escape(host)}: ~ neofetch</text>',
        f'<g font-family="{FONT}" font-size="{FONT_SIZE}">',
        *body,
        f'<rect x="{PAD_X + 8 * 22 + 6}" y="{cursor_y}" width="9" height="16" fill="{ACCENT}" '
        f'opacity="{1 if STATIC else 0}">{blink}</rect>',
        "</g></svg>",
    ]
    OUT.write_text("\n".join(svg) + "\n")
    print(f"wrote {OUT.name} ({WIDTH}x{height})")


if __name__ == "__main__":
    main()

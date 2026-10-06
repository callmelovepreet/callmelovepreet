"""Render data/contributions.json as an animated 53-week heatmap SVG.

Boxes drop in along a diagonal once on load, then freeze. A Less -> More
legend and a stats footer sit underneath.

    python scripts/render_heatmap_svg.py          # writes contrib-heatmap.svg
    STATIC=1 python scripts/render_heatmap_svg.py # frozen frame for previews
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
#          none -> brightest (level 5 is a neon top end)
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

WEEKS = 53
CELL = 13
GAP = 3
STEP = CELL + GAP
LEFT = 52  # room for weekday labels
TOP = 46  # room for the header and month labels
PAD = 20
DELAY = 0.012  # seconds per diagonal step
START = 0.3  # let the image settle before the first box drops
STATIC = os.environ.get("STATIC") == "1"


def load() -> dict:
    if SRC.exists():
        return json.loads(SRC.read_text())
    # No data yet: draw an empty year so the README never shows a broken image.
    today = date.today()
    days = [
        {"date": (today - timedelta(days=i)).isoformat(), "count": 0}
        for i in range(WEEKS * 7 - 1, -1, -1)
    ]
    return {"days": days, "total": 0, "current_streak": 0, "longest_streak": 0,
            "best_day": {"date": today.isoformat(), "count": 0}}


def levels(counts: list[int]) -> list[int]:
    """Bucket counts into 0..5 using quantiles of the non-zero days."""
    nonzero = sorted(c for c in counts if c)
    if not nonzero:
        return [0] * len(counts)

    def q(p: float) -> int:
        return nonzero[min(len(nonzero) - 1, int(p * len(nonzero)))]

    cuts = [q(0.25), q(0.5), q(0.75), q(0.95)]
    out = []
    for c in counts:
        if not c:
            out.append(0)
        else:
            out.append(1 + sum(c > cut for cut in cuts))
    return out


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def main() -> None:
    data = load()
    days = data["days"]
    by_date = {d["date"]: d["count"] for d in days}
    last = date.fromisoformat(days[-1]["date"])
    # Columns run Sunday..Saturday; the last column holds the latest week.
    first = last - timedelta(days=(last.weekday() + 1) % 7 + (WEEKS - 1) * 7)
    grid = [first + timedelta(days=i) for i in range(WEEKS * 7) if first + timedelta(days=i) <= last]
    lv = levels([by_date.get(d.isoformat(), 0) for d in grid])

    width = LEFT + WEEKS * STEP - GAP + PAD
    grid_bottom = TOP + 7 * STEP - GAP
    height = grid_bottom + 66

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        f"text{{font-family:{FONT};}}",
        ".c{rx:3px;ry:3px;}",
    ]
    if not STATIC:
        out += [
            "@keyframes drop{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}",
            "@keyframes fade{from{opacity:0}to{opacity:1}}",
            ".c{opacity:0;animation:drop .45s cubic-bezier(.2,.8,.3,1) forwards;transform-box:fill-box;}",
            ".f{opacity:0;animation:fade .6s ease-out forwards;}",
        ]
    out += [
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
    ]

    # Month labels above the first column that starts a new month.
    seen = None
    for w in range(WEEKS):
        d = first + timedelta(days=w * 7)
        if d > last:
            break
        if d.month != seen and (w < WEEKS - 2):
            if seen is not None or d.day <= 7:
                out.append(
                    f'<text x="{LEFT + w * STEP}" y="{TOP - 10}" font-size="11" fill="{MUTED}">'
                    f'{d.strftime("%b")}</text>'
                )
            seen = d.month
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(
            f'<text x="{PAD}" y="{TOP + row * STEP + CELL - 2}" font-size="11" fill="{MUTED}">{name}</text>'
        )

    for i, (d, level) in enumerate(zip(grid, lv)):
        w, row = divmod(i, 7)
        style = "" if STATIC else f' style="animation-delay:{START + (w + row) * DELAY:.3f}s"'
        count = by_date.get(d.isoformat(), 0)
        noun = "contribution" if count == 1 else "contributions"
        out.append(
            f'<rect class="c" x="{LEFT + w * STEP}" y="{TOP + row * STEP}" width="{CELL}" height="{CELL}" '
            f'fill="{PALETTE[level]}"{style}><title>{count} {noun} on {d.strftime("%b")} '
            f"{ordinal(d.day)}</title></rect>"
        )

    # Footer: stats on the left, legend on the right.
    finish = START + (WEEKS + 7) * DELAY + 0.3
    fstyle = "" if STATIC else f' class="f" style="animation-delay:{finish:.2f}s"'
    best = data["best_day"]
    best_label = date.fromisoformat(best["date"]).strftime("%b %d").replace(" 0", " ")
    stats = (
        f'<tspan fill="{TEXT}" font-weight="700">{data["total"]:,}</tspan> contributions in the last year'
        f'  ·  current streak <tspan fill="{TEXT}">{data["current_streak"]}d</tspan>'
        f'  ·  longest <tspan fill="{TEXT}">{data["longest_streak"]}d</tspan>'
        f'  ·  best day <tspan fill="{TEXT}">{best["count"]}</tspan> ({best_label})'
    )
    fy = grid_bottom + 34
    out.append(f"<g{fstyle}>")
    out.append(f'<text x="{LEFT}" y="{fy}" font-size="12" fill="{MUTED}">{stats}</text>')
    lx = width - PAD - len(PALETTE) * (CELL + 3) - 34
    out.append(f'<text x="{lx - 34}" y="{fy}" font-size="11" fill="{MUTED}">Less</text>')
    for i, color in enumerate(PALETTE):
        out.append(
            f'<rect x="{lx + i * (CELL + 3)}" y="{fy - CELL + 2}" width="{CELL}" height="{CELL}" '
            f'rx="3" fill="{color}"/>'
        )
    out.append(
        f'<text x="{lx + len(PALETTE) * (CELL + 3) + 4}" y="{fy}" font-size="11" fill="{MUTED}">More</text>'
    )
    out.append("</g></svg>")

    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT.name} ({width}x{height}, {len(grid)} days)")


if __name__ == "__main__":
    main()

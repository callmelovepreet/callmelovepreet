"""Render data/contributions.json as an animated 3D skyline SVG.

Every day is a building as tall as the square root of its count, drawn as a
front, a lit top and a shaded side in an oblique projection. Buildings rise in
a wave from the front row to the back, then a leader line points at the best day.

    python scripts/render_skyline_svg.py          # writes contrib-skyline.svg
    STATIC=1 python scripts/render_skyline_svg.py # frozen frame for previews
"""

from datetime import date, timedelta
from pathlib import Path

from render_heatmap_svg import BG, BORDER, FONT, MUTED, PALETTE, STATIC, TEXT, WEEKS, levels, load

OUT = Path(__file__).resolve().parent.parent / "contrib-skyline.svg"

CELL = 12  # front face width
STEP = 15  # column spacing
DX, DY = 9, 7  # how far each row further back shifts right and up
SX, SY = 7, 5.5  # depth of one building (top/side offset)
MAXH = 110  # height of the busiest day
PAD = 20
TOP = 40  # room for the best-day label
DELAY = 0.012  # seconds per wave step
START = 0.3


def shade(color: str, f: float) -> str:
    """Mix toward white (f > 0) or black (f < 0)."""
    rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    target = 255 if f > 0 else 0
    return "#" + "".join(f"{round(c + (target - c) * abs(f)):02x}" for c in rgb)


def main() -> None:
    data = load()
    by_date = {d["date"]: d["count"] for d in data["days"]}
    last = date.fromisoformat(data["days"][-1]["date"])
    # Same Sunday-first, 53-column layout as the heatmap.
    first = last - timedelta(days=(last.weekday() + 1) % 7 + (WEEKS - 1) * 7)
    grid = [first + timedelta(days=i) for i in range(WEEKS * 7) if first + timedelta(days=i) <= last]
    counts = [by_date.get(d.isoformat(), 0) for d in grid]
    lv = levels(counts)
    peak = max(counts) or 1

    width = PAD * 2 + (WEEKS - 1) * STEP + CELL + 6 * DX + SX
    ground = TOP + MAXH + 6 * DY + SY  # bottom of the front row
    height = ground + 34

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" viewBox="0 0 {width} {height:.0f}">',
        "<style>",
        f"text{{font-family:{FONT};}}",
    ]
    if not STATIC:
        out += [
            "@keyframes rise{from{transform:scaleY(0)}to{transform:scaleY(1)}}",
            "@keyframes fade{from{opacity:0}to{opacity:1}}",
            ".b{transform:scaleY(0);transform-box:fill-box;transform-origin:50% 100%;"
            "animation:rise .6s cubic-bezier(.2,.8,.3,1.15) forwards;}",
            ".f{opacity:0;animation:fade .6s ease-out forwards;}",
        ]
    out += [
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1:.0f}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
    ]

    best_i = counts.index(max(counts))
    best_top = None
    # Painter's order: back row (Sunday) first, left to right within a row.
    for row in range(7):
        k = 6 - row  # depth: 0 is the front row
        for w in range(WEEKS):
            i = w * 7 + row
            if i >= len(grid):
                continue
            x, y = PAD + w * STEP + k * DX, ground - k * DY
            h = MAXH * (counts[i] / peak) ** 0.5
            color = PALETTE[lv[i]]
            top = (f'<polygon points="{x},{y - h:.1f} {x + SX},{y - h - SY:.1f} {x + CELL + SX},{y - h - SY:.1f} '
                   f'{x + CELL},{y - h:.1f}" fill="{shade(color, 0.25 if h else 0)}"/>')
            if not h:
                out.append(top)  # empty day: just a ground tile
                continue
            style = "" if STATIC else f' class="b" style="animation-delay:{START + (w + k * 3) * DELAY:.3f}s"'
            out.append(
                f"<g{style}>"
                f'<rect x="{x}" y="{y - h:.1f}" width="{CELL}" height="{h:.1f}" fill="{color}"/>'
                f'<polygon points="{x + CELL},{y - h:.1f} {x + CELL + SX},{y - h - SY:.1f} '
                f'{x + CELL + SX},{y - SY:.1f} {x + CELL},{y}" fill="{shade(color, -0.35)}"/>'
                f"{top}</g>"
            )
            if i == best_i:
                best_top = (x + CELL / 2 + SX / 2, y - h - SY / 2)

    # Month labels along the front edge, under the first week of each month.
    seen = None
    for w in range(WEEKS - 2):
        d = first + timedelta(days=w * 7)
        if d.month != seen:
            if seen is not None or d.day <= 7:
                out.append(f'<text x="{PAD + w * STEP}" y="{ground + 20:.0f}" font-size="11" fill="{MUTED}">'
                           f'{d.strftime("%b")}</text>')
            seen = d.month

    if best_top:
        finish = START + (WEEKS + 18) * DELAY + 0.4
        fstyle = "" if STATIC else f' class="f" style="animation-delay:{finish:.2f}s"'
        bx, by = best_top
        ly = TOP - 14
        anchor = "end" if bx > width / 2 else "start"
        tx = bx - 6 if anchor == "end" else bx + 6
        label = grid[best_i].strftime("%b %d").replace(" 0", " ")
        out += [
            f"<g{fstyle}>",
            f'<line x1="{bx:.1f}" y1="{by - 4:.1f}" x2="{bx:.1f}" y2="{ly + 4}" stroke="{MUTED}" stroke-dasharray="2 3"/>',
            f'<circle cx="{bx:.1f}" cy="{by - 4:.1f}" r="2" fill="{TEXT}"/>',
            f'<text x="{tx:.1f}" y="{ly + 8}" font-size="12" fill="{MUTED}" text-anchor="{anchor}">best day '
            f'<tspan fill="{TEXT}" font-weight="700">{max(counts)}</tspan> ({label})</text>',
            "</g>",
        ]
    out.append("</svg>")

    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT.name} ({width}x{height:.0f}, {len(grid)} days)")


if __name__ == "__main__":
    main()

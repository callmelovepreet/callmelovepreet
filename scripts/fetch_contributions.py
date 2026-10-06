"""Scrape the public contribution calendar into data/contributions.json.

GitHub serves the calendar as public HTML at
https://github.com/users/<username>/contributions, the same fragment the
profile page uses, so no token or GraphQL call is needed.

    GITHUB_USER=callmelovepreet python scripts/fetch_contributions.py
    python scripts/fetch_contributions.py --html saved.html  # parse a local copy
"""

import argparse
import json
import os
import re
from collections import OrderedDict
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"
DEFAULT_USER = "callmelovepreet"
COUNT_RE = re.compile(r"([\d,]+)\s+contributions?")


def fetch_html(user: str) -> str:
    resp = requests.get(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": f"{user}-profile-readme"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}

    days = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        level = int(cell.get("data-level", 0))
        tip = tips.get(cell.get("id"), "")
        match = COUNT_RE.search(tip)
        if match:
            count = int(match.group(1).replace(",", ""))
        elif tip.lower().startswith("no contribution"):
            count = 0
        else:
            # No readable tooltip: fall back to the bucketed level.
            count = level
        days.append({"date": cell["data-date"], "count": count, "level": level})

    if not days:
        raise SystemExit("no contribution cells found; GitHub's markup may have changed")
    days.sort(key=lambda d: d["date"])
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        longest = max(longest, run)

    # The current streak may end yesterday if today has no activity yet.
    current, tail = 0, list(reversed(days))
    if tail and tail[0]["count"] == 0:
        tail = tail[1:]
    for d in tail:
        if not d["count"]:
            break
        current += 1
    return current, longest


def summarize(user: str, days: list[dict]) -> dict:
    current, longest = streaks(days)
    best = max(days, key=lambda d: d["count"])
    monthly: "OrderedDict[str, int]" = OrderedDict()
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]
    return {
        "user": user,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": sum(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"]),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
        "days": days,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, help="parse a saved HTML file instead of fetching")
    args = parser.parse_args()

    user = os.environ.get("GITHUB_USER", DEFAULT_USER)
    html = args.html.read_text() if args.html else fetch_html(user)
    data = summarize(user, parse_days(html))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(
        f"wrote {OUT.relative_to(ROOT)}: {data['total']} contributions, "
        f"{len(data['days'])} days, streak {data['current_streak']}/{data['longest_streak']}"
    )


if __name__ == "__main__":
    main()

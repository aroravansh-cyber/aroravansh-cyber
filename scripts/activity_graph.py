#!/usr/bin/env python3
"""Generate a GitHub contribution activity line graph as a standalone SVG.

Usage:
    GITHUB_TOKEN=... python scripts/activity_graph.py
    python scripts/activity_graph.py --demo      # fake data, for local testing
"""
import datetime as dt
import json
import math
import os
import random
import sys
import urllib.request

USER = os.environ.get("GH_USER", "aroravansh-cyber")
DAYS = 30
OUT = os.environ.get("OUT_FILE", "profile/activity-graph.svg")

BG = "#0A0A0A"
GRID = "#2A1111"
LINE = "#F97316"
AREA = "#EF4444"
TEXT = "#FCA5A5"
MUTED = "#9CA3AF"
POINT = "#FFFFFF"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=DAYS + 1)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": USER,
                "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data or not data.get("data", {}).get("user"):
        sys.exit(f"GitHub API error: {data}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = {}
    for week in weeks:
        for d in week["contributionDays"]:
            days[d["date"]] = d["contributionCount"]
    ordered = sorted(days.items())[-DAYS:]
    return [(dt.date.fromisoformat(k), v) for k, v in ordered]


def demo_days():
    random.seed(7)
    today = dt.date.today()
    return [(today - dt.timedelta(days=DAYS - 1 - i), random.randint(0, 9)) for i in range(DAYS)]


def nice_max(v):
    if v <= 5:
        return 5
    step = 5 if v <= 25 else 10
    return int(math.ceil(v / step) * step)


def build_svg(days):
    w, h = 900, 320
    ml, mr, mt, mb = 56, 28, 78, 44
    pw, ph = w - ml - mr, h - mt - mb
    counts = [c for _, c in days]
    total = sum(counts)
    ymax = nice_max(max(counts) if counts else 0)
    n = len(days)

    def x(i):
        return ml + (pw * i / (n - 1) if n > 1 else pw / 2)

    def y(v):
        return mt + ph - (ph * v / ymax)

    pts = [(x(i), y(c)) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{ml:.1f},{mt + ph:.1f} {line} {x(n - 1):.1f},{mt + ph:.1f}"

    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="Contribution activity, last {DAYS} days">'
    )
    out.append(
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{AREA}" stop-opacity="0.45"/>'
        f'<stop offset="100%" stop-color="{AREA}" stop-opacity="0"/></linearGradient></defs>'
    )
    out.append(f'<rect width="{w}" height="{h}" rx="12" fill="{BG}" stroke="#7F1D1D" stroke-width="1"/>')
    font = "font-family=\"'Segoe UI', Ubuntu, Arial, sans-serif\""
    out.append(f'<text x="{ml}" y="36" {font} font-size="20" font-weight="700" fill="{TEXT}">Contribution Activity</text>')
    out.append(
        f'<text x="{ml}" y="58" {font} font-size="13" fill="{MUTED}">'
        f'{total} contributions in the last {DAYS} days  |  @{USER}</text>'
    )

    for t in range(5):
        v = ymax * t / 4
        gy = y(v)
        out.append(f'<line x1="{ml}" y1="{gy:.1f}" x2="{w - mr}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(
            f'<text x="{ml - 10}" y="{gy + 4:.1f}" {font} font-size="11" fill="{MUTED}" text-anchor="end">{int(round(v))}</text>'
        )

    for i, (d, _) in enumerate(days):
        if i % 5 == 0 or i == n - 1:
            out.append(
                f'<text x="{x(i):.1f}" y="{h - 16}" {font} font-size="11" fill="{MUTED}" text-anchor="middle">'
                f'{d.strftime("%b")} {d.day}</text>'
            )

    out.append(f'<polygon points="{area}" fill="url(#g)"/>')
    out.append(
        f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for (px, py), (d, c) in zip(pts, days):
        out.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{POINT}" stroke="{LINE}" stroke-width="2">'
            f'<title>{d.isoformat()}: {c} contributions</title></circle>'
        )
    out.append("</svg>")
    return "\n".join(out)


def main():
    days = demo_days() if "--demo" in sys.argv else fetch_days()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_svg(days))
    print(f"Wrote {OUT} ({len(days)} days)")


if __name__ == "__main__":
    main()

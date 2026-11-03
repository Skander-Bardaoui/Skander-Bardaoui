#!/usr/bin/env python3
"""Render the contribution-field HUD strip from the public GitHub calendar."""

import argparse
import datetime as dt
import html
import os
import re
import time
import urllib.request

USER = os.environ.get("GITHUB_USER", "Skander-Bardaoui")
CALENDAR_URL = "https://github.com/users/{user}/contributions"

W, H = 860, 260
CELL, GAP = 10.0, 3.4
STEP = CELL + GAP
GRID_Y = 96.0
ROWS = 7
BEAM_DUR = 10.0

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

BG_TOP, BG_BOTTOM = "#041417", "#030C0E"
BORDER, DIVIDER = "#0E2E33", "#0E2E33"
ACCENT, TEAL, PALE = "#22D3EE", "#2DD4BF", "#A5F3FC"
TEXT, DIM, FAINT = "#E2E8F0", "#64748B", "#475569"
LEVELS = ["#081B28", "#0B2C45", "#0F4C75", "#1682B8", "#38BDF8"]
FUTURE = "#05131C"


def fetch_calendar(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; profile-contribution-signal/1.0)",
            "Accept": "text/html",
        },
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - retry transient network failures
            last_error = exc
            time.sleep(2 + attempt * 2)
    raise SystemExit(f"unable to fetch contribution calendar: {last_error}")


def parse_calendar(page):
    tips = {}
    for match in re.finditer(
        r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page
    ):
        tips[match.group(1)] = match.group(2)

    days = {}
    for match in re.finditer(r"<td\b[^>]*>", page):
        tag = match.group(0)
        date_match = re.search(r'data-date="([0-9-]+)"', tag)
        level_match = re.search(r'data-level="([0-9])"', tag)
        id_match = re.search(r'\bid="([^"]+)"', tag)
        if not (date_match and level_match and id_match):
            continue
        count_match = re.search(
            r"([\d,]+)\s+contribution", tips.get(id_match.group(1), "")
        )
        count = int(count_match.group(1).replace(",", "")) if count_match else 0
        days[dt.date.fromisoformat(date_match.group(1))] = (
            int(level_match.group(1)),
            count,
        )

    if len(days) < 300:
        raise SystemExit(f"contribution calendar parse failed ({len(days)} days found)")
    return days


def streaks(days):
    best = run = 0
    previous = None
    for day in sorted(days):
        if days[day][1] > 0:
            run = run + 1 if previous == day - dt.timedelta(days=1) else 1
            best = max(best, run)
        else:
            run = 0
        previous = day
    return best


def build_svg(days):
    dates = sorted(days)
    first, last = dates[0], dates[-1]
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    columns = (last - start).days // 7 + 1
    grid_w = columns * CELL + (columns - 1) * GAP
    grid_h = ROWS * CELL + (ROWS - 1) * GAP
    grid_x = round((W - grid_w) / 2, 2)

    total = sum(count for _, count in days.values())
    active_days = sum(1 for _, count in days.values() if count > 0)
    peak = max(count for _, count in days.values())
    best_streak = streaks(days)
    window_days = (last - first).days + 1

    months = []
    for col in range(columns):
        week = [start + dt.timedelta(days=col * 7 + row) for row in range(ROWS)]
        if col == 0:
            months.append((col, MONTHS[first.month - 1]))
            continue
        for day in week:
            if day.day == 1:
                months.append((col, MONTHS[day.month - 1]))
                break

    sync_date = f"{last.day:02d} {MONTHS[last.month - 1]} {last.year}"
    title = "Contribution field — live 52-week scan"
    desc = (
        f"{total} contributions across {window_days} days, "
        f"{active_days} active days, best streak {best_streak} days, "
        f"peak {peak} contributions in a day."
    )

    out = []
    add = out.append
    add(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(desc)}">')
    add(f"<title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc>")
    add("<defs>")
    add(f'<linearGradient id="pbg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient>')
    add('<radialGradient id="pglow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        'gradientTransform="translate(80 240) rotate(-45) scale(380 380)">'
        f'<stop stop-color="{TEAL}" stop-opacity=".10"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/>'
        "</radialGradient>")
    add('<radialGradient id="pglow2" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        'gradientTransform="translate(790 30) rotate(135) scale(320 320)">'
        f'<stop stop-color="{ACCENT}" stop-opacity=".07"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>'
        "</radialGradient>")
    add('<pattern id="pmesh" width="40" height="40" patternUnits="userSpaceOnUse">'
        f'<path d="M40 0H0V40" stroke="#5EEAD4" stroke-opacity=".03"/></pattern>')
    add('<pattern id="pscan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#5EEAD4" opacity=".022"/></pattern>')
    add('<linearGradient id="beam" x1="0" y1="0" x2="96" y2="0" gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{ACCENT}" stop-opacity="0"/>'
        f'<stop offset=".55" stop-color="{ACCENT}" stop-opacity=".14"/>'
        f'<stop offset="1" stop-color="{PALE}" stop-opacity=".28"/></linearGradient>')
    add('<filter id="glow" x="-80%" y="-80%" width="260%" height="260%">'
        '<feGaussianBlur stdDeviation="2.6" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    add('<clipPath id="panelClip"><rect x=".5" y=".5" width="859" height="259" rx="18"/></clipPath>')
    add(f'<clipPath id="gridClip"><rect x="{grid_x - 2:.2f}" y="{GRID_Y - 2:.2f}" '
        f'width="{grid_w + 4:.2f}" height="{grid_h + 4:.2f}" rx="4"/></clipPath>')
    delays = "".join(
        f".f{col}{{animation-delay:{(col * STEP + 7) * BEAM_DUR / (grid_w + 98):.3f}s}}"
        for col in range(columns)
    )
    add(
        "<style>"
        ".beam{animation:sweep 10s linear infinite}"
        f"@keyframes sweep{{from{{transform:translateX(-96px)}}"
        f"to{{transform:translateX({grid_w + 98:.2f}px)}}}}"
        ".flash{opacity:0;animation:flash 10s linear infinite}"
        + delays
        + "@keyframes flash{0%{opacity:0}0.6%{opacity:.22}3%{opacity:.08}5%{opacity:0}100%{opacity:0}}"
        ".blink{animation:blink 2.2s ease-in-out infinite}"
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}"
        ".halo{animation:halo 2.6s ease-in-out infinite}"
        "@keyframes halo{0%,100%{opacity:.25}50%{opacity:.95}}"
        ".trail{animation:trail 6.5s linear infinite}"
        "@keyframes trail{from{stroke-dashoffset:0}to{stroke-dashoffset:-812}}"
        "</style>"
    )
    add("</defs>")

    add(f'<rect x=".5" y=".5" width="859" height="259" rx="18" fill="url(#pbg)" stroke="{BORDER}"/>')
    add('<g clip-path="url(#panelClip)">')
    add(f'<rect x=".5" y=".5" width="859" height="259" fill="url(#pmesh)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="259" fill="url(#pscan)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="259" fill="url(#pglow)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="259" fill="url(#pglow2)"/>')
    for path in (
        "M10 28 V10 H28", f"M{W - 28} 10 H{W - 10} V28",
        f"M10 {H - 28} V{H - 10} H28", f"M{W - 28} {H - 10} H{W - 10} V{H - 28}",
    ):
        add(f'<path d="{path}" stroke="{ACCENT}" stroke-opacity=".32" stroke-width="1"/>')
    add("</g>")

    add(f'<circle cx="26" cy="26" r="3.2" fill="{ACCENT}" class="blink"/>')
    add(f'<text x="38" y="31" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{ACCENT}" font-size="15" letter-spacing="1.6">CONTRIBUTION FIELD</text>')
    add(f'<text x="38" y="48" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="9" letter-spacing="1.3">LIVE SCAN · 52-WEEK WINDOW · {window_days} DAYS</text>')

    stats = [
        (512, "TOTAL", f"{total}", ACCENT, "start"),
        (606, "ACTIVE DAYS", f"{active_days}D", TEAL, "start"),
        (700, "BEST STREAK", f"{best_streak}D", "#FBBF24", "start"),
        (836, "PEAK DAY", f"{peak}", "#38BDF8", "end"),
    ]
    for x, label, value, color, anchor in stats:
        add(f'<text x="{x}" y="24" text-anchor="{anchor}" font-family="Consolas, \'Courier New\', monospace" '
            f'fill="{DIM}" font-size="8" letter-spacing="1.1">{label}</text>')
        add(f'<text x="{x}" y="52" text-anchor="{anchor}" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
            f'fill="{TEXT}" font-size="27" font-weight="700">{value}</text>')
        bar_x = x if anchor == "start" else x - 22
        add(f'<rect x="{bar_x}" y="58" width="22" height="2" fill="{color}"/>')

    add(f'<line x1="24" y1="64" x2="{W - 24}" y2="64" stroke="{DIVIDER}"/>')

    for col, label in months:
        x = grid_x + col * STEP
        add(f'<text x="{x:.2f}" y="88" font-family="Consolas, \'Courier New\', monospace" '
            f'fill="{FAINT}" font-size="8" letter-spacing="1">{label}</text>')
    for row, label in ((1, "MON"), (3, "WED"), (5, "FRI")):
        y = GRID_Y + row * STEP + 8
        add(f'<text x="{grid_x - 10:.2f}" y="{y:.2f}" text-anchor="end" '
            f'font-family="Consolas, \'Courier New\', monospace" fill="#3E5566" '
            f'font-size="7.5" letter-spacing=".8">{label}</text>')

    for col in range(columns):
        for row in range(ROWS):
            day = start + dt.timedelta(days=col * 7 + row)
            x = grid_x + col * STEP
            y = GRID_Y + row * STEP
            if day in days:
                level, _ = days[day]
                add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{CELL}" height="{CELL}" rx="2.6" fill="{LEVELS[level]}"/>')
            else:
                add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{CELL}" height="{CELL}" rx="2.6" fill="{FUTURE}"/>')

    for col in range(columns):
        x = grid_x + col * STEP
        add(f'<rect x="{x:.2f}" y="{GRID_Y}" width="{CELL}" height="{grid_h:.2f}" rx="1.4" '
            f'fill="#7DD3FC" class="flash f{col}"/>')

    add('<g clip-path="url(#gridClip)">')
    add(f'<g transform="translate({grid_x:.2f} {GRID_Y})"><g class="beam">')
    add(f'<rect x="0" y="0" width="96" height="{grid_h:.2f}" fill="url(#beam)"/>')
    add(f'<rect x="94" y="0" width="2" height="{grid_h:.2f}" fill="{PALE}" filter="url(#glow)"/>')
    add("</g></g></g>")

    today = last
    today_col = (today - start).days // 7
    today_row = (today.weekday() + 1) % 7
    tx = grid_x + today_col * STEP
    ty = GRID_Y + today_row * STEP
    add(f'<rect x="{tx - 1.2:.2f}" y="{ty - 1.2:.2f}" width="{CELL + 2.4}" height="{CELL + 2.4}" rx="3.2" '
        f'fill="none" stroke="{PALE}" stroke-width="1.2" class="halo"/>')

    add(f'<line x1="24" y1="198" x2="{W - 24}" y2="198" stroke="{DIVIDER}"/>')
    add(f'<circle cx="26" cy="216" r="2.4" fill="{TEAL}" class="blink"/>')
    add(f'<text x="36" y="219" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">SIGNAL NOMINAL</text>')
    add(f'<text x="{W - 24}" y="219" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">LAST SYNC · {sync_date}</text>')

    for x in range(24, W - 23, 72):
        add(f'<line x1="{x}" y1="232" x2="{x}" y2="240" stroke="{DIVIDER}"/>')
    add(f'<line x1="24" y1="236" x2="{W - 24}" y2="236" stroke="{BORDER}"/>')
    add(f'<line x1="24" y1="236" x2="{W - 24}" y2="236" stroke="{ACCENT}" stroke-width="1.6" '
        'stroke-linecap="round" stroke-dasharray="64 748" opacity=".85" class="trail"/>')

    add("</svg>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", help="parse a saved contributions page instead of fetching")
    parser.add_argument("--out", default="dist/contribution-signal.svg")
    args = parser.parse_args()

    if args.html:
        page = open(args.html, encoding="utf-8").read()
    else:
        page = fetch_calendar(CALENDAR_URL.format(user=USER))

    days = parse_calendar(page)
    svg = build_svg(days)
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"wrote {out_path} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()

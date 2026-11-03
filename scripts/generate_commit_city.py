#!/usr/bin/env python3
"""Render the commit-city skyline HUD from the public GitHub calendar."""

import argparse
import datetime as dt
import html
import os
import re
import time
import urllib.request

USER = os.environ.get("GITHUB_USER", "Skander-Bardaoui")
CALENDAR_URL = "https://github.com/users/{user}/contributions"

W, H = 860, 300
GROUND = 232.0
MAX_H = 114.0
TOWER_W = 11.0
DEPTH = 3.5
STEP = 15.0

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

BG_TOP, BG_BOTTOM = "#041417", "#030C0E"
BORDER = "#0E2E33"
ACCENT, TEAL, PALE = "#22D3EE", "#2DD4BF", "#A5F3FC"
AMBER, BLUE = "#FBBF24", "#38BDF8"
TEXT, MUTED, DIM, FAINT = "#E2E8F0", "#94A3B8", "#64748B", "#475569"


def fetch_calendar(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; profile-commit-city/1.0)",
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


def build_svg(days):
    dates = sorted(days)
    first, last = dates[0], dates[-1]
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    weeks = (last - start).days // 7 + 1

    weekly = []
    for week in range(weeks):
        total = active = 0
        for row in range(7):
            day = start + dt.timedelta(days=week * 7 + row)
            if day in days:
                count = days[day][1]
                total += count
                if count:
                    active += 1
        weekly.append((total, active))

    total = sum(count for _, count in days.values())
    active_days = sum(1 for _, count in days.values() if count > 0)
    best_week = 0
    best_week_idx = 0
    for index, (week_total, _) in enumerate(weekly):
        if week_total > best_week:
            best_week = week_total
            best_week_idx = index
    peak_date = max(dates, key=lambda day: days[day][1])
    peak = days[peak_date][1]
    window_days = (last - first).days + 1
    sync_date = f"{last.day:02d} {MONTHS[last.month - 1]} {last.year}"
    peak_label = f"{peak_date.day:02d} {MONTHS[peak_date.month - 1]} {peak_date.year}"

    grid_w = weeks * STEP - (STEP - TOWER_W)
    start_x = (W - grid_w) / 2
    max_week = max(1, best_week)

    months = []
    for week in range(weeks):
        if week == 0:
            months.append((week, MONTHS[first.month - 1]))
            continue
        for row in range(7):
            day = start + dt.timedelta(days=week * 7 + row)
            if day.day == 1:
                months.append((week, MONTHS[day.month - 1]))
                break

    towers = []
    for index, (week_total, _) in enumerate(weekly):
        ratio = week_total / max_week if max_week else 0
        height = 2.0 if week_total == 0 else 8 + ratio * (MAX_H - 8)
        x = start_x + index * STEP
        towers.append({
            "x": x,
            "cx": x + TOWER_W / 2,
            "h": height,
            "top": GROUND - height,
            "ratio": ratio,
            "total": week_total,
        })

    title = "Commit city — 52-week skyline of GitHub commits"
    desc = (
        f"{total} contributions across {window_days} days, {active_days} active days, "
        f"best week {best_week} contributions, peak {peak} on {peak_label}."
    )

    out = []
    add = out.append
    add(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(desc)}">')
    add(f"<title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc>")

    add("<defs>")
    add(f'<linearGradient id="pbg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient>')
    add('<radialGradient id="skyGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        'gradientTransform="translate(430 240) scale(430 95)">'
        f'<stop stop-color="{TEAL}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="moonGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        'gradientTransform="translate(664 104) scale(78)">'
        f'<stop stop-color="{ACCENT}" stop-opacity=".13"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="moon" cx=".38" cy=".32" r=".9">'
        f'<stop stop-color="#0F4C75"/><stop offset=".6" stop-color="#071E2A"/>'
        f'<stop offset="1" stop-color="{BG_BOTTOM}"/></radialGradient>')
    add(f'<linearGradient id="cityGrad" x1="0" y1="{GROUND}" x2="0" y2="{GROUND - MAX_H}" gradientUnits="userSpaceOnUse">'
        '<stop stop-color="#06141C"/><stop offset=".45" stop-color="#0B2C45"/>'
        '<stop offset=".8" stop-color="#0F4C75"/><stop offset="1" stop-color="#1682B8"/></linearGradient>')
    add('<linearGradient id="fog" x1="0" y1="188" x2="0" y2="232" gradientUnits="userSpaceOnUse">'
        '<stop stop-color="#041417" stop-opacity="0"/><stop offset="1" stop-color="#041417" stop-opacity=".8"/>'
        "</linearGradient>")
    add('<linearGradient id="beamV" x1="0" y1="232" x2="0" y2="68" gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{ACCENT}" stop-opacity=".34"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>'
        "</linearGradient>")
    add('<linearGradient id="meteorGrad" x1="0" y1="0" x2="30" y2="-9" gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{PALE}" stop-opacity=".9"/><stop offset="1" stop-color="{PALE}" stop-opacity="0"/>'
        "</linearGradient>")
    add('<linearGradient id="titleGrad" x1="0" y1="0" x2="1" y2="0">'
        f'<stop stop-color="{TEXT}"/><stop offset="1" stop-color="{PALE}"/></linearGradient>')
    add('<pattern id="pmesh" width="32" height="32" patternUnits="userSpaceOnUse">'
        '<path d="M32 0H0V32" stroke="#5EEAD4" stroke-opacity=".028"/></pattern>')
    add('<pattern id="pscan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#5EEAD4" opacity=".02"/></pattern>')
    add('<filter id="glow" x="-120%" y="-120%" width="340%" height="340%">'
        '<feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    add(f'<clipPath id="panelClip"><rect x=".5" y=".5" width="859" height="299" rx="16"/></clipPath>')

    add(
        "<style>"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        ".orbit{animation:spin 120s linear infinite}"
        "@keyframes twinkle{0%,100%{opacity:.12}50%{opacity:.65}}"
        ".twA{animation:twinkle 4.2s ease-in-out infinite}"
        ".twB{animation:twinkle 5.6s ease-in-out infinite}"
        ".twC{animation:twinkle 3.4s ease-in-out infinite}"
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}"
        ".blink1{animation:blink 2.2s ease-in-out infinite}"
        ".blink2{animation:blink 1.5s ease-in-out infinite}"
        "@keyframes beaconPulse{0%,100%{opacity:.3;transform:scale(.8)}50%{opacity:.95;transform:scale(1.18)}}"
        ".beacon{animation:beaconPulse 2.6s ease-in-out infinite}"
        "@keyframes winFlick{0%,100%{opacity:.25}50%{opacity:.9}}"
        ".win{animation:winFlick 5.5s ease-in-out infinite}"
        "@keyframes air{from{stroke-dashoffset:0}to{stroke-dashoffset:-796}}"
        ".air1{animation:air 18s linear infinite -6s}"
        ".air2{animation:air 26s linear infinite -14s}"
        "@keyframes meteor{0%{transform:translate(760px,72px);opacity:0}"
        "4%{opacity:.9}"
        "9%{transform:translate(610px,124px);opacity:0}"
        "100%{transform:translate(610px,124px);opacity:0}}"
        ".meteor{animation:meteor 13s ease-in infinite 4s}"
        "</style>"
    )
    add("</defs>")

    add(f'<rect x=".5" y=".5" width="859" height="299" rx="16" fill="url(#pbg)" stroke="{BORDER}"/>')
    add('<g clip-path="url(#panelClip)">')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#pmesh)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#pscan)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#skyGlow)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#moonGlow)"/>')

    twinkle_classes = ("twA", "twB", "twC")
    for i in range(34):
        x = 30 + (i * 173 + 61) % 800
        y = 66 + (i * 97 + 31) % 160
        radius = 0.7 + (i % 3) * 0.3
        opacity = 0.3 + (i % 4) * 0.1
        add(f'<circle cx="{x}" cy="{y}" r="{radius:.1f}" fill="{PALE}" opacity="{opacity:.2f}" '
            f'class="{twinkle_classes[i % 3]}" style="animation-delay:{-(i % 7) * 0.7:.2f}s"/>')

    for week, _ in months:
        gx = start_x + week * STEP + TOWER_W / 2
        add(f'<line x1="{gx:.2f}" y1="66" x2="{gx:.2f}" y2="{GROUND}" stroke="{ACCENT}" '
            f'stroke-opacity=".045"/>')

    add(f'<circle cx="664" cy="104" r="52" stroke="{ACCENT}" stroke-opacity=".18" '
        f'stroke-dasharray="1.5 7" class="orbit" style="transform-origin:664px 104px"/>')
    add(f'<circle cx="664" cy="104" r="38" fill="url(#moon)" stroke="{ACCENT}" stroke-opacity=".3"/>')
    add(f'<circle cx="664" cy="104" r="38" fill="none" stroke="{PALE}" stroke-opacity=".12"/>')
    add(f'<line x1="632" y1="104" x2="696" y2="104" stroke="{ACCENT}" stroke-opacity=".16"/>')

    add('<g class="meteor">')
    add(f'<line x1="0" y1="0" x2="30" y2="-9" stroke="url(#meteorGrad)" stroke-width="1.2"/>')
    add(f'<circle cx="0" cy="0" r="1.8" fill="{PALE}" filter="url(#glow)"/>')
    add("</g>")

    for i in range(weeks):
        bx = start_x + i * STEP + 4
        bh = 6 + (i * 37) % 23
        add(f'<rect x="{bx:.2f}" y="{GROUND - 6 - bh:.2f}" width="9" height="{bh}" '
            f'fill="#071C26" opacity=".85"/>')

    add(f'<line x1="40" y1="86" x2="820" y2="86" stroke="{BORDER}" stroke-opacity=".45"/>')
    add(f'<line x1="40" y1="86" x2="820" y2="86" stroke="{PALE}" stroke-opacity=".45" '
        f'stroke-dasharray="52 744" class="air1"/>')
    add(f'<line x1="40" y1="112" x2="820" y2="112" stroke="{BORDER}" stroke-opacity=".35"/>')
    add(f'<line x1="40" y1="112" x2="820" y2="112" stroke="{TEAL}" stroke-opacity=".4" '
        f'stroke-dasharray="34 762" class="air2"/>')

    add(f'<line x1="24" y1="{GROUND}" x2="{W - 24}" y2="{GROUND}" stroke="{ACCENT}" stroke-opacity=".22"/>')
    add(f'<rect x="24" y="{GROUND - 1}" width="{W - 48}" height="1" fill="{ACCENT}" opacity=".18"/>')

    for index, tower in enumerate(towers):
        x = tower["x"]
        top = tower["top"]
        height = tower["h"]
        ratio = tower["ratio"]
        if tower["total"] == 0:
            add(f'<rect x="{x:.2f}" y="{GROUND - 2:.2f}" width="{TOWER_W}" height="2" fill="#071820"/>')
            add(f'<line x1="{x:.2f}" y1="{GROUND - 2:.2f}" x2="{x + TOWER_W:.2f}" y2="{GROUND - 2:.2f}" '
                f'stroke="{ACCENT}" stroke-opacity=".2"/>')
            continue

        side = (f'{x + TOWER_W:.2f},{top:.2f} {x + TOWER_W + DEPTH:.2f},{top - DEPTH:.2f} '
                f'{x + TOWER_W + DEPTH:.2f},{GROUND - DEPTH:.2f} {x + TOWER_W:.2f},{GROUND:.2f}')
        roof = (f'{x:.2f},{top:.2f} {x + DEPTH:.2f},{top - DEPTH:.2f} '
                f'{x + TOWER_W + DEPTH:.2f},{top - DEPTH:.2f} {x + TOWER_W:.2f},{top:.2f}')
        is_peak = index == best_week_idx and best_week > 0
        front_stroke = PALE if is_peak else "#1E6E8C"
        front_opacity = ".55" if is_peak else ".3"

        add(f'<polygon points="{side}" fill="#04121A" fill-opacity=".92" stroke="{BORDER}" stroke-opacity=".5"/>')
        add(f'<polygon points="{roof}" fill="#7DD3FC" fill-opacity="{0.15 + ratio * 0.35:.2f}" '
            f'stroke="{ACCENT}" stroke-opacity=".3"/>')
        add(f'<rect x="{x:.2f}" y="{top:.2f}" width="{TOWER_W}" height="{height:.2f}" '
            f'fill="url(#cityGrad)" stroke="{front_stroke}" stroke-opacity="{front_opacity}"/>')
        add(f'<line x1="{x:.2f}" y1="{top:.2f}" x2="{x + TOWER_W:.2f}" y2="{top:.2f}" '
            f'stroke="{ACCENT}" stroke-opacity="{0.2 + ratio * 0.6:.2f}"/>')

        rows = min(8, int((height - 16) / 9)) if height >= 26 else 0
        for row in range(rows):
            for col in (0, 1):
                if (index * 3 + row * 5 + col) % 5 == 0:
                    continue
                wx = x + 2.6 + col * 3.6
                wy = top + 12 + row * 9
                lit = 0.35 + ((index + row + col) % 3) * 0.18
                color = AMBER if (index * 7 + row) % 23 == 0 else PALE
                flicker = ' class="win" style="animation-delay:%.2fs"' % ((index * 0.13) % 4) \
                    if index % 9 == 0 and row % 3 == 0 else ""
                add(f'<rect x="{wx:.2f}" y="{wy:.2f}" width="1.5" height="2" rx=".4" '
                    f'fill="{color}" opacity="{lit:.2f}"{flicker}/>')

    add(f'<rect x="20" y="188" width="820" height="44" fill="url(#fog)"/>')

    for rank, index in enumerate(sorted(range(weeks), key=lambda i: towers[i]["total"], reverse=True)[:3]):
        if towers[index]["total"] <= 0:
            continue
        cx = towers[index]["cx"]
        tip = towers[index]["top"] - DEPTH - (11 if rank == 0 else 7)
        add(f'<line x1="{cx:.2f}" y1="{towers[index]["top"] - DEPTH:.2f}" x2="{cx:.2f}" y2="{tip:.2f}" '
            f'stroke="{ACCENT}" stroke-opacity=".55"/>')
        add(f'<circle cx="{cx:.2f}" cy="{tip:.2f}" r="{1.9 if rank == 0 else 1.4}" '
            f'fill="{PALE}" filter="url(#glow)" class="blink1" style="animation-delay:{rank * 0.6:.1f}s"/>')

    today = towers[weeks - 1]
    tcx, ttop = today["cx"], today["top"]
    if ttop > 72:
        add(f'<rect x="{tcx - 1.2:.2f}" y="68" width="2.4" height="{ttop - 68:.2f}" fill="url(#beamV)"/>')
    add(f'<circle cx="{tcx + 7:.2f}" cy="69" r="2.2" fill="{ACCENT}" class="blink1"/>')
    add(f'<circle cx="{tcx:.2f}" cy="{ttop:.2f}" r="6.5" stroke="{PALE}" stroke-opacity=".8" '
        f'class="beacon" style="transform-origin:{tcx:.2f}px {ttop:.2f}px"/>')
    add(f'<circle cx="{tcx:.2f}" cy="{ttop:.2f}" r="2" fill="{PALE}" filter="url(#glow)"/>')

    if best_week > 0:
        peak_cx = towers[best_week_idx]["cx"]
        tag_w, tag_h = 96, 16
        tag_cx = min(max(peak_cx, 26 + tag_w / 2), W - 26 - tag_w / 2)
        tag_x = tag_cx - tag_w / 2
        tag_y = max(towers[best_week_idx]["top"] - 46, 66)
        conn_x = min(max(peak_cx, tag_x + 10), tag_x + tag_w - 10)
        add(f'<line x1="{conn_x:.2f}" y1="{tag_y + tag_h:.2f}" x2="{peak_cx:.2f}" '
            f'y2="{towers[best_week_idx]["top"] - DEPTH - 11:.2f}" stroke="{AMBER}" stroke-opacity=".4"/>')
        add(f'<rect x="{tag_x:.2f}" y="{tag_y:.2f}" width="{tag_w}" height="{tag_h}" rx="3" '
            f'fill="#061A22" stroke="{AMBER}" stroke-opacity=".3"/>')
        add(f'<text x="{tag_cx:.2f}" y="{tag_y + 11.5:.2f}" text-anchor="middle" '
            f'font-family="Consolas, \'Courier New\', monospace" fill="{AMBER}" '
            f'font-size="7" letter-spacing=".8">PEAK WEEK · {best_week}</text>')

    for week, label in months:
        gx = start_x + week * STEP + TOWER_W / 2
        add(f'<line x1="{gx:.2f}" y1="{GROUND}" x2="{gx:.2f}" y2="{GROUND + 4}" stroke="{BORDER}"/>')
        add(f'<text x="{gx:.2f}" y="246" text-anchor="middle" '
            f'font-family="Consolas, \'Courier New\', monospace" fill="{FAINT}" '
            f'font-size="7" letter-spacing="1">{label}</text>')

    for path in (
        "M10 26 V10 H26", f"M{W - 26} 10 H{W - 10} V26",
        f"M10 {H - 26} V{H - 10} H26", f"M{W - 26} {H - 10} H{W - 10} V{H - 26}",
    ):
        add(f'<path d="{path}" stroke="{ACCENT}" stroke-opacity=".32" stroke-width="1"/>')
    add("</g>")

    add(f'<text x="24" y="24" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="8" letter-spacing="2">SYS.CITY-01 // SKYLINE FEED</text>')
    add(f'<rect x="24" y="36" width="7" height="7" transform="rotate(45 27.5 39.5)" '
        f'fill="{ACCENT}" filter="url(#glow)"/>')
    add(f'<text x="42" y="46" font-family="Consolas, \'Courier New\', monospace" fill="url(#titleGrad)" '
        f'font-size="16" font-weight="700" letter-spacing="3">COMMIT CITY</text>')
    add(f'<rect x="184" y="33" width="54" height="16" rx="8" fill="{TEAL}" fill-opacity=".08" '
        f'stroke="{TEAL}" stroke-opacity=".4"/>')
    add(f'<circle cx="195" cy="41" r="2.2" fill="{TEAL}" class="blink1"/>')
    add(f'<text x="203" y="44.5" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{TEAL}" font-size="8" letter-spacing="1">LIVE</text>')
    add(f'<text x="{W - 24}" y="24" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8" letter-spacing="1.2">WINDOW · {window_days}D · {weeks} TOWERS</text>')
    add(f'<text x="{W - 24}" y="42" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{TEAL}" font-size="9" letter-spacing="1.6">HEIGHT · COMMITS</text>')
    add(f'<line x1="24" y1="58" x2="{W - 24}" y2="58" stroke="{BORDER}"/>')
    add(f'<line x1="24" y1="58" x2="128" y2="58" stroke="{ACCENT}" stroke-opacity=".55" stroke-width="1.2"/>')

    add(f'<line x1="24" y1="250" x2="{W - 24}" y2="250" stroke="{BORDER}"/>')
    add(f'<circle cx="26" cy="270" r="2.4" fill="{TEAL}" class="blink2"/>')
    add(f'<text x="36" y="273" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">SIGNAL NOMINAL</text>')
    add(f'<text x="26" y="287" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.3">PULSE = TODAY · TOWER = WEEK</text>')

    stats = (
        (392, "TOTAL", f"{total}", ACCENT),
        (500, "ACTIVE", f"{active_days}D", TEAL),
        (608, "BEST WEEK", f"{best_week}", AMBER),
        (700, "PEAK DAY", f"{peak}", BLUE),
    )
    for x, label, value, color in stats:
        add(f'<text x="{x}" y="266" font-family="Consolas, \'Courier New\', monospace" '
            f'fill="{FAINT}" font-size="7" letter-spacing="1.2">{label}</text>')
        add(f'<text x="{x}" y="281" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
            f'fill="{color}" font-size="13" font-weight="700">{value}</text>')

    add(f'<text x="{W - 24}" y="273" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">SYNC · {sync_date}</text>')
    add(f'<text x="{W - 24}" y="287" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.3">PEAK · {peak_label}</text>')

    add("</svg>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", help="parse a saved contributions page instead of fetching")
    parser.add_argument("--out", default="dist/commit-city.svg")
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

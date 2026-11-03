#!/usr/bin/env python3
"""Render the signal-core orbital HUD from the public GitHub calendar."""

import argparse
import datetime as dt
import html
import math
import os
import re
import time
import urllib.request

USER = os.environ.get("GITHUB_USER", "Skander-Bardaoui")
CALENDAR_URL = "https://github.com/users/{user}/contributions"

W, H = 860, 300
OX, OY = 196, 150
CORE_R, HUD_R = 32, 84

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
            "User-Agent": "Mozilla/5.0 (compatible; profile-signal-core/1.0)",
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
    last = dates[-1]
    total = sum(count for _, count in days.values())
    active_days = sum(1 for _, count in days.values() if count > 0)
    peak = max(count for _, count in days.values())
    best_streak = streaks(days)
    window_days = (last - dates[0]).days + 1
    sync_date = f"{last.day:02d} {MONTHS[last.month - 1]} {last.year}"

    title = "Signal core — live orbital telemetry"
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
        'gradientTransform="translate(190 150) scale(240)">'
        f'<stop stop-color="{ACCENT}" stop-opacity=".12"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="pglow2" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        'gradientTransform="translate(800 30) scale(300)">'
        f'<stop stop-color="{TEAL}" stop-opacity=".06"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="halo" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({OX} {OY}) scale(58)">'
        f'<stop stop-color="{ACCENT}" stop-opacity=".30"/>'
        f'<stop offset=".55" stop-color="{TEAL}" stop-opacity=".10"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="radar" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({OX} {OY}) scale({HUD_R})">'
        f'<stop stop-color="{ACCENT}" stop-opacity=".24"/>'
        f'<stop offset=".7" stop-color="{ACCENT}" stop-opacity=".07"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="core" cx=".35" cy=".3" r=".9">'
        f'<stop stop-color="#0F4C75"/><stop offset=".65" stop-color="#08222F"/>'
        f'<stop offset="1" stop-color="{BG_BOTTOM}"/></radialGradient>')
    add('<linearGradient id="titleGrad" x1="0" y1="0" x2="1" y2="0">'
        f'<stop stop-color="{TEXT}"/><stop offset="1" stop-color="{PALE}"/></linearGradient>')
    add('<pattern id="pmesh" width="32" height="32" patternUnits="userSpaceOnUse">'
        f'<path d="M32 0H0V32" stroke="#5EEAD4" stroke-opacity=".028"/></pattern>')
    add('<pattern id="pscan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#5EEAD4" opacity=".02"/></pattern>')
    add('<filter id="glow" x="-120%" y="-120%" width="340%" height="340%">'
        '<feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    add('<filter id="coreGlow" x="-80%" y="-80%" width="260%" height="260%">'
        '<feGaussianBlur stdDeviation="4.5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    add(f'<clipPath id="panelClip"><rect x=".5" y=".5" width="859" height="299" rx="16"/></clipPath>')

    add(
        "<style>"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        ".hud{animation:spin 120s linear infinite}"
        ".radar{animation:spin 8s linear infinite}"
        ".ringA{animation:spin 22s linear infinite}"
        ".ringB{animation:spin 30s linear infinite reverse}"
        ".ringC{animation:spin 14s linear infinite}"
        ".counter{animation:spin 20s linear infinite reverse}"
        "@keyframes pulse{0%,100%{opacity:.35;transform:scale(.9)}"
        "50%{opacity:.9;transform:scale(1.08)}}"
        ".pulse{animation:pulse 2.8s ease-in-out infinite}"
        "@keyframes dot{0%,100%{opacity:.4}50%{opacity:1}}"
        ".dot{animation:dot 2.8s ease-in-out infinite}"
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}"
        ".blink1{animation:blink 2.2s ease-in-out infinite}"
        ".blink2{animation:blink 1.5s ease-in-out infinite}"
        "@keyframes twinkle{0%,100%{opacity:.12}50%{opacity:.65}}"
        ".twA{animation:twinkle 4.2s ease-in-out infinite}"
        ".twB{animation:twinkle 5.6s ease-in-out infinite}"
        ".twC{animation:twinkle 3.4s ease-in-out infinite}"
        ".ch{opacity:0;animation:chIn .01s linear forwards}"
        "@keyframes chIn{to{opacity:1}}"
        ".cursor{opacity:0;animation:cursor 1.1s steps(1,end) infinite 2.15s}"
        "@keyframes cursor{0%,49%{opacity:1}50%,100%{opacity:0}}"
        "@keyframes eq{0%,100%{opacity:.25}50%{opacity:.9}}"
        ".eq{animation:eq 2.6s ease-in-out infinite}"
        "@keyframes scanY{from{transform:translateY(0)}to{transform:translateY(182px)}}"
        ".scanLine{animation:scanY 12s linear infinite}"
        "</style>"
    )
    add("</defs>")

    add(f'<rect x=".5" y=".5" width="859" height="299" rx="16" fill="url(#pbg)" stroke="{BORDER}"/>')
    add('<g clip-path="url(#panelClip)">')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#pmesh)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#pscan)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#pglow)"/>')
    add(f'<rect x=".5" y=".5" width="859" height="299" fill="url(#pglow2)"/>')

    twinkle_classes = ("twA", "twB", "twC")
    for i in range(26):
        x = 40 + (i * 173 + 61) % 780
        y = 66 + (i * 97 + 31) % 172
        radius = 0.7 + (i % 3) * 0.3
        opacity = 0.35 + (i % 4) * 0.1
        add(f'<circle cx="{x}" cy="{y}" r="{radius:.1f}" fill="{PALE}" opacity="{opacity:.2f}" '
            f'class="{twinkle_classes[i % 3]}" style="animation-delay:{-(i % 7) * 0.7:.2f}s"/>')

    for path in (
        "M10 26 V10 H26", f"M{W - 26} 10 H{W - 10} V26",
        f"M10 {H - 26} V{H - 10} H26", f"M{W - 26} {H - 10} H{W - 10} V{H - 26}",
    ):
        add(f'<path d="{path}" stroke="{ACCENT}" stroke-opacity=".32" stroke-width="1"/>')
    add("</g>")

    add(f'<text x="24" y="24" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="8" letter-spacing="2">SYS.ORB-01 // ORBITAL UPLINK</text>')
    add(f'<rect x="24" y="36" width="7" height="7" transform="rotate(45 27.5 39.5)" '
        f'fill="{ACCENT}" filter="url(#glow)"/>')
    add(f'<text x="42" y="46" font-family="Consolas, \'Courier New\', monospace" fill="url(#titleGrad)" '
        f'font-size="16" font-weight="700" letter-spacing="3">SIGNAL CORE</text>')
    add(f'<rect x="184" y="33" width="54" height="16" rx="8" fill="{TEAL}" fill-opacity=".08" '
        f'stroke="{TEAL}" stroke-opacity=".4"/>')
    add(f'<circle cx="195" cy="41" r="2.2" fill="{TEAL}" class="blink1"/>')
    add(f'<text x="203" y="44.5" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{TEAL}" font-size="8" letter-spacing="1">LIVE</text>')
    add(f'<text x="{W - 24}" y="24" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8" letter-spacing="1.2">36.8065°N · 10.1815°E</text>')
    add(f'<text x="{W - 24}" y="42" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{TEAL}" font-size="9" letter-spacing="1.6">STATUS · STABLE</text>')
    add(f'<line x1="24" y1="58" x2="{W - 24}" y2="58" stroke="{BORDER}"/>')
    add(f'<line x1="24" y1="58" x2="128" y2="58" stroke="{ACCENT}" stroke-opacity=".55" stroke-width="1.2"/>')

    add(f'<text x="24" y="112" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.5">CORE // SB-01</text>')
    add(f'<text x="336" y="112" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.5">ORBIT // STABLE</text>')

    add(f'<g class="hud" style="transform-origin:{OX}px {OY}px">')
    for i in range(36):
        angle = math.radians(i * 10)
        inner = 76 if i % 9 == 0 else 80
        x1 = OX + math.cos(angle) * inner
        y1 = OY + math.sin(angle) * inner
        x2 = OX + math.cos(angle) * HUD_R
        y2 = OY + math.sin(angle) * HUD_R
        color = PALE if i % 9 == 0 else ACCENT
        opacity = 0.5 if i % 9 == 0 else 0.22
        add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-opacity="{opacity}"/>')
    add("</g>")
    add(f'<circle cx="{OX}" cy="{OY}" r="{HUD_R}" stroke="{ACCENT}" stroke-opacity=".18" '
        f'stroke-dasharray="1.5 7"/>')
    add(f'<circle cx="{OX}" cy="{OY}" r="{HUD_R - 6}" stroke="{TEAL}" stroke-opacity=".10"/>')

    add(f'<g class="radar" style="transform-origin:{OX}px {OY}px">')
    add(f'<path d="M{OX} {OY} L274.9 121.3 A{HUD_R} {HUD_R} 0 0 1 {OX + HUD_R} {OY} Z" fill="url(#radar)"/>')
    add(f'<line x1="{OX}" y1="{OY}" x2="{OX + HUD_R}" y2="{OY}" stroke="{PALE}" '
        f'stroke-opacity=".5" filter="url(#glow)"/>')
    add("</g>")

    rings = (
        ("ringA", -16, 80, 30, ACCENT, "0.5", "", ((80, "2.6", "0s", PALE), (-80, "2", "1.2s", ACCENT))),
        ("ringB", 28, 62, 44, TEAL, "0.42", "", ((62, "2.2", "0.6s", PALE), (-62, "1.8", "1.8s", TEAL))),
        ("ringC", 0, 46, 46, PALE, "0.28", "2 6", ((46, "2", "0.3s", PALE), (-46, "1.8", "1.5s", TEAL))),
    )
    for cls, tilt, rx, ry, color, opacity, dash, sats in rings:
        add(f'<g class="{cls}" style="transform-origin:{OX}px {OY}px">')
        add(f'<g transform="rotate({tilt} {OX} {OY})">')
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        add(f'<ellipse cx="{OX}" cy="{OY}" rx="{rx}" ry="{ry}" stroke="{color}" '
            f'stroke-opacity="{opacity}"{dash_attr}/>')
        for offset, r, delay, sat_color in sats:
            add(f'<circle cx="{OX + offset}" cy="{OY}" r="{r}" fill="{sat_color}" '
                f'filter="url(#glow)" class="dot" style="animation-delay:{delay}"/>')
        add("</g></g>")

    add(f'<circle cx="{OX}" cy="{OY}" r="52" fill="url(#halo)" class="pulse" '
        f'style="transform-origin:{OX}px {OY}px"/>')
    add(f'<circle cx="{OX}" cy="{OY}" r="{CORE_R}" fill="url(#core)" stroke="{ACCENT}" stroke-opacity=".55"/>')
    add(f'<circle cx="{OX}" cy="{OY}" r="23" stroke="{PALE}" stroke-opacity=".3" stroke-dasharray="2 5" '
        f'class="counter" style="transform-origin:{OX}px {OY}px"/>')
    add(f'<text x="{OX}" y="157" text-anchor="middle" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
        f'font-weight="700" font-size="20" letter-spacing="1" fill="{PALE}" filter="url(#coreGlow)">SB</text>')
    add(f'<text x="{OX}" y="244" text-anchor="middle" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="8" letter-spacing="1.4">36.8065°N · 10.1815°E</text>')

    add('<g class="scanLine">')
    add(f'<line x1="24" y1="60" x2="{W - 24}" y2="60" stroke="{ACCENT}" stroke-opacity=".04"/>')
    add("</g>")

    add(f'<rect x="356" y="66" width="480" height="174" rx="8" fill="#04181D" stroke="{BORDER}"/>')
    add(f'<line x1="356" y1="86" x2="836" y2="86" stroke="{BORDER}"/>')
    for cx, color in ((370, ACCENT), (381, TEAL), (392, PALE)):
        add(f'<circle cx="{cx}" cy="76" r="2.3" fill="{color}" fill-opacity=".55"/>')
    add(f'<text x="404" y="79" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">SIGNAL.LOG — UPLINK</text>')
    add(f'<text x="824" y="79" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="8" letter-spacing="1">PTY-01</text>')

    def line(y, parts):
        spans = "".join(
            f'<tspan fill="{color}">{html.escape(text)}</tspan>' for text, color in parts
        )
        add(f'<text x="368" y="{y}" xml:space="preserve" '
            f'font-family="Consolas, \'Courier New\', monospace" font-size="11" letter-spacing=".2">{spans}</text>')

    line(104, [("$ ", ACCENT), ("whoami", TEXT)])
    line(119, [("> ", TEAL), ("skander.bardaoui", PALE), (" · full-stack engineer", MUTED)])
    line(134, [("$ ", ACCENT), ("status --now", TEXT)])
    line(149, [("> ", TEAL), ("building ", MUTED), ("novaentra", PALE), (" + ai oral-exam coach", MUTED)])
    line(164, [("> ", TEAL), ("open to ", MUTED), ("pfe 2026", TEAL), (" · full-stack / bi", MUTED)])
    line(179, [("$ ", ACCENT), ("signal --summary", TEXT)])
    line(194, [
        ("> ", TEAL),
        (f"{total}", ACCENT), (" total · ", MUTED),
        (f"{active_days}", TEAL), (" active · ", MUTED),
        (f"{best_streak}", AMBER), ("d streak · peak ", MUTED),
        (f"{peak}", BLUE),
    ])

    typed = "awaiting inbound signal"
    chars = []
    for index, char in enumerate(typed):
        delay = 0.8 + index * 0.055
        chars.append(f'<tspan class="ch" style="animation-delay:{delay:.3f}s">{html.escape(char)}</tspan>')
    add(f'<text x="368" y="209" xml:space="preserve" fill="{MUTED}" '
        f'font-family="Consolas, \'Courier New\', monospace" font-size="11" letter-spacing=".2">'
        f'<tspan fill="{TEAL}">&gt; </tspan>{"".join(chars)}'
        f'<tspan class="cursor" fill="{TEAL}">_</tspan></text>')

    add(f'<line x1="368" y1="218" x2="824" y2="218" stroke="{BORDER}"/>')
    add(f'<text x="368" y="229" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.5">UPLINK SPECTRUM</text>')
    for i in range(36):
        bar_h = 4 + (i * 7) % 9
        x = 500 + i * 9
        color = ACCENT if i % 2 == 0 else TEAL
        add(f'<rect x="{x}" y="{232 - bar_h}" width="5" height="{bar_h}" rx="1" fill="{color}" '
            f'fill-opacity=".55" class="eq" style="animation-delay:{i * 0.07:.2f}s"/>')

    add(f'<line x1="24" y1="250" x2="{W - 24}" y2="250" stroke="{BORDER}"/>')
    add(f'<circle cx="26" cy="270" r="2.4" fill="{TEAL}" class="blink2"/>')
    add(f'<text x="36" y="273" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">SIGNAL NOMINAL</text>')
    add(f'<text x="26" y="287" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.3">UPLINK 0x7F3A · ALL SYSTEMS NOMINAL</text>')

    stats = (
        (392, "TOTAL", f"{total}", ACCENT),
        (500, "ACTIVE", f"{active_days}D", TEAL),
        (608, "STREAK", f"{best_streak}D", AMBER),
        (700, "PEAK", f"{peak}", BLUE),
    )
    for x, label, value, color in stats:
        add(f'<text x="{x}" y="266" font-family="Consolas, \'Courier New\', monospace" '
            f'fill="{FAINT}" font-size="7" letter-spacing="1.2">{label}</text>')
        add(f'<text x="{x}" y="281" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
            f'fill="{color}" font-size="13" font-weight="700">{value}</text>')

    add(f'<text x="{W - 24}" y="273" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{DIM}" font-size="8.5" letter-spacing="1.2">SYNC · {sync_date}</text>')
    add(f'<text x="{W - 24}" y="287" text-anchor="end" font-family="Consolas, \'Courier New\', monospace" '
        f'fill="{FAINT}" font-size="7" letter-spacing="1.3">WINDOW · {window_days}D</text>')

    add("</svg>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", help="parse a saved contributions page instead of fetching")
    parser.add_argument("--out", default="dist/signal-core.svg")
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

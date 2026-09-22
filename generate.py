#!/usr/bin/env python3
"""Generate an XMLTV EPG for the Sicilian channel "Tele One".

Tele One publishes no guide feed — only a weekly grid as HTML at
https://www.teleone.it/chi-siamo/il-palinsesto-di-teleone/ , one block per weekday, each a list of
`HH.MM` times followed by a programme title. The schedule is the same every week, so this script
reads that grid once and projects it over the next seven days, chaining stop times across midnight.

Times on the page are Italian local time. They are written into the XMLTV with a Europe/Rome offset
rather than converted, so a viewer in another country sees them in their own clock.

Channel id is `teleone.it` — paste that exact string as the app's tvg-id.

Stdlib only — runs on a stock GitHub Actions runner.
"""

import html
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timedelta, time
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

CHANNEL_ID = "teleone.it"
CHANNEL_NAME = "Tele One"
DAYS_AHEAD = 7
ROME = ZoneInfo("Europe/Rome")
URL = "https://www.teleone.it/chi-siamo/il-palinsesto-di-teleone/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
OUT = "teleone.xml"

# Monday first, to match datetime.weekday(). The page writes some of them without their accent
# ("Mercoledi", "Giovedi"), so headings are matched with the accents stripped.
DAYS = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
_TIME = re.compile(r"(\d{1,2})[.:](\d{2})")


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower())
                   if unicodedata.category(c) != "Mn").strip()


def lines_of(page: str) -> list:
    body = re.sub(r"(?s)<(script|style).*?</\1>", "", page)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


def weekly_grid(lines: list) -> dict:
    """{weekday index: [(hour, minute, title)]} — the same week, every week."""
    seen, headings = set(), []
    for i, line in enumerate(lines):
        name = fold(line)
        if name in DAYS and name not in seen:
            seen.add(name)
            headings.append((DAYS.index(name), i))
    headings.sort(key=lambda h: h[1])

    grid = {}
    for n, (weekday, start) in enumerate(headings):
        end = headings[n + 1][1] if n + 1 < len(headings) else len(lines)
        block, slots = lines[start + 1:end], []
        for k in range(len(block) - 1):
            match = _TIME.fullmatch(block[k])
            title = block[k + 1]
            # A time followed by another time is a heading artefact, not a programme.
            if match and not _TIME.fullmatch(title):
                slots.append((int(match.group(1)), int(match.group(2)), title))
        if slots:
            grid[weekday] = slots
    return grid


def programmes(grid: dict, today) -> list:
    """[(start, stop, title)] over DAYS_AHEAD days, stops chained to the next start."""
    starts = []
    # One extra day, so the last real programme has a following start to end against.
    for offset in range(DAYS_AHEAD + 1):
        day = today + timedelta(days=offset)
        for hour, minute, title in grid.get(day.weekday(), []):
            # "24.00" is midnight at the END of that day, which is how the grid closes a night.
            midnight = datetime.combine(day, time(0, 0), ROME)
            starts.append((midnight + timedelta(hours=hour, minutes=minute), title))

    starts.sort(key=lambda s: s[0])
    out = []
    for n, (start, title) in enumerate(starts[:-1]):
        stop = starts[n + 1][0]
        if stop > start and start < datetime.combine(today + timedelta(days=DAYS_AHEAD), time(0, 0), ROME):
            out.append((start, stop, title))
    return out


def main() -> int:
    request = urllib.request.Request(URL, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            page = response.read().decode("utf-8", "replace")
    except Exception as error:                       # noqa: BLE001 — any failure is the same failure
        print(f"could not fetch the palinsesto: {error}", file=sys.stderr)
        return 1

    grid = weekly_grid(lines_of(page))
    if len(grid) < 5:
        # The page has always carried all seven days. Fewer means it changed shape, and writing a
        # half-empty guide over a good one is worse than writing nothing.
        print(f"parsed only {len(grid)} day(s) — refusing to overwrite {OUT}", file=sys.stderr)
        return 1

    shows = programmes(grid, datetime.now(ROME).date())
    if not shows:
        print("no programmes built — refusing to overwrite", file=sys.stderr)
        return 1

    stamp = lambda dt: dt.strftime("%Y%m%d%H%M%S %z")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<tv generator-info-name="teleone-epg" generator-info-url="https://github.com/sasagr/teleone-epg">',
             f'  <channel id="{CHANNEL_ID}">',
             f'    <display-name>{CHANNEL_NAME}</display-name>',
             '  </channel>']
    for start, stop, title in shows:
        lines.append(f'  <programme start="{stamp(start)}" stop="{stamp(stop)}" channel="{CHANNEL_ID}">')
        lines.append(f'    <title lang="it">{escape(title)}</title>')
        lines.append('  </programme>')
    lines.append('</tv>')

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(shows)} programmes across {len(grid)} weekdays → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

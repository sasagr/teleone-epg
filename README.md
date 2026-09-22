# Tele One EPG

A cloud-hosted XMLTV guide for **Tele One**, the Sicilian channel at
[teleone.it](https://www.teleone.it), built for an IPTV app that can attach a guide by URL.

Tele One publishes no feed — only a weekly grid as HTML on
[its palinsesto page](https://www.teleone.it/chi-siamo/il-palinsesto-di-teleone/): one block per
weekday, each a list of `HH.MM` times followed by a programme title. `generate.py` reads that grid
and projects it over the next seven days, chaining each programme's stop time to the next one's
start, across midnight included.

## Use it

| Field | Value |
|---|---|
| Stream | `https://648026e87a75e.streamlock.net/teleone/teleone/playlist.m3u8` |
| EPG | `https://raw.githubusercontent.com/sasagr/teleone-epg/main/teleone.xml` |
| tvg-id | `teleone.it` |

## Times

The palinsesto is written in Italian local time, and the XMLTV keeps it that way: every timestamp
carries a `+0200`/`+0100` Europe/Rome offset rather than being converted. A player shows it in
whatever clock the viewer is on — 06:00 in Palermo is 07:00 in Cyprus.

## How it stays current

A GitHub Action runs `generate.py` twice a day and commits `teleone.xml` when it differs. The
schedule itself rarely changes; what moves is the seven-day window.

The generator refuses to write a file if it parses fewer than five weekdays, or no programmes at
all — the page has always carried all seven, so anything less means it changed shape, and half a
guide over a good one is worse than nothing.

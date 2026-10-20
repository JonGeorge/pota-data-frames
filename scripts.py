#!/usr/bin/env python3
"""Render the POTA hunter card as a static HTML page with no JavaScript.

QRZ shows bios in a sandboxed frame that blocks scripts, including scripts
inside any iframe you embed. Plain HTML + CSS still renders, so a scheduled
GitHub Action runs this script and publishes the finished page.

Usage:
  python scripts/render_hunter_html.py --call N3XTR --out hunter/n3xtr/index.html
  python scripts/render_hunter_html.py --call N3XTR --json sample.json --out test.html   # offline test
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from urllib.parse import quote

CSS = """
  :root {
    --bg: #2E2720; --tile: #3B3229; --rule: #4A3F34;
    --text: #F1EBE2; --text-2: #D8CFC2; --muted: #A89B8C;
    --label: #B9C4A8; --accent: #D9875A;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: transparent; }
  body { font-family: Arial, Helvetica, sans-serif; color: var(--text); }
  a { color: inherit; text-decoration: none; }
  .card { width: 100%; max-width: 720px; background: var(--bg); border-radius: 16px;
          padding: 16px 18px 28px; display: flex; flex-direction: column; gap: 12px; }
  .top { display: flex; align-items: center; gap: 16px; }
  .id { display: flex; align-items: center; gap: 12px; padding-right: 16px; }
  .badge { width: 44px; height: 44px; border-radius: 22px; background: var(--accent);
           display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .eyebrow { font-size: 11px; letter-spacing: 2px; color: var(--label); }
  .call { font-size: 24px; font-weight: 700; line-height: 1; letter-spacing: .5px; }
  .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; flex-grow: 1; }
  .stat { background: var(--tile); border-radius: 12px; padding: 8px 12px; display: flex; flex-direction: column; gap: 2px; }
  .num { font-size: 24px; font-weight: 700; line-height: 1.1; color: var(--accent); font-variant-numeric: tabular-nums; }
  .lbl { font-size: 11px; letter-spacing: 1px; color: var(--label); }
  .recent { border-top: 1px solid var(--rule); padding-top: 10px; display: flex; flex-direction: column; gap: 8px; }
  .recent-head { display: flex; justify-content: space-between; align-items: center; }
  .stamp { font-size: 11px; color: var(--muted); }
  .list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
  .row { display: flex; align-items: center; gap: 12px; padding: 4px 8px; border-radius: 6px;
         font-size: 12px; color: var(--text-2); min-width: 0; font-variant-numeric: tabular-nums; }
  .row.shade { background: var(--tile); }
  .row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
  .n { width: 18px; color: var(--muted); }
  .act { font-weight: 700; font-size: 13px; color: var(--text); width: 110px; }
  .ref { color: var(--accent); width: 80px; }
  .loc { color: var(--label); width: 56px; }
  .bm { color: var(--muted); width: 70px; }
  .row span.park { flex-shrink: 1; min-width: 0; }
  .msg { font-size: 12px; color: var(--muted); padding: 4px 8px; }
  @media (max-width: 560px) { .top { flex-wrap: wrap; } .row span.park { display: none; } }
"""

BADGE = ('<svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2E2720" '
         'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 19l7-12 4 6 2-3 7 9z"></path>'
         '<path d="M7 19c2-2 4-2 6 0"></path></svg>')


def fmt_num(n):
    return f"{n:,}" if isinstance(n, int) else "—"


def fmt_loc(loc):
    parts = [p.strip() for p in str(loc or "").split(",") if p.strip()]
    if not parts:
        return ""
    first = parts[0][3:] if parts[0].startswith("US-") else parts[0]
    return first + "+" if len(parts) > 1 else first


def fetch_profile(call):
    req = urllib.request.Request("https://api.pota.app/profile/" + quote(call), headers={
        "Accept": "application/json",
        "User-Agent": "pota-data-frames (github.com/JonGeorge/pota-data-frames)",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def build(data, call, count):
    e = escape
    stats = data.get("stats") or {}
    hunter = stats.get("hunter") or {}
    qsos = (data.get("recent_activity") or {}).get("hunter_qsos") or []
    qsos = sorted(qsos, key=lambda q: str(q.get("date") or ""), reverse=True)[:count]
    stamp = datetime.now(timezone.utc).strftime("%d %b %H:%M UTC")

    rows = []
    for i, q in enumerate(qsos):
        when = str(q.get("date") or "").replace("T", " ")[:16]
        title = " · ".join(x for x in [q.get("park"), q.get("location"), when + " UTC" if when else ""] if x)
        bm = " ".join(x for x in [q.get("band"), q.get("mode")] if x)
        rows.append(
            f'<li class="row{" shade" if i % 2 == 0 else ""}" title="{e(title)}">'
            f'<span class="n">{i + 1:02d}</span>'
            f'<span class="act">{e(q.get("callsign") or "—")}</span>'
            f'<span class="ref">{e(q.get("reference") or "—")}</span>'
            f'<span class="loc">{e(fmt_loc(q.get("location")))}</span>'
            f'<span class="bm">{e(bm)}</span>'
            f'<span class="park">{e(q.get("park") or "")}</span></li>'
        )
    if not rows:
        rows.append('<li class="msg">No recent hunter contacts yet.</li>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(call)} POTA Hunter</title>
<style>{CSS}</style>
</head>
<body>
<div class="card">
  <div class="top">
    <div class="id">
      <div class="badge">{BADGE}</div>
      <div><div class="eyebrow">POTA HUNTER</div><div class="call">{e(call)}</div></div>
    </div>
    <div class="stats">
      <div class="stat"><div class="num">{fmt_num(hunter.get("parks"))}</div><div class="lbl">PARKS</div></div>
      <div class="stat"><div class="num">{fmt_num(hunter.get("qsos"))}</div><div class="lbl">QSOS</div></div>
      <div class="stat"><div class="num">{fmt_num(stats.get("awards"))}</div><div class="lbl">AWARDS</div></div>
    </div>
  </div>
  <div class="recent">
    <div class="recent-head">
      <div class="eyebrow">LAST {count} HUNTED</div>
      <div class="stamp">pota.app · updated {e(stamp)}</div>
    </div>
    <ol class="list">
      {"".join(rows)}
    </ol>
  </div>
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--call", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--json", help="read profile from a file instead of the POTA API")
    a = ap.parse_args()

    call = a.call.strip().upper()
    count = min(max(a.count, 1), 25)
    try:
        if a.json:
            with open(a.json) as f:
                data = json.load(f)
        else:
            data = fetch_profile(call)
    except Exception as err:
        # Keep the last good page rather than publishing an error.
        sys.exit(f"Could not fetch POTA profile for {call}: {err}")
    if not isinstance(data, dict) or "stats" not in data:
        sys.exit(f"Unexpected POTA response for {call}; leaving existing page in place.")

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(build(data, call, count))
    os.replace(tmp, a.out)
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()

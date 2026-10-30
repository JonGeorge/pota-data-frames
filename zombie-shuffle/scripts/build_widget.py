#!/usr/bin/env python3
"""Build the N3XTR "Zombies worked" widget from Zombie Shuffle Logger CSV exports.

Reads every *.csv in data/ (merging and de-duplicating rows), and writes a single
self-contained page to _site/index.html for GitHub Pages. Standard library only.

Only public-safe fields are published: time, band, call, SPC, zombie name, bonus.
RST, frequency, power and your Notes column never leave the CSV.
"""
from __future__ import annotations

import csv
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "_site"

MY_CALL = "N3XTR"
MAX_ROWS = 12          # rows shown in the widget, newest first
REFRESH_SECONDS = 300  # viewers' browsers reload the widget every 5 minutes
BAND_ORDER = ["80m", "40m", "20m", "15m", "10m"]


def load_rows() -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for path in sorted(DATA.glob("*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                call = (r.get("Call") or "").strip().upper()
                if not call:
                    continue  # blank starter row
                date = (r.get("Date") or "").strip()
                t_utc = (r.get("Time_UTC") or "").strip().replace(":", "").zfill(4)
                t_loc = (r.get("Time_Local") or "").strip().replace(":", "").zfill(4)
                key = f"{date}|{t_utc}|{call}"
                if key in seen:
                    continue
                seen.add(key)
                nr = (r.get("Zombie_Nr_Rcvd") or "").strip()
                bonus_flag = (r.get("Bonus_Station") or "").strip().lower()
                rows.append({
                    "date": date,
                    "utc": t_utc,
                    "local": t_loc,
                    "band": (r.get("Band") or "").strip().lower(),
                    "call": call,
                    "spc": (r.get("SPC_Rcvd") or "").strip().upper(),
                    "nr": nr,
                    "name": (r.get("Zombie_Name_Rcvd") or "").strip().upper(),
                    "bonus": bonus_flag in {"y", "yes", "true", "1", "x"} or nr == "4321",
                })
    # Local date + local time sorts correctly through the UTC-midnight rollover.
    rows.sort(key=lambda q: (q["date"], q["local"]), reverse=True)
    return rows


def stats(rows: list[dict]) -> dict:
    pts = sum(int(q["nr"]) for q in rows if q["nr"].isdigit())
    bonus = sum(1 for q in rows if q["bonus"])
    spcs = {q["spc"] for q in rows if q["spc"]}
    bands: dict[str, int] = {}
    for q in rows:
        bands[q["band"]] = bands.get(q["band"], 0) + 1
    band_txt = " · ".join(f"{b} {bands[b]}" for b in BAND_ORDER if b in bands) or "–"
    return {
        "qsos": len(rows),
        "bonus": bonus,
        "spcs": len(spcs),
        "score": pts * max(1, bonus),
        "bands": band_txt,
    }


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


def hm(t: str) -> str:
    return f"{t[:2]}:{t[2:]}" if len(t) == 4 else t


def render(rows: list[dict]) -> str:
    s = stats(rows)
    built = datetime.now(timezone.utc).strftime("%H:%MZ %b %d").replace(" 0", " ")
    shown = rows[:MAX_ROWS]
    more = len(rows) - len(shown)

    if shown:
        lines = []
        for q in shown:
            tr = '<tr class="bonus">' if q["bonus"] else "<tr>"
            tag = "<span>BONUS</span>" if q["bonus"] else ""
            lines.append(
                f'{tr}<td class="t">{e(hm(q["utc"]))}<span>Z</span></td>'
                f'<td class="b">{e(q["band"])}</td>'
                f'<td class="c">{e(q["call"])}</td>'
                f'<td>{e(q["spc"])}</td>'
                f'<td class="n">{e(q["name"])}</td>'
                f'<td class="tag">{tag}</td></tr>'
            )
        body_rows = "\n".join(lines)
        plural = "s" if more != 1 else ""
        more_html = f'<p class="more">+ {more} earlier zombie{plural}</p>' if more > 0 else ""
        table = f"""<div class="scroll"><table>
<thead><tr><th>UTC</th><th>Band</th><th>Call</th><th>SPC</th><th>Zombie</th><th></th></tr></thead>
<tbody>
{body_rows}
</tbody></table></div>
{more_html}"""
    else:
        table = """<div class="empty"><strong>No zombies in the crypt yet</strong>
The log updates on dinner breaks. Listen for CQ BOO near 7.030 and 7.040.</div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>Zombies worked by {MY_CALL}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Creepster&family=Fredoka:wght@400;600&family=IBM+Plex+Mono:wght@500;600&display=swap">
<style>
:root {{
  --bg: #1d1529; --panel: #170f22; --ink: #f2eadc; --muted: #ab9fbd; --line: #362a49;
  --pumpkin: #ff8a2a; --night: #b79cf0; --slime: #9be15d; --slime-soft: #1f3314;
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; height: 100%; }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.4 "Fredoka", "Trebuchet MS", system-ui, sans-serif;
  display: flex; flex-direction: column; gap: 10px; padding: 14px 16px; overflow: hidden; }}
header {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px 12px; }}
h1 {{ margin: 0; font: 400 28px/1 "Creepster", "Chiller", Impact, fantasy; letter-spacing: .03em; color: var(--night);
  display: flex; align-items: center; gap: 8px; }}
h1 i {{ width: 10px; height: 10px; border-radius: 50%; background: var(--pumpkin); box-shadow: 0 0 10px var(--pumpkin); }}
.upd {{ font: 500 12px "IBM Plex Mono", ui-monospace, monospace; color: var(--muted); }}
.stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }}
.stat {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; min-width: 0; }}
.stat b {{ display: block; font: 600 18px "IBM Plex Mono", ui-monospace, monospace; font-variant-numeric: tabular-nums;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.stat span {{ font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
.stat.score {{ background: radial-gradient(circle at 30% 20%, #ffb15c, var(--pumpkin) 65%); border-color: var(--pumpkin); color: #1a1006; }}
.stat.score span {{ color: #1a1006; opacity: .75; }}
.scroll {{ flex: 1; min-height: 0; overflow-y: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }}
table {{ width: 100%; border-collapse: collapse; font: 500 14px "IBM Plex Mono", ui-monospace, monospace; font-variant-numeric: tabular-nums; }}
th {{ position: sticky; top: 0; background: var(--panel); text-align: left; font: 600 11px "Fredoka", system-ui, sans-serif;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted); padding: 7px 10px; border-bottom: 1px solid var(--line); }}
td {{ padding: 6px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }}
tr:last-child td {{ border-bottom: 0; }}
td.t span {{ color: var(--muted); }}
td.b {{ color: var(--muted); }}
td.c {{ font-weight: 600; color: var(--ink); }}
td.n {{ color: var(--pumpkin); }}
tr.bonus td.c {{ color: var(--slime); }}
td.tag span {{ font: 700 10px "Fredoka", system-ui, sans-serif; letter-spacing: .06em; color: var(--slime);
  background: var(--slime-soft); border: 1px solid var(--slime); padding: 1px 7px; border-radius: 999px; }}
.more {{ margin: 0; font-size: 12px; color: var(--muted); text-align: right; }}
.empty {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
  gap: 4px; border: 1px dashed #6a52a0; border-radius: 8px; color: var(--muted); padding: 16px; }}
.empty strong {{ font: 400 22px "Creepster", fantasy; letter-spacing: .03em; color: var(--pumpkin); }}
@media (max-width: 480px) {{
  .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  th:nth-child(2), td:nth-child(2), th:nth-child(4), td:nth-child(4) {{ display: none; }}
}}
</style>
</head>
<body>
<header>
  <h1><i aria-hidden="true"></i>Zombies worked</h1>
  <span class="upd">updated {e(built)} · {e(s["bands"])}</span>
</header>
<div class="stats">
  <div class="stat"><span>QSOs</span><b>{s["qsos"]}</b></div>
  <div class="stat"><span>Bonus</span><b>{s["bonus"]}</b></div>
  <div class="stat"><span>States/Prov</span><b>{s["spcs"]}</b></div>
  <div class="stat score"><span>Est. score</span><b>{s["score"]:,}</b></div>
</div>
{table}
</body>
</html>
"""


def main() -> int:
    if not DATA.is_dir():
        print(f"No data/ folder at {DATA}", file=sys.stderr)
        return 1
    rows = load_rows()
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(render(rows), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built _site/index.html with {len(rows)} QSO(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

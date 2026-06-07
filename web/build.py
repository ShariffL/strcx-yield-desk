#!/usr/bin/env python3
"""
build.py — generate web/index.html for the STRCx Yield Desk.

The dashboard is a single, self-contained HTML file (no CDN, no network, no
build tooling) so a judge can open it cold — exactly like the CLI runs keyless.
Numbers are not hand-typed: this script runs the real desk.py engine in --mock
mode and bakes the authentic JSON into the page, then mirrors only the small
interactive math (hold simulation, current yield) in JS.

Run:  python3 web/build.py     ->  writes web/index.html
"""
from __future__ import annotations
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
sys.path.insert(0, ROOT)

import kraken_client as K          # noqa: E402
import analytics as A              # noqa: E402


def desk_json(args: list[str]) -> dict:
    """Run `python3 desk.py --mock <args> --json` and parse the result."""
    cmd = [sys.executable, os.path.join(ROOT, "desk.py"), "--mock", *args, "--json"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"desk.py failed for {args}: {out.stderr or out.stdout}")
    return json.loads(out.stdout)


def series(fname: str):
    return K.extract_ohlc_series(K._load_mock(fname))


def collect() -> dict:
    scan = desk_json(["scan"])
    rv = desk_json(["rv"])
    hedge = desk_json(["hedge", "--pair", "MSTRx/USD", "--notional", "5000"])
    holdsim = desk_json(["holdsim", "--amount", "5000", "--months", "12"])

    s, m = series("ohlc_strcx.json"), series("ohlc_mstrx.json")
    sv, mv = A.align_on_timestamp(s, m)
    ratio_hist = [mm / ss for mm, ss in zip(mv, sv) if ss]

    return {
        "scan": scan,
        "rv": rv,
        "hedge": hedge,
        "holdsim": holdsim,
        "series": {
            "strcx": [[t, round(c, 4)] for t, c in s],
            "mstrx": [[t, round(c, 4)] for t, c in m],
            "ratio": [round(r, 4) for r in ratio_hist],
        },
        "meta": {
            "repo": "https://github.com/ShariffL/strcx-yield-desk",
            "par": scan.get("par", 100.0),
            "btc_perp": "PF_XBTUSD",
        },
    }


def main():
    data = collect()
    tpl_path = os.path.join(WEB, "template.html")
    with open(tpl_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    blob = json.dumps(data, separators=(",", ":"))
    html = tpl.replace("/*__DATA__*/null", blob)
    out_path = os.path.join(WEB, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out_path}  ({len(html):,} bytes)")
    print("open it:  open web/index.html")


if __name__ == "__main__":
    main()

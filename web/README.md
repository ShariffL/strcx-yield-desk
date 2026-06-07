# STRCx Yield Desk — browser UI

A single, self-contained dashboard for the desk. No build step, no server, no
network, no dependencies — just like the CLI, a judge can open it cold.

## View it

Open the file directly in any browser:

```bash
open web/index.html          # macOS
# or just double-click web/index.html
```

It works over `file://` because everything (data, charts, logic) is inlined —
there is no `fetch`, no CDN, no external asset.

## What's on it

- **Scan** — live price vs $100 par, current yield, pull-to-par, with an
  interactive coupon slider (STRC's coupon is variable).
- **Price history** — daily closes against the par line.
- **Relative value** — MSTRx/STRCx ratio, z-score and ±1σ band, risk-on/off signal.
- **BTC-beta hedge** — beta, hedge notional and the futures-paper short, with R²/corr/n fit quality.
- **Hold simulator** — interactive amount / period / coupon sliders.

## Regenerate

The numbers are **baked from the real `desk.py` engine** (mock dataset), not
hand-typed. To refresh them after changing the analytics or mock data:

```bash
python3 web/build.py         # runs desk.py --json and rewrites web/index.html
```

`build.py` runs each subcommand with `--mock … --json`, pulls the OHLC series via
`kraken_client`, and injects the result into `template.html`. Only the small
interactive math (hold simulation, current yield) is mirrored in JS.

## A shareable URL for the jury (optional)

`index.html` is static, so it can go on any static host. For GitHub Pages, the
simplest route is to serve it from a `/docs` folder or the repo root (Pages can't
serve an arbitrary `web/` subfolder directly).

## Note on the logo

The emblem in the header is a clean **generated SVG mark**, not an official
brand asset. Swap the `<svg class="logo">…</svg>` block in `template.html` (then
re-run `build.py`) if you have the official STRCx/xStocks logo.

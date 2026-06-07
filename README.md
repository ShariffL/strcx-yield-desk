# STRCx Yield Desk

**Run a tokenised preferred like a fixed-income desk — on top of the Kraken CLI.**

STRCx (Strategy PP Variable xStock) isn't a moonshot token. It's a tokenised
*preferred share* that should sit near **$100 par**, with its dividend accruing
on-chain via a **daily rebase multiplier**. The right lens is fixed income:
*am I being paid enough to hold this, and what's the real risk underneath?*

Most agents treat every token like a bet. This one treats STRCx like credit.

```
$ python3 desk.py --mock demo
STRCx 97.44 USD  |  DISCOUNT (-2.56% vs 100 par)
  current yield : 9.24%   (at 9.0% coupon on par)
  pull-to-par   : +2.63%  if it reverts to par
  read          : trading below par — you're paid to wait (yield + upside to par).
...
```

## What it does

Three tools, one desk:

| Tool        | Question it answers                                   | Data source            | Keys? |
|-------------|-------------------------------------------------------|------------------------|-------|
| `scan`      | Is STRCx cheap vs par? What yield am I really earning?| Kraken public market   | none  |
| `holdsim`   | "If I hold $X for N months...?"                       | Kraken public market   | none  |
| `rv`        | Risk-on or risk-off? (MSTRx common vs STRCx preferred)| Kraken public market   | none  |
| `hedge`     | Strip the BTC swing out of the position               | Kraken **futures paper** | none |

The whole desk runs **keyless**: `scan`/`holdsim`/`rv` read public market data,
`hedge` uses the local futures-paper simulator. A judge can run all of it cold.

Honest scope: STRCx itself can't be *paper-traded* — the spot paper engine has no
`--asset-class`, so it can't price tokenised assets. That's why the desk is
**analyse + hedge**, with the only live execution happening in futures paper.
The live rebase multiplier (your real accrued yield) is a keyed extension; see below.

## Quickstart (no keys, no Kraken binary, no network)

```bash
python3 desk.py --mock demo            # narrated end-to-end
python3 desk.py --mock scan
python3 desk.py --mock holdsim --amount 5000 --months 12
python3 desk.py --mock rv
python3 desk.py --mock hedge --pair MSTRx/USD --notional 5000          # beta over default 90d
python3 desk.py --mock hedge --pair MSTRx/USD --lookback 180 --json    # longer window, machine output
python3 tests/test_analytics.py        # 11/11 unit tests on the math
```

`--mock` serves canned data from `mock_data/` so nothing external is needed.

## Run it for real (keyless)

1. Install the Kraken CLI:
   ```bash
   curl --proto '=https' --tlsv1.2 -LsSf \
     https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh
   ```
2. Confirm STRCx/MSTRx are reachable and check the exact ticker JSON shape once:
   ```bash
   bash scripts/keyless-probe.sh
   kraken ticker STRCx/USD --asset-class tokenized_asset -o json
   ```
   `kraken_client.extract_last_price()` is tolerant, but if the field names differ
   from the assumed Kraken-REST shape, adjust that one function.
3. Drop `--mock`:
   ```bash
   python3 desk.py scan
   python3 desk.py rv
   python3 desk.py hedge --pair MSTRx/USD --notional 5000 --execute   # opens the short in futures paper
   ```

## Make it agentic (the "Agent Zero" layer)

The Kraken CLI ships an MCP server. Expose only the keyless groups and let an
agent (Claude Code, Cursor, ...) drive the desk in plain language:

```bash
kraken mcp -s market,paper,futures-paper
```

See `AGENT.md` for the wiring and example prompts ("is STRCx cheap right now?",
"hedge my MSTRx position", "simulate holding $2k for 6 months").

## Keyed extension (optional, not needed for the demo)

Your *real* accrued yield comes from the rebase multiplier on private endpoints:

```bash
kraken balance --rebase-multiplier rebased -o json   # balance AFTER the multiplier
kraken balance --rebase-multiplier base    -o json   # balance BEFORE
kraken ledgers --asset STRCx -o json                 # accrual history
```

`rebased / base` = the cumulative multiplier; the daily delta = your effective yield.

## How it maps to the judging criteria

- **Innovation** — treats a token as a *preferred* (par + daily multiplier); uses the
  obscure `--rebase-multiplier` flag almost nobody finds.
- **Technical execution** — pure, unit-tested analytics; tolerant parsing; beta is
  estimated on **timestamp-aligned** returns over a configurable lookback with an
  **R²/correlation/n** quality readout (and an honest fallback on thin data); the RV
  signal uses an aligned historical ratio band; a working futures-paper hedge; zero deps.
- **Use of Kraken CLI** — tokenised market data + futures paper + MCP, all native.
- **Clarity** — every tool prints its reasoning in plain language; runs keyless so it's
  verifiable in one command.
- **Practical utility** — a real income/risk workflow, especially for non-US holders.

## Files

```
desk.py            CLI: scan / holdsim / rv / hedge / demo
analytics.py       pure math: par, yield, hold-sim, beta, RV signal (unit-tested)
kraken_client.py   thin wrapper around the kraken binary + mock loader
mock_data/         canned ticker/OHLC JSON for keyless runs
tests/             unit tests for the analytics
scripts/           keyless probe + demo runner
AGENT.md           MCP / Claude Code agentic wiring
DEMO.md            ~2.5 min recording script mapped to the criteria
SETUP-CLAUDE-CODE.md  step-by-step: run it and publish it live via Claude Code
```

## Notes & caveats

- Pair names (`STRCx/USD`, `MSTRx/USD`) and the ticker JSON shape should be confirmed
  with one live call (see step 2). Everything is built to make that a one-line tweak.
- The dividend rate (`--rate`, default 0.09) is a *variable* coupon — set it to
  Strategy's currently published STRC rate. It's net-of-withholding, mirroring the
  on-chain multiplier.
- Prices are USD; the hold-sim ignores USD/EUR moves.
- This is a planning/analysis tool, not financial advice and not a profit promise.

## License

MIT — see `LICENSE`.

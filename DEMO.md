# DEMO.md — ~2.5 minute recording script

Goal: show a clear story and hit all five criteria. Everything runs keyless, so you
can record in one take. Type the commands; say the lines.

---

**0:00 — The hook (innovation)**
> "Most agents treat every token like a moonshot. STRCx isn't one. It's a tokenised
> *preferred share* that should sit near $100 par, and its dividend accrues on-chain
> through a daily rebase multiplier. So I built a desk that runs it like fixed income."

**0:20 — Is it cheap? (clarity + use of CLI)**
```bash
python3 desk.py scan        # or --mock for offline
```
> "It pulls the price straight from the Kraken CLI's tokenised market data — no third
> party. Right now it's a couple percent under par, so I'm earning a ~9% coupon *and*
> I've got upside if it pulls back to par. The tool says that in plain language."

**0:50 — What does holding actually give me? (practical utility)**
```bash
python3 desk.py holdsim --amount 2000 --months 6
```
> "The multiplier rebases my balance up over time. Hold $2k for six months and here's
> the token growth and the value, flat versus pull-to-par."

**1:15 — Risk-on or risk-off? (innovation)**
```bash
python3 desk.py rv
```
> "It compares the volatile common, MSTRx, against the stable preferred, STRCx. When
> the common looks rich, the desk says de-risk toward the preferred. Pure relative
> value, read straight from market data."

**1:40 — Kill the BTC risk (technical execution + use of CLI)**
```bash
python3 desk.py hedge --pair MSTRx/USD --notional 5000 --execute
```
> "If I hold the common for upside, the real risk underneath is Bitcoin. The desk
> estimates the BTC beta from price history and opens the hedge as a short in Kraken's
> futures-paper engine — leverage, funding and liquidation all simulated, no keys, no
> money."

**2:10 — The agent (Agent Zero)**
```bash
kraken mcp -s market,paper,futures-paper
```
> "And because the Kraken CLI is MCP-native, I expose only the keyless tools and just
> *ask* the desk these questions in Claude Code. Everything you saw, an agent can chain
> on its own — and you can run the whole thing yourself without an API key."

**2:30 — Close**
> "STRCx Yield Desk: a tokenised preferred, run like credit, fully verifiable, zero keys."

---

### Criteria checklist
- Innovation — preferred/par/multiplier framing; the `--rebase-multiplier` flag.
- Technical execution — unit-tested math, tolerant parsing, working futures-paper hedge.
- Use of Kraken CLI — tokenised market data + futures paper + MCP.
- Clarity — plain-language reasoning; one-command keyless runs.
- Practical utility — real income/risk workflow for non-US holders.

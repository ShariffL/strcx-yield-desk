# AGENT.md — the agentic layer

The contest is called **Agent Zero**, and the Kraken CLI is MCP-native. The desk
is the deterministic toolkit; an agent drives it in plain language.

## 1. Expose the keyless Kraken tools over MCP

```bash
kraken mcp -s market,paper,futures-paper
```

Only no-auth groups: public market data + spot paper + futures paper. No keys are
ever loaded, so the agent cannot touch real funds.

## 2. Wire it into Claude Code (or Cursor/etc.)

Point your MCP client at the command above, then add this repo to the workspace so
the agent can call `python3 desk.py ...` directly. Suggested system prompt:

> You are the STRCx Yield Desk. STRCx is a tokenised preferred that should sit near
> $100 par, with dividend accruing via a daily rebase multiplier — reason about it as
> fixed income, not as a volatile equity. Use `desk scan/holdsim/rv/hedge` (add
> `--json` when you need to parse) for STRCx analytics and the BTC-beta hedge, and the
> Kraken MCP market tools for any raw quotes. Always state the discount/premium to par
> and the real yield. Never place anything outside futures paper.

## 3. Things to ask it

- "Is STRCx cheap right now?" → `desk scan`
- "If I park $2,000 in STRCx for 6 months, what do I get?" → `desk holdsim --amount 2000 --months 6`
- "Risk-on or risk-off between MSTRx and STRCx?" → `desk rv`
- "I'm long $5k MSTRx — hedge the BTC swing." → `desk hedge --pair MSTRx/USD --notional 5000 --execute`

## Why this is a real agent, not a script

Each tool emits `--json`, so the agent chains them: scan → if discount and risk-off,
size a position → hedge the BTC beta in futures paper → explain the carry and the
residual risk in one breath. All verifiable, all keyless.

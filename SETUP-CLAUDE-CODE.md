# Go live with Claude Code — step by step

Goal: get the STRCx Yield Desk running on your machine *and* published as a public
GitHub repo, driven by Claude Code so you mostly supervise rather than type.

You drive Claude Code in plain language. Lines in **"quotes"** are prompts you paste
into Claude Code; lines in `code` are commands you run in a terminal yourself.

## Prerequisites
- Node.js (for Claude Code).
- A GitHub account.
- macOS or Linux. On Windows, run the Kraken binary inside WSL (Claude Code itself
  works on Windows; the `kraken` binary does not run natively).

## Phase 1 — Install Claude Code
```
npm install -g @anthropic-ai/claude-code
claude --version
```
Docs / alternative installers: https://docs.claude.com/en/docs/claude-code/overview
**Done when:** `claude --version` prints a version.

## Phase 2 — Let Claude Code install everything
Put `strcx-yield-desk.zip` in `~/Downloads`, make an empty folder, open Claude Code
there (`claude`), then paste:

> "Install the Kraken CLI using the official installer from github.com/krakenfx/kraken-cli.
>  Then unzip ~/Downloads/strcx-yield-desk.zip into this folder. Run
>  `python3 desk.py --mock demo` and `python3 tests/test_analytics.py` and show me the output."

Claude Code runs the steps and asks permission for system actions.
**Done when:** you see the 3-part demo and `11/11 tests passed`. (This proves the code
works, with no keys and no network.)

## Phase 3 — Verify against real Kraken data (still keyless)
> "Run `bash scripts/keyless-probe.sh`, then
>  `kraken ticker STRCx/USD --asset-class tokenized_asset -o json`. Confirm STRCx comes
>  back with a price. If the JSON field names differ from what `extract_last_price()` in
>  kraken_client.py expects, adjust only that function to match, then run `python3 desk.py scan`."

**Done when:** `python3 desk.py scan` shows a live STRCx price, discount/premium to par,
and yield — drawn from the Kraken CLI, no keys.

## Phase 4 — Wire the agent layer (MCP)
```
claude mcp add --transport stdio kraken -- kraken mcp -s market,paper,futures
```
Then inside Claude Code: `/mcp` to confirm "kraken" is connected. Now ask in plain
language: *"Is STRCx cheap right now?"*, *"Hedge a $5k MSTRx position in futures paper."*
Claude Code uses the kraken MCP tools for raw data and runs `desk.py` for the analytics.
**Done when:** `/mcp` lists `kraken` and the agent answers those questions.

## Phase 5 — Publish it live on GitHub
Authenticate once, then create + push in one command:
```
gh auth login
gh repo create strcx-yield-desk --public --source=. --remote=origin --push
```
No `gh`? Create an empty repo in the browser, then:
```
git init && git add -A && git commit -m "STRCx Yield Desk"
git branch -M main
git remote add origin https://github.com/<your-username>/strcx-yield-desk.git
git push -u origin main
```
**Done when:** the repo opens in your browser with all files and the README rendered.

## Phase 6 — Record and submit
Follow `DEMO.md` (~2.5 min). Record the keyless demo, the live `scan`, and the MCP agent
answering a question. Confirm the contest is still open before submitting.
**Done when:** repo is public + demo recorded.

## If something breaks
Tell Claude Code the exact error and ask it to fix that one thing. The most likely
snags: `kraken` not on PATH (restart shell), the ticker JSON shape differing (Phase 3
fix), or `gh` not authenticated (`gh auth login`).

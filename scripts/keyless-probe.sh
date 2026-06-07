#!/usr/bin/env bash
#
# kraken-cli-paper-probe.sh
# Keyless probe voor de STRCx Yield Desk.
#
# Installeert (indien nodig) de Kraken CLI en test in EEN run wat de
# paper-engine wel/niet slikt. Geen API-keys, geen account, geen echt geld.
# Er wordt nergens een order op de live exchange geplaatst — alleen publieke
# market-data en de lokale paper-engines.
#
# Draaien:  bash kraken-cli-paper-probe.sh
#
# Tip: heb je `jq` geinstalleerd, dan wordt de JSON netjes geprint.
#      (macOS: brew install jq | Debian/Ubuntu: apt install jq)

set -uo pipefail   # bewust GEEN 'set -e': we willen juist door failures heen kijken

# ---- helpers ---------------------------------------------------------------
HAVE_JQ=0; command -v jq >/dev/null 2>&1 && HAVE_JQ=1

line()     { printf '%s\n' "------------------------------------------------------------"; }
info()     { printf '[INFO] %s\n' "$*"; }
test_hdr() { line; printf '[TEST] %s\n' "$*"; }

# Draait een commando, toont het, print de output (mooi met jq) en meldt PASS/FAIL
# op basis van de exit code. Stopt het script nooit.
run() {
  local desc="$1"; shift
  test_hdr "$desc"
  printf '$ %s\n' "$*"
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$HAVE_JQ" -eq 1 ]; then printf '%s\n' "$out" | jq . 2>/dev/null || printf '%s\n' "$out"
  else printf '%s\n' "$out"; fi
  if [ "$rc" -eq 0 ]; then printf '[PASS] exit=0\n'; else printf '[FAIL] exit=%s\n' "$rc"; fi
  return "$rc"
}

# ---- 0. Install ------------------------------------------------------------
line; info "Stap 0 — Kraken CLI aanwezig?"
if ! command -v kraken >/dev/null 2>&1; then
  info "Niet gevonden. Installeren via de officiele one-liner..."
  curl --proto '=https' --tlsv1.2 -LsSf \
    https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh
  hash -r 2>/dev/null || true
  if ! command -v kraken >/dev/null 2>&1; then
    info "kraken staat nog niet op je PATH. Herstart je shell of voeg de install-dir toe aan PATH."
    info "macOS blokkeert de binary? -> xattr -d com.apple.quarantine \"\$(command -v kraken)\""
    exit 1
  fi
fi
info "Versie: $(kraken --version 2>/dev/null || echo onbekend)"

# ---- 1. Sanity (publiek, geen keys) ----------------------------------------
run "Status van het systeem"                 kraken status -o json
run "Controle-ticker BTCUSD (moet slagen)"   kraken ticker BTCUSD -o json

# ---- 2. Bestaat STRCx / MSTRx als tokenized pair? --------------------------
test_hdr "Zoeken naar STRCx / MSTRx in de tokenized pairs"
printf '$ kraken pairs --asset-class tokenized_asset -o json | grep -i "STRC|MSTR"\n'
PAIRS_OUT="$(kraken pairs --asset-class tokenized_asset -o json 2>&1)"
STRCX_LISTED=no; MSTRX_LISTED=no
printf '%s' "$PAIRS_OUT" | grep -iq 'STRC' && STRCX_LISTED=yes
printf '%s' "$PAIRS_OUT" | grep -iq 'MSTR' && MSTRX_LISTED=yes
printf '%s\n' "$PAIRS_OUT" | grep -i 'STRC\|MSTR' || info "Geen STRC/MSTR-match in de pairs-output."
printf '[RESULT] STRCx gelist: %s | MSTRx gelist: %s\n' "$STRCX_LISTED" "$MSTRX_LISTED"

run "Ticker STRCx/USD (tokenized)"  kraken ticker STRCx/USD --asset-class tokenized_asset -o json
run "Asset-info STRCx (zoek naar multiplier/rebase-velden)" \
    kraken assets --asset STRCx --asset-class tokenized_asset -o json

# ---- 3. Spot paper ---------------------------------------------------------
run "Spot paper init (USD 10.000)"            kraken paper init --balance 10000 --currency USD -o json
run "Spot paper buy BTCUSD (controle)"        kraken paper buy BTCUSD 0.01 -o json

test_hdr "Spot paper buy STRCx/USD (tokenized) — DE bepalende test"
printf '$ kraken paper buy STRCx/USD 1 --asset-class tokenized_asset -o json\n'
PAPER_TOK_OUT="$(kraken paper buy STRCx/USD 1 --asset-class tokenized_asset -o json 2>&1)"; PAPER_TOK_RC=$?
if [ "$HAVE_JQ" -eq 1 ]; then printf '%s\n' "$PAPER_TOK_OUT" | jq . 2>/dev/null || printf '%s\n' "$PAPER_TOK_OUT"
else printf '%s\n' "$PAPER_TOK_OUT"; fi
PAPER_TOKENIZED=no; [ "$PAPER_TOK_RC" -eq 0 ] && PAPER_TOKENIZED=yes
printf '[RESULT] paper slikt tokenized_asset: %s (exit=%s)\n' "$PAPER_TOKENIZED" "$PAPER_TOK_RC"

run "Spot paper status"   kraken paper status -o json
run "Spot paper history"  kraken paper history -o json

# ---- 4. Futures paper (BTC-hedge leg, werkt sowieso keyless) ---------------
run "Futures paper init (USD 10.000)"             kraken futures paper init --balance 10000 --currency USD -o json
run "Futures paper LONG PF_XBTUSD 1 @5x"          kraken futures paper buy  PF_XBTUSD 1 --leverage 5 --type market -o json
run "Futures paper SHORT PF_XBTUSD 1 @5x (hedge)" kraken futures paper sell PF_XBTUSD 1 --leverage 5 --type market -o json
run "Futures paper positions"                     kraken futures paper positions -o json
run "Futures paper status"                        kraken futures paper status -o json

# ---- 5. Eindoordeel --------------------------------------------------------
line
printf '================ SAMENVATTING ================\n'
printf 'STRCx gelist als tokenized pair : %s\n' "$STRCX_LISTED"
printf 'MSTRx gelist als tokenized pair : %s\n' "$MSTRX_LISTED"
printf 'Spot paper accepteert STRCx     : %s\n' "$PAPER_TOKENIZED"
printf 'Futures paper (BTC-hedge)       : werkt keyless (zie tests hierboven)\n'
line
if [ "$STRCX_LISTED" = yes ] && [ "$PAPER_TOKENIZED" = yes ]; then
  printf 'ROUTE: volledige keyless demo mogelijk — Agent 1 + 2 in spot paper, Agent 3 in futures paper.\n'
elif [ "$STRCX_LISTED" = yes ] && [ "$PAPER_TOKENIZED" = no ]; then
  printf 'ROUTE: STRCx bestaat, maar paper slikt geen tokenized_asset.\n'
  printf '       -> Multiplier read-only tonen (keys + STRCx-positie), hedge in futures paper, sweep live-only.\n'
else
  printf 'ROUTE: STRCx niet gevonden via de CLI. Verschuif zwaartepunt naar de read-only\n'
  printf '       multiplier-analyse + BTC futures-paper hedge; verifieer de exacte pair-naam handmatig.\n'
fi
line

# ---- 6. Later, MET keys: de multiplier zelf (NIET in deze keyless run) -----
# Dit is het hart van Agent 1. Draai dit pas als je keys + een STRCx-positie hebt:
#
#   export KRAKEN_API_KEY=...; export KRAKEN_API_SECRET=...
#   kraken balance --rebase-multiplier rebased -o json   # saldo NA multiplier
#   kraken balance --rebase-multiplier base    -o json   # saldo VOOR multiplier
#   kraken ledgers --asset STRCx -o json                 # accrual-historie
#
# rebased / base = cumulatieve multiplier; de dagelijkse delta = je effectieve yield.

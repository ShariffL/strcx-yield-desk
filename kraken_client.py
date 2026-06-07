"""
kraken_client.py — thin wrapper around the `kraken` CLI binary.

Design goals:
- Real path: shells out to `kraken <args> -o json` and parses the result.
- Mock path (--mock): loads canned JSON from mock_data/ so the whole desk runs
  with no binary, no keys, no network. This is what lets a judge run it cold.
- Tolerant extraction: the exact field names of `kraken ticker -o json` are
  confirmed on first run; extract_last_price() tries the likely shapes
  (Kraken REST mirrors: result[pair].c[0]) and falls back gracefully.

Nothing here needs API keys: ticker/ohlc are public market data, and the
futures-paper engine is a local simulator.
"""

from __future__ import annotations
import json
import os
import shutil
import subprocess

MOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data")


class KrakenError(RuntimeError):
    pass


def _load_mock(name: str) -> dict:
    path = os.path.join(MOCK_DIR, name)
    with open(path, "r") as f:
        return json.load(f)


def run_kraken(args: list[str], mock_file: str | None = None, mock: bool = False) -> dict:
    """
    Run `kraken <args> -o json` and return parsed JSON.
    In mock mode, return the canned file instead.
    """
    if mock:
        if not mock_file:
            raise KrakenError("mock mode requires a mock_file")
        return _load_mock(mock_file)

    if shutil.which("kraken") is None:
        raise KrakenError(
            "kraken binary not found on PATH. Install it (see README) or run with --mock."
        )
    cmd = ["kraken", *args, "-o", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise KrakenError(
            f"`{' '.join(cmd)}` failed (exit {proc.returncode}): {proc.stderr or proc.stdout}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise KrakenError(f"could not parse JSON from kraken: {e}\nraw: {proc.stdout[:500]}")


def extract_last_price(payload: dict) -> float:
    """
    Pull the last traded price out of a ticker payload, tolerant to schema.
    Tries, in order: result[pair].c[0]  ->  top-level last/price/c.
    Confirm the real shape once with: kraken ticker STRCx/USD --asset-class tokenized_asset -o json
    """
    # Kraken-REST-style nesting: {"result": {"STRCXUSD": {"c": ["97.44", "1.0"], ...}}}
    res = payload.get("result", payload)
    if isinstance(res, dict):
        for v in res.values():
            if isinstance(v, dict):
                c = v.get("c") or v.get("last") or v.get("price")
                if isinstance(c, (list, tuple)) and c:
                    return float(c[0])
                if isinstance(c, (str, int, float)):
                    return float(c)
    # Flat fallbacks
    for key in ("last", "price", "lastPrice"):
        if key in payload:
            return float(payload[key])
    c = payload.get("c")
    if isinstance(c, (list, tuple)) and c:
        return float(c[0])
    raise KrakenError(f"could not find a price field in payload: {json.dumps(payload)[:300]}")


def extract_ohlc_series(payload: dict) -> list[tuple[int, float]]:
    """
    Pull (timestamp, close) pairs from an OHLC payload, tolerant to schema,
    sorted by timestamp. Kraken-REST OHLC rows look like
    [time, open, high, low, close, vwap, vol, count].
    """
    res = payload.get("result", payload)
    rows = None
    if isinstance(res, dict):
        for k, v in res.items():
            if isinstance(v, list) and v and isinstance(v[0], (list, tuple)):
                rows = v
                break
    elif isinstance(res, list):
        rows = res
    if not rows:
        raise KrakenError("could not find OHLC rows in payload")
    out: list[tuple[int, float]] = []
    for row in rows:
        try:
            ts = int(float(row[0]))
            close = float(row[4])           # close is index 4 in Kraken REST OHLC
        except (IndexError, ValueError, TypeError):
            nums = [float(x) for x in row if _is_num(x)]
            if len(nums) >= 2:
                ts, close = int(nums[0]), nums[-1]
            else:
                continue
        out.append((ts, close))
    out.sort(key=lambda p: p[0])
    return out


def extract_closes(payload: dict) -> list[float]:
    """List of close prices (chronological). Built on extract_ohlc_series."""
    return [c for _, c in extract_ohlc_series(payload)]


def _is_num(x) -> bool:
    try:
        float(x)
        return True
    except (ValueError, TypeError):
        return False


# --- convenience calls -----------------------------------------------------
def ticker(pair: str, asset_class: str | None = None, mock: bool = False,
           mock_file: str | None = None) -> dict:
    args = ["ticker", pair]
    if asset_class:
        args += ["--asset-class", asset_class]
    return run_kraken(args, mock_file=mock_file, mock=mock)


def ohlc(pair: str, interval: int = 1440, asset_class: str | None = None,
         mock: bool = False, mock_file: str | None = None) -> dict:
    args = ["ohlc", pair, "--interval", str(interval)]
    if asset_class:
        args += ["--asset-class", asset_class]
    return run_kraken(args, mock_file=mock_file, mock=mock)

"""
analytics.py — pure, dependency-free math for the STRCx Yield Desk.

Everything here is a plain function over numbers so it can be unit-tested and
reasoned about. No network, no Kraken calls. The Kraken CLI feeds the numbers
(see kraken_client.py); this module turns them into decisions.

Why this matters: STRCx is a *tokenised preferred* that should sit near $100
par, with its dividend accruing via a daily rebase multiplier. So the right
lens is fixed income (yield, premium/discount to par), not "number go up".
"""

from __future__ import annotations
from statistics import mean


# ---------------------------------------------------------------------------
# Par / yield lens
# ---------------------------------------------------------------------------
def pct_to_par(price: float, par: float = 100.0) -> float:
    """Premium(+)/discount(-) to par, in percent. -2.5 means 2.5% under par."""
    return (price / par - 1.0) * 100.0


def current_yield(price: float, annual_rate: float, par: float = 100.0) -> float:
    """
    Current (running) yield in percent.

    A preferred pays a dividend on *par*, not on market price. STRC's variable
    coupon is quoted as an annual rate on the $100 par. So the yield you
    actually earn at today's price is (par * rate) / price.

    annual_rate is a fraction, e.g. 0.09 for 9%.
    """
    if price <= 0:
        raise ValueError("price must be positive")
    return (par * annual_rate) / price * 100.0


def pull_to_par_pct(price: float, par: float = 100.0) -> float:
    """
    One-off return if price reverts to par from here, in percent.
    Positive when trading at a discount (upside to par).
    """
    return (par / price - 1.0) * 100.0


def hold_simulation(
    amount: float,
    price: float,
    annual_rate: float,
    months: int,
    par: float = 100.0,
) -> dict:
    """
    "If I hold <amount> for <months>..." simulator.

    Models the dividend as the daily rebase multiplier does it: the token
    *balance* grows over time (rather than paying cash). We compound monthly
    at annual_rate/12. Price is assumed flat unless you also look at the
    'value_if_pull_to_par' scenario.

    amount is in the same currency as price (STRCx trades in USD).
    annual_rate is net-of-withholding, as the on-chain multiplier already is.

    Returns a dict of scenarios. All assumptions are explicit on purpose —
    this is a planning tool, not a promise.
    """
    if months < 0:
        raise ValueError("months must be >= 0")
    tokens0 = amount / price
    growth = (1.0 + annual_rate / 12.0) ** months
    tokens1 = tokens0 * growth
    yield_tokens = tokens1 - tokens0
    return {
        "input_amount": round(amount, 2),
        "entry_price": round(price, 4),
        "tokens_start": round(tokens0, 6),
        "tokens_end": round(tokens1, 6),
        "yield_tokens": round(yield_tokens, 6),
        "yield_pct": round((growth - 1.0) * 100.0, 4),
        "value_if_price_flat": round(tokens1 * price, 2),
        "value_if_pull_to_par": round(tokens1 * par, 2),
        "assumptions": {
            "annual_rate": annual_rate,
            "compounding": "monthly via rebase multiplier",
            "price_path": "flat (see pull_to_par scenario for reversion)",
            "fx": "amount in USD; ignores USD/EUR moves",
        },
    }


# ---------------------------------------------------------------------------
# BTC-beta hedge
# ---------------------------------------------------------------------------
def returns_from_closes(closes: list[float]) -> list[float]:
    """Simple period-over-period returns from a list of close prices."""
    out = []
    for prev, cur in zip(closes, closes[1:]):
        if prev:
            out.append(cur / prev - 1.0)
    return out


def beta(asset_returns: list[float], btc_returns: list[float]) -> float:
    """
    Beta of an asset to BTC = cov(asset, btc) / var(btc).

    Uses overlapping observations. Returns 0.0 if there is not enough data or
    BTC has no variance (caller should fall back to a default assumption).
    """
    n = min(len(asset_returns), len(btc_returns))
    if n < 3:
        return 0.0
    a = asset_returns[-n:]
    b = btc_returns[-n:]
    ma, mb = mean(a), mean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (n - 1)
    var = sum((y - mb) ** 2 for y in b) / (n - 1)
    if var == 0:
        return 0.0
    return cov / var


def hedge_btc_notional(position_notional: float, asset_beta: float) -> float:
    """
    USD notional of BTC to SHORT to neutralise the BTC component of a long
    position. Just notional * beta. Convert to contracts per Kraken's PF_XBTUSD
    spec at execution time.
    """
    return position_notional * asset_beta


# ---------------------------------------------------------------------------
# MSTRx <-> STRCx relative-value (risk-on / risk-off)
# ---------------------------------------------------------------------------
def rv_ratio(mstrx_price: float, strcx_price: float) -> float:
    """Ratio of the volatile common to the stable preferred."""
    if strcx_price <= 0:
        raise ValueError("strcx_price must be positive")
    return mstrx_price / strcx_price


def zscore(value: float, series: list[float]) -> float:
    """Z-score of value against a reference series. 0.0 if series too short."""
    if len(series) < 2:
        return 0.0
    m = mean(series)
    var = sum((x - m) ** 2 for x in series) / (len(series) - 1)
    sd = var ** 0.5
    if sd == 0:
        return 0.0
    return (value - m) / sd


def rv_signal(
    mstrx_price: float,
    strcx_price: float,
    ratio_history: list[float] | None = None,
    z_threshold: float = 1.0,
) -> dict:
    """
    Risk-on/off signal from the MSTRx/STRCx ratio.

    High ratio vs its own history => the common is rich relative to the
    preferred => tilt toward STRCx (de-risk). Low ratio => risk-on (MSTRx).
    """
    ratio = rv_ratio(mstrx_price, strcx_price)
    hist = ratio_history or []
    z = zscore(ratio, hist)
    r_mean = round(mean(hist), 4) if hist else None
    r_sd = round((sum((x - mean(hist)) ** 2 for x in hist) / (len(hist) - 1)) ** 0.5, 4) if len(hist) > 1 else None
    if z >= z_threshold:
        signal = "TILT_STRCX"      # de-risk: common looks expensive
    elif z <= -z_threshold:
        signal = "TILT_MSTRX"      # risk-on: common looks cheap
    else:
        signal = "NEUTRAL"
    return {
        "ratio": round(ratio, 4),
        "ratio_mean": r_mean,
        "ratio_sd": r_sd,
        "zscore": round(z, 3),
        "n_obs": len(hist),
        "signal": signal,
        "reading": {
            "TILT_STRCX": "Common rich vs preferred -> de-risk toward STRCx.",
            "TILT_MSTRX": "Common cheap vs preferred -> risk-on toward MSTRx.",
            "NEUTRAL": "No strong relative-value edge right now.",
        }[signal],
    }


# ---------------------------------------------------------------------------
# Timestamp alignment + estimate quality (added for robust beta / RV)
# ---------------------------------------------------------------------------
def align_on_timestamp(a: list[tuple[int, float]],
                       b: list[tuple[int, float]]) -> tuple[list[float], list[float]]:
    """
    Align two (timestamp, value) series on their common timestamps.

    Beta and the RV ratio are only meaningful when the two legs are compared
    over the *same* moments. Zipping by position silently corrupts the estimate
    when the series differ in length or start. This intersects on timestamp and
    returns two value-lists in matching, time-sorted order.
    """
    da = dict(a)
    db = dict(b)
    common = sorted(set(da) & set(db))
    return [da[t] for t in common], [db[t] for t in common]


def pearson_r(x: list[float], y: list[float]) -> float:
    """Pearson correlation over overlapping observations. 0.0 if degenerate."""
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    x, y = x[-n:], y[-n:]
    mx, my = mean(x), mean(y)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sxx = sum((xi - mx) ** 2 for xi in x)
    syy = sum((yi - my) ** 2 for yi in y)
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / ((sxx * syy) ** 0.5)


def beta_with_quality(asset_returns: list[float], btc_returns: list[float]) -> dict:
    """
    Beta plus the quality of the fit, so the desk can be honest about how much
    to trust it. r2 near 0 means BTC explains little of this asset's moves
    (expected for the low-beta preferred) -> treat beta as indicative.
    """
    b = beta(asset_returns, btc_returns)
    r = pearson_r(asset_returns, btc_returns)
    n = min(len(asset_returns), len(btc_returns))
    return {"beta": b, "corr": r, "r2": r * r, "n": n}

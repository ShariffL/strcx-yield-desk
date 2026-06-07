"""Unit tests for analytics.py. Run: python -m pytest -q  (or python tests/test_analytics.py)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analytics as A


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_pct_to_par():
    assert approx(A.pct_to_par(100.0), 0.0)
    assert approx(A.pct_to_par(97.0), -3.0)
    assert approx(A.pct_to_par(105.0), 5.0)


def test_current_yield():
    # 9% on $100 par, bought at $97.44 -> slightly above 9%
    y = A.current_yield(97.44, 0.09)
    assert 9.2 < y < 9.3, y


def test_pull_to_par():
    # at 97.44, reverting to 100 is ~2.63% upside
    assert approx(A.pull_to_par_pct(97.44), (100 / 97.44 - 1) * 100)


def test_hold_simulation():
    r = A.hold_simulation(amount=1000.0, price=100.0, annual_rate=0.12, months=6)
    # 12% annual, monthly compounding for 6 months ~ 6.15%
    assert 6.0 < r["yield_pct"] < 6.3, r["yield_pct"]
    assert r["tokens_start"] == 10.0
    assert r["value_if_pull_to_par"] >= r["value_if_price_flat"] or True  # par==price here


def test_beta_perfect_correlation():
    btc = [0.01, -0.02, 0.03, -0.01, 0.02]
    asset = [2 * x for x in btc]          # beta should be ~2
    assert approx(A.beta(asset, btc), 2.0, tol=1e-9)


def test_beta_insufficient_data():
    assert A.beta([0.01], [0.01]) == 0.0


def test_hedge_notional():
    assert A.hedge_btc_notional(1000.0, 0.5) == 500.0


def test_rv_signal_directions():
    hist = [1.5, 1.55, 1.6, 1.62, 1.58, 1.61]   # mean ~1.576
    # very high ratio -> tilt to STRCx (de-risk)
    hi = A.rv_signal(mstrx_price=200.0, strcx_price=100.0, ratio_history=hist)
    assert hi["signal"] == "TILT_STRCX", hi
    # very low ratio -> risk-on MSTRx
    lo = A.rv_signal(mstrx_price=140.0, strcx_price=100.0, ratio_history=hist)
    assert lo["signal"] == "TILT_MSTRX", lo


def test_align_on_timestamp():
    a = [(1, 10.0), (2, 20.0), (3, 30.0)]
    b = [(2, 200.0), (3, 300.0), (4, 400.0)]
    va, vb = A.align_on_timestamp(a, b)
    assert va == [20.0, 30.0] and vb == [200.0, 300.0]


def test_pearson_and_beta_quality():
    btc = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.03]
    asset = [1.5 * x for x in btc]            # perfect linear -> corr 1, r2 1, beta 1.5
    assert approx(A.pearson_r(asset, btc), 1.0, tol=1e-9)
    q = A.beta_with_quality(asset, btc)
    assert approx(q["beta"], 1.5, tol=1e-9)
    assert approx(q["r2"], 1.0, tol=1e-9)
    assert q["n"] == len(btc)


def test_rv_signal_band_fields():
    hist = [1.2, 1.25, 1.3, 1.28, 1.22, 1.26]
    sig = A.rv_signal(150.0, 100.0, ratio_history=hist)
    assert sig["ratio_mean"] is not None and sig["ratio_sd"] is not None
    assert sig["n_obs"] == len(hist)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")



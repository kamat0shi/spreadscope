import math
from backend.services.spreads import calculate_spreads


def test_calculate_spreads_basic_two_exchanges():
    prices = {
        "gate": {
            "BTC_USDT": {"fair": 100.0, "ts": 1},
        },
        "mexc": {
            "BTC_USDT": {"fair": 103.0, "ts": 2},
        },
    }

    out = calculate_spreads(prices)
    assert len(out) == 1

    r = out[0]
    assert r["symbol"] == "BTC_USDT"
    assert r["low_exchange"] == "gate"
    assert r["high_exchange"] == "mexc"
    assert math.isclose(r["low_price"], 100.0, rel_tol=1e-9)
    assert math.isclose(r["high_price"], 103.0, rel_tol=1e-9)
    assert math.isclose(r["spread_abs"], 3.0, rel_tol=1e-9)
    assert math.isclose(r["spread_pct"], 3.0, rel_tol=1e-9)  # 3 / 100 * 100


def test_calculate_spreads_ignores_single_exchange_symbol():
    prices = {
        "gate": {"ETH_USDT": {"fair": 2000.0, "ts": 1}},
        "mexc": {},
    }
    out = calculate_spreads(prices)
    assert out == []


def test_calculate_spreads_uses_last_when_fair_missing():
    prices = {
        "gate": {"BTC_USDT": {"last": 100.0, "ts": 1}},
        "mexc": {"BTC_USDT": {"last": 101.0, "ts": 2}},
    }
    out = calculate_spreads(prices)
    assert len(out) == 1
    assert out[0]["spread_abs"] == 1.0


def test_calculate_spreads_uses_mid_when_only_bid_ask():
    prices = {
        "gate": {"BTC_USDT": {"bid": 99.0, "ask": 101.0, "ts": 1}},  # mid=100
        "mexc": {"BTC_USDT": {"bid": 100.0, "ask": 104.0, "ts": 2}}, # mid=102
    }
    out = calculate_spreads(prices)
    assert len(out) == 1
    assert out[0]["low_price"] == 100.0
    assert out[0]["high_price"] == 102.0
    assert out[0]["spread_abs"] == 2.0


def test_calculate_spreads_skips_invalid_prices():
    prices = {
        "gate": {"BTC_USDT": {"fair": None, "ts": 1}},
        "mexc": {"BTC_USDT": {"fair": 0, "ts": 2}},  # <=0 invalid
        "ourbit": {"BTC_USDT": {"fair": 105.0, "ts": 3}},
    }
    out = calculate_spreads(prices)
    # сравнить не с кем, т.к. только одна валидная биржа
    assert out == []


def test_calculate_spreads_exchange_filter():
    prices = {
        "gate": {"BTC_USDT": {"fair": 100.0, "ts": 1}},
        "mexc": {"BTC_USDT": {"fair": 110.0, "ts": 2}},
        "ourbit": {"BTC_USDT": {"fair": 90.0, "ts": 3}},
    }
    out = calculate_spreads(prices, exchanges_filter=["gate", "mexc"])
    assert len(out) == 1
    assert out[0]["low_exchange"] == "gate"
    assert out[0]["high_exchange"] == "mexc"
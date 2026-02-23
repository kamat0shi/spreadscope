# exchanges.py
import time
from typing import Dict, Any, List, Optional, Tuple

# ---- нормализация для UI ----
def normalize_record(
    exchange: str,
    symbol: str,
    last: float,
    bid: Optional[float],
    ask: Optional[float],
    fair: Optional[float],
    ts: int,
    meta: Dict[str, Any]
) -> Dict[str, Any]:
    # берём max_size из разных мета-полей
    max_size = None
    if exchange == "gate":
        # gate meta: order_size_max
        max_size = meta.get("order_size_max")
    else:
        # mexc/ourbit meta: maxVol
        max_size = meta.get("maxVol")

    return {
        "exchange": exchange,
        "symbol": symbol,
        "last": last,
        "bid": bid,
        "ask": ask,
        "fair": fair,
        "ts": ts,
        "max_size": max_size
    }

# ---- парсеры ответа ----
def rest_parse_mexc_like(it: Dict[str, Any], now_ms: int):
    sym  = it.get("symbol")
    last = it.get("lastPrice") or it.get("lastprice")
    bid  = it.get("bid1")
    ask  = it.get("ask1")
    fair = it.get("fairPrice")
    ts   = it.get("timestamp") or now_ms
    if not sym or last is None:
        return None
    try:
        last = float(last)
        bid  = float(bid) if bid is not None else None
        ask  = float(ask) if ask is not None else None
        fair = float(fair) if fair is not None else None
    except Exception:
        return None
    return str(sym), last, bid, ask, fair, int(ts)

def meta_sym_mexc_like(d: Dict[str, Any]) -> Optional[str]:
    s = d.get("symbol")
    return str(s) if s else None

def meta_payload_mexc_like(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "priceUnit":     d.get("priceUnit"),
        "volUnit":       d.get("volUnit"),
        "contractSize":  d.get("contractSize"),
        "priceScale":    d.get("priceScale"),
        "volScale":      d.get("volScale"),
        "minVol":        d.get("minVol"),
        "maxVol":        d.get("maxVol"),
        "maxLeverage":   d.get("maxLeverage"),
        "amountScale":   d.get("amountScale"),
        "makerFeeRate":  d.get("makerFeeRate"),
        "takerFeeRate":  d.get("takerFeeRate"),
        "settleCoin":    d.get("settleCoin"),
    }

def rest_parse_gate(it: Dict[str, Any], now_ms: int):
    sym  = it.get("contract")
    last = it.get("last")
    bid  = it.get("highest_bid")
    ask  = it.get("lowest_ask")
    fair = it.get("mark_price")
    if not sym or last is None:
        return None
    try:
        last = float(last)
        bid  = float(bid)  if bid  not in (None, "") else None
        ask  = float(ask)  if ask  not in (None, "") else None
        fair = float(fair) if fair not in (None, "") else None
    except Exception:
        return None
    return str(sym), last, bid, ask, fair, now_ms

def meta_sym_gate(d: Dict[str, Any]) -> Optional[str]:
    s = d.get("name")
    return str(s) if s else None

def meta_payload_gate(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "order_price_round":  d.get("order_price_round"),
        "mark_price_round":   d.get("mark_price_round"),
        "order_size_min":     d.get("order_size_min"),
        "order_size_max":     d.get("order_size_max"),
        "maker_fee_rate":     d.get("maker_fee_rate"),
        "taker_fee_rate":     d.get("taker_fee_rate"),
        "quanto_multiplier":  d.get("quanto_multiplier"),
        "size":               d.get("size"),
        "leverage_min":       d.get("leverage_min"),
        "leverage_max":       d.get("leverage_max"),
        "maintenance_rate":   d.get("maintenance_rate"),
        "funding_interval":   d.get("funding_interval"),
        "funding_rate_limit": d.get("funding_rate_limit"),
        "spread_protect_rate":d.get("spread_protect_rate"),
        "status":             d.get("status"),
    }

# описание поддерживаемых бирж (URLы)
EXCH_DEF: Dict[str, Dict[str, Any]] = {
    "gate": {
        "tickers": "https://api.gateio.ws/api/v4/futures/usdt/tickers",
        "meta":    "https://api.gateio.ws/api/v4/futures/usdt/contracts",
        "rest_parse": rest_parse_gate,
        "meta_sym":   meta_sym_gate,
        "meta_payload": meta_payload_gate,
    },
    "mexc": {
        "tickers": "https://futures.mexc.com/api/v1/contract/ticker?",
        "meta":    "https://contract.mexc.com/api/v1/contract/detail",
        "rest_parse": rest_parse_mexc_like,
        "meta_sym":   meta_sym_mexc_like,
        "meta_payload": meta_payload_mexc_like,
    },
    "ourbit": {
        "tickers": "https://futures.ourbit.com/api/v1/contract/ticker",
        "meta":    "https://futures.ourbit.com/api/v1/contract/detail",
        "rest_parse": rest_parse_mexc_like,
        "meta_sym":   meta_sym_mexc_like,
        "meta_payload": meta_payload_mexc_like,
    }
}

from typing import Dict, Any, List, Tuple, Optional


def _price_for_compare(p: Dict[str, Any]) -> Optional[float]:
    """
    Приоритет цены для сравнения:
    fair -> last -> mid(bid/ask)
    """
    fair = p.get("fair")
    if isinstance(fair, (int, float)):
        return float(fair)

    last = p.get("last")
    if isinstance(last, (int, float)):
        return float(last)

    bid = p.get("bid")
    ask = p.get("ask")
    if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) and bid > 0 and ask > 0:
        return (float(bid) + float(ask)) / 2.0

    return None


def calculate_spreads(
    prices_by_exchange: Dict[str, Dict[str, Dict[str, Any]]],
    only_symbol: Optional[str] = None,
    exchanges_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Строит список спредов между биржами по одинаковому symbol.
    Возвращает список записей, отсортированный по spread_pct (desc).
    """
    # symbol -> list[{exchange, price, ts, raw}]
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for exchange, symbols_map in prices_by_exchange.items():
        if exchanges_filter and exchange not in exchanges_filter:
            continue

        for symbol, p in symbols_map.items():
            if only_symbol and symbol != only_symbol:
                continue

            price = _price_for_compare(p)
            if price is None or price <= 0:
                continue

            grouped.setdefault(symbol, []).append(
                {
                    "exchange": exchange,
                    "price": float(price),
                    "ts": p.get("ts"),
                    "raw": p,
                }
            )

    result: List[Dict[str, Any]] = []

    for symbol, rows in grouped.items():
        # Нужны минимум 2 биржи для сравнения
        if len(rows) < 2:
            continue

        low = min(rows, key=lambda x: x["price"])
        high = max(rows, key=lambda x: x["price"])

        low_price = low["price"]
        high_price = high["price"]
        spread_abs = high_price - low_price
        if low_price <= 0:
            continue

        spread_pct = (spread_abs / low_price) * 100.0

        # пропускаем "нулевые" спреды (одна и та же цена)
        if spread_abs <= 0:
            continue

        result.append(
            {
                "symbol": symbol,
                "low_exchange": low["exchange"],
                "high_exchange": high["exchange"],
                "low_price": round(low_price, 8),
                "high_price": round(high_price, 8),
                "spread_abs": round(spread_abs, 8),
                "spread_pct": round(spread_pct, 4),
                "compared_exchanges": [r["exchange"] for r in sorted(rows, key=lambda x: x["exchange"])],
                "quotes_count": len(rows),
                "ts_min": min((r.get("ts") or 0) for r in rows),
                "ts_max": max((r.get("ts") or 0) for r in rows),
            }
        )

    result.sort(key=lambda x: x["spread_pct"], reverse=True)
    return result
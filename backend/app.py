# backend/app.py
import os
import json
import asyncio
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.exchanges import EXCH_DEF, normalize_record
from backend.services.spreads import calculate_spreads

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

EXCHANGES = (os.getenv("EXCHANGES") or "gate,mexc,ourbit").replace(" ", "").lower().split(",")
INTERVAL_MIN = float(os.getenv("INTERVAL_MIN", "0.6"))
INTERVAL_MAX = float(os.getenv("INTERVAL_MAX", "1.2"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))

app = FastAPI(title="SpreadScope API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для учебного MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- in-memory state -----
PRICES: Dict[str, Dict[str, Dict[str, Any]]] = {ex: {} for ex in EXCHANGES}
META: Dict[str, Dict[str, Dict[str, Any]]] = {ex: {} for ex in EXCHANGES}
SUBS: Dict[str, "set[WebSocket]"] = {ex: set() for ex in EXCHANGES}


# ---------- helpers ----------
async def fetch_json(session: aiohttp.ClientSession, url: str) -> Any:
    async with session.get(url) as r:
        r.raise_for_status()
        return await r.json(content_type=None)


def rows_from_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        d = data.get("data")
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            return [d]
    raise RuntimeError(f"Unexpected payload type: {type(data).__name__}")


def load_local_rates() -> Dict[str, Any]:
    """
    Локальные котировки/база конвертера (fallback).
    """
    path = DATA_DIR / "rates.json"
    if not path.exists():
        return {"base": "USD", "rates": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"base": "USD", "rates": {}}


def get_all_quotes_snapshot() -> List[Dict[str, Any]]:
    """
    Нормализованный снапшот всех котировок по всем биржам.
    """
    out: List[Dict[str, Any]] = []
    for exchange in EXCHANGES:
        meta_map = META.get(exchange, {})
        for sym, p in PRICES.get(exchange, {}).items():
            out.append(
                normalize_record(
                    exchange=exchange,
                    symbol=sym,
                    last=p.get("last"),
                    bid=p.get("bid"),
                    ask=p.get("ask"),
                    fair=p.get("fair"),
                    ts=p.get("ts"),
                    meta=meta_map.get(sym, {}),
                )
            )
    return out


async def broadcaster(exchange: str, msg: Dict[str, Any]):
    dead = []
    for ws in list(SUBS[exchange]):
        try:
            await ws.send_text(json.dumps(msg, separators=(",", ":")))
        except Exception:
            dead.append(ws)
    for ws in dead:
        SUBS[exchange].discard(ws)


# ---------- polling ----------
async def poll_exchange(exchange: str):
    """
    Фоновая задача: тянет тикеры и мету, и рассылает дельты WS-клиентам.
    """
    if exchange not in EXCH_DEF:
        return

    cfg = EXCH_DEF[exchange]
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)

    next_meta_at = time.time()
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": "SpreadScope/0.1"}) as session:
        while True:
            try:
                # тикеры
                tick = await fetch_json(session, cfg["tickers"])
                rows = rows_from_payload(tick)
                now_ms = int(time.time() * 1000)

                for it in rows:
                    parsed = cfg["rest_parse"](it, now_ms)
                    if not parsed:
                        continue

                    sym, last, bid, ask, fair, ts = parsed
                    PRICES[exchange][sym] = {
                        "last": last,
                        "bid": bid,
                        "ask": ask,
                        "fair": fair,
                        "ts": ts,
                    }

                    meta = META[exchange].get(sym, {})
                    await broadcaster(
                        exchange,
                        {
                            "type": "tick",
                            "record": normalize_record(exchange, sym, last, bid, ask, fair, ts, meta),
                        },
                    )

                # периодическая мета
                if time.time() >= next_meta_at:
                    try:
                        meta_payload = await fetch_json(session, cfg["meta"])
                        metas = rows_from_payload(meta_payload)
                        pushed = 0
                        for d in metas:
                            sym = cfg["meta_sym"](d)
                            if not sym:
                                continue
                            payload = cfg["meta_payload"](d)
                            META[exchange][sym] = payload
                            pushed += 1

                        await broadcaster(exchange, {"type": "meta_batch", "count": pushed})
                    finally:
                        next_meta_at = time.time() + random.uniform(5.0, 12.0)

                await asyncio.sleep(random.uniform(INTERVAL_MIN, INTERVAL_MAX))

            except Exception:
                # для MVP не падаем, а продолжаем polling
                await asyncio.sleep(1.0)


@app.on_event("startup")
async def on_start():
    for ex in EXCHANGES:
        if ex in EXCH_DEF:
            asyncio.create_task(poll_exchange(ex))


# ---------- API ----------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "exchanges_enabled": EXCHANGES,
        "quotes_cached": {ex: len(PRICES.get(ex, {})) for ex in EXCHANGES},
    }


@app.get("/api/quotes")
async def api_quotes(
    exchange: Optional[str] = Query(default=None, description="gate|mexc|ourbit"),
    symbol: Optional[str] = Query(default=None, description="exact symbol, e.g. BTC_USDT"),
    limit: int = Query(default=200, ge=1, le=2000),
):
    """
    Нормализованный список котировок.
    """
    snapshot = get_all_quotes_snapshot()

    if exchange:
        snapshot = [r for r in snapshot if r.get("exchange") == exchange]

    if symbol:
        snapshot = [r for r in snapshot if r.get("symbol") == symbol]

    snapshot.sort(key=lambda x: (x.get("exchange") or "", x.get("symbol") or ""))
    return {"count": min(len(snapshot), limit), "records": snapshot[:limit]}


@app.get("/api/spreads")
async def api_spreads(
    symbol: Optional[str] = Query(default=None, description="exact symbol"),
    exchanges: Optional[str] = Query(default=None, description="comma separated, e.g. gate,mexc"),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Считает спреды между биржами по одинаковым symbol на основе in-memory PRICES.
    """
    exchanges_filter = None
    if exchanges:
        exchanges_filter = [e.strip().lower() for e in exchanges.split(",") if e.strip()]

    spreads = calculate_spreads(
        prices_by_exchange=PRICES,
        only_symbol=symbol,
        exchanges_filter=exchanges_filter,
    )
    return {"count": min(len(spreads), limit), "records": spreads[:limit]}


@app.get("/api/converter/rates")
async def api_converter_rates():
    """
    Локальные rates для конвертера (MVP / fallback).
    Формат: {"base":"USD","rates":{"USD":1,"EUR":0.92,...}}
    """
    return load_local_rates()


# ---------- WS ----------
@app.websocket("/ws")
async def ws_prices(ws: WebSocket, exchange: str = Query(..., description="gate|mexc|ourbit")):
    if exchange not in EXCH_DEF:
        await ws.close(code=1008)
        return

    await ws.accept()
    SUBS[exchange].add(ws)

    try:
        snapshot = []
        meta_map = META[exchange]
        for sym, p in PRICES[exchange].items():
            snapshot.append(
                normalize_record(
                    exchange,
                    sym,
                    p.get("last"),
                    p.get("bid"),
                    p.get("ask"),
                    p.get("fair"),
                    p.get("ts"),
                    meta_map.get(sym, {}),
                )
            )

        await ws.send_text(json.dumps({"type": "snapshot", "records": snapshot}, separators=(",", ":")))

        while True:
            try:
                _ = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                await ws.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        pass
    finally:
        SUBS[exchange].discard(ws)


# ---------- Frontend static ----------
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(
        {
            "message": "SpreadScope API is running",
            "docs": "/docs",
            "health": "/health",
            "quotes": "/api/quotes",
            "spreads": "/api/spreads",
        }
    )
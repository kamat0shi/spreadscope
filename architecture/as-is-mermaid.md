```markdown
# As Is Architecture (SpreadScope Sprint 1 / MVP)
```

```mermaid
flowchart TB
    U[User / Browser] --> FE[frontend/index.html\nfrontend/app.js\nfrontend/style.css]

    FE -->|GET /api/spreads| APP[backend/app.py (FastAPI)]
    FE -->|GET /api/quotes| APP
    FE -->|GET /api/converter/rates| APP
    FE -->|GET /health| APP
    FE -->|WS /ws?exchange=...| APP

    APP --> EXCH[backend/exchanges.py\nEXCH_DEF + parsers + normalize_record]
    APP --> SPR[backend/services/spreads.py\ncalculate_spreads()]
    APP --> RATES[backend/data/rates.json]

    APP --> PRICES[(In-memory cache\nPRICES)]
    APP --> META[(In-memory cache\nMETA)]
    APP --> SUBS[(WS subscribers\nSUBS)]

    APP -->|polling via aiohttp| GATE[(Gate API)]
    APP -->|polling via aiohttp| MEXC[(MEXC API)]
    APP -->|polling via aiohttp| OURBIT[(Ourbit API)]
```

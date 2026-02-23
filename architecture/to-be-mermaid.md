# To Be Architecture (SpreadScope)

```mermaid
flowchart TB
    U["User / Browser"] --> FE["Frontend UI<br/>HTML/CSS/JS<br/>Spreads / Converter / Watchlist / History"]

    FE -->|REST API| API["Backend API (FastAPI)<br/>Controllers / Endpoints"]
    FE -->|WebSocket| WS["WS Endpoint / Live Stream"]

    API --> S1["Spread Calculation Service"]
    API --> S2["Converter Service"]
    API --> S3["Pair Normalization Service"]
    API --> S4["User Data Service (planned)"]

    WS --> QC[("In-memory Quote Cache")]

    S1 --> QC
    S1 --> NORM["Pair Mapping / Normalization Rules"]
    S2 --> LR["Local Rates JSON (MVP fallback)"]
    S2 --> QC

    API --> AUTH["Auth Module (planned)<br/>Firebase/Auth service or custom"]
    API --> DB[("SQLite / PostgreSQL<br/>users / watchlist / history / journal")]

    S4 --> DB
    AUTH --> DB

    POLL["Polling Worker / Exchange Fetcher (planned)"] --> AD1["Gate Adapter"]
    POLL --> AD2["MEXC Adapter"]
    POLL --> AD3["Ourbit Adapter"]

    AD1 --> EXT1[("Gate API")]
    AD2 --> EXT2[("MEXC API")]
    AD3 --> EXT3[("Ourbit API")]

    POLL --> QC
```

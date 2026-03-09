#!/usr/bin/env python3
"""
E-Commerce Analytics API
FastAPI + ClickHouse — read-only analytics layer over the events table.

Endpoints
─────────
GET /health                         liveness + CH connectivity check
GET /events                         paginated raw event log
GET /metrics/overview               KPIs: total events, CVR, revenue, AOV
GET /metrics/funnel                 view→click→cart→purchase counts + drop-off %
GET /metrics/timeseries             event counts bucketed by minute/hour/day
GET /metrics/top-products           top N products by views / purchases / revenue
GET /metrics/top-categories         aggregated stats per category
GET /metrics/users/{user_id}        single-user journey
GET /metrics/revenue                revenue over time + total
GET /metrics/realtime               last-60-seconds rolling window (for live dashboards)
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Literal, Optional
import clickhouse_connect
import os
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv()

CH_HOST     = os.getenv("CH_HOST",     "localhost")
CH_PORT     = int(os.getenv("CH_PORT", "8123"))
CH_USER     = os.getenv("CH_USER",     "default")
CH_PASSWORD = os.getenv("CH_PASSWORD", "")
CH_DB       = os.getenv("CH_DB",       "default")
TABLE       = f"{CH_DB}.events"

# ---------------------------------------------------------------------------
# ClickHouse async client (single shared instance — safe for async/await)
# ---------------------------------------------------------------------------

_async_client: clickhouse_connect.driver.AsyncClient | None = None


async def get_client() -> clickhouse_connect.driver.AsyncClient:
    global _async_client
    if _async_client is None:
        raise HTTPException(status_code=503, detail="ClickHouse client not initialised")
    return _async_client


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _async_client
    _async_client = await clickhouse_connect.get_async_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
        database=CH_DB,
    )
    await _async_client.query("SELECT 1")
    print(f"✓ Connected to ClickHouse (async) at {CH_HOST}:{CH_PORT}")
    yield
    await _async_client.close()
    print("✓ ClickHouse async connection closed")


app = FastAPI(
    title="E-Commerce Analytics API",
    description="Real-time analytics over the Kafka→ClickHouse events pipeline",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(result) -> list[dict]:
    """Convert clickhouse_connect QueryResult to list of dicts."""
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def _parse_window(window: str) -> str:
    """Return a ClickHouse interval expression for common window strings."""
    mapping = {
        "1h":  "now() - INTERVAL 1 HOUR",
        "6h":  "now() - INTERVAL 6 HOUR",
        "24h": "now() - INTERVAL 24 HOUR",
        "7d":  "now() - INTERVAL 7 DAY",
        "30d": "now() - INTERVAL 30 DAY",
    }
    if window not in mapping:
        raise HTTPException(
            status_code=400,
            detail=f"window must be one of {list(mapping)}",
        )
    return mapping[window]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health():
    """Liveness + ClickHouse connectivity check."""
    client = await get_client()
    result = await client.query("SELECT count() FROM default.events")
    total  = result.result_rows[0][0]
    return {"status": "ok", "clickhouse": "connected", "total_events": total}


@app.get("/events", tags=["Raw Data"])
async def list_events(
    limit:      int           = Query(50,    ge=1, le=1000),
    offset:     int           = Query(0,     ge=0),
    event_type: Optional[str] = Query(None,  description="Filter by event_type"),
    category:   Optional[str] = Query(None,  description="Filter by category"),
    user_id:    Optional[str] = Query(None,  description="Filter by user_id"),
    window:     str           = Query("24h", description="Time window: 1h/6h/24h/7d/30d"),
):
    """Paginated raw event log with optional filters."""
    client = await get_client()
    since  = _parse_window(window)
    wheres = [f"timestamp >= {since}"]
    if event_type:
        wheres.append(f"event_type = '{event_type}'")
    if category:
        wheres.append(f"category = '{category}'")
    if user_id:
        wheres.append(f"user_id = '{user_id}'")

    where_clause = " AND ".join(wheres)
    sql = f"""
        SELECT event_id, event_type, user_id, product_id,
               price, timestamp, category, ip_address
        FROM {TABLE}
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT {limit} OFFSET {offset}
    """
    result = await client.query(sql)
    rows   = _row_to_dict(result)
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()
    return {"data": rows, "limit": limit, "offset": offset}


@app.get("/metrics/overview", tags=["Metrics"])
async def overview(
    window: str = Query("24h", description="Time window: 1h/6h/24h/7d/30d"),
):
    """Top-level KPIs: events, CVR, revenue, AOV, unique users."""
    client = await get_client()
    since  = _parse_window(window)
    sql = f"""
        SELECT
            count()                                                          AS total_events,
            countIf(event_type = 'view')                                     AS views,
            countIf(event_type = 'click')                                    AS clicks,
            countIf(event_type = 'add_to_cart')                              AS carts,
            countIf(event_type = 'purchase')                                 AS purchases,
            uniqExact(user_id)                                               AS unique_users,
            sumIf(price, event_type = 'purchase')                            AS total_revenue,
            if(countIf(event_type='purchase') > 0,
               sumIf(price, event_type='purchase') /
               countIf(event_type='purchase'), 0)                            AS aov,
            if(countIf(event_type='view') > 0,
               100.0 * countIf(event_type='purchase') /
               countIf(event_type='view'), 0)                                AS cvr_pct
        FROM {TABLE}
        WHERE timestamp >= {since}
    """
    result = await client.query(sql)
    row    = dict(zip(result.column_names, result.result_rows[0]))
    return {"window": window, **row}


@app.get("/metrics/funnel", tags=["Metrics"])
async def funnel(
    window:   str           = Query("24h"),
    category: Optional[str] = Query(None),
):
    """Full funnel with absolute counts and step-over-step drop-off rates."""
    client     = await get_client()
    since      = _parse_window(window)
    cat_filter = f"AND category = '{category}'" if category else ""
    sql = f"""
        SELECT
            countIf(event_type = 'view')        AS views,
            countIf(event_type = 'click')       AS clicks,
            countIf(event_type = 'add_to_cart') AS carts,
            countIf(event_type = 'purchase')    AS purchases
        FROM {TABLE}
        WHERE timestamp >= {since} {cat_filter}
    """
    result = await client.query(sql)
    r = dict(zip(result.column_names, result.result_rows[0]))

    def pct(num, den):
        return round(100.0 * num / den, 2) if den else 0.0

    return {
        "window":   window,
        "category": category,
        "stages": [
            {"stage": "view",        "count": r["views"],     "drop_off_pct": None},
            {"stage": "click",       "count": r["clicks"],    "drop_off_pct": pct(r["clicks"],    r["views"])},
            {"stage": "add_to_cart", "count": r["carts"],     "drop_off_pct": pct(r["carts"],     r["clicks"])},
            {"stage": "purchase",    "count": r["purchases"], "drop_off_pct": pct(r["purchases"], r["carts"])},
        ],
        "overall_cvr_pct": pct(r["purchases"], r["views"]),
    }


@app.get("/metrics/timeseries", tags=["Metrics"])
async def timeseries(
    window:     str     = Query("24h"),
    bucket:     Literal["minute", "hour", "day"] = Query("hour"),
    event_type: Optional[str] = Query(None),
):
    """Event counts bucketed by time for charting."""
    client    = await get_client()
    since     = _parse_window(window)
    trunc     = {"minute": "toStartOfMinute", "hour": "toStartOfHour", "day": "toStartOfDay"}[bucket]
    et_filter = f"AND event_type = '{event_type}'" if event_type else ""
    sql = f"""
        SELECT
            {trunc}(timestamp) AS bucket,
            event_type,
            count()            AS cnt,
            sumIf(price, event_type = 'purchase') AS revenue
        FROM {TABLE}
        WHERE timestamp >= {since} {et_filter}
        GROUP BY bucket, event_type
        ORDER BY bucket ASC, event_type
    """
    result = await client.query(sql)
    rows   = _row_to_dict(result)
    for r in rows:
        if isinstance(r.get("bucket"), datetime):
            r["bucket"] = r["bucket"].isoformat()
    return {"window": window, "bucket": bucket, "data": rows}


@app.get("/metrics/top-products", tags=["Metrics"])
async def top_products(
    window: str = Query("24h"),
    by:     Literal["views", "purchases", "revenue"] = Query("revenue"),
    limit:  int = Query(10, ge=1, le=100),
):
    """Top N products ranked by views, purchases, or revenue."""
    client = await get_client()
    since  = _parse_window(window)
    order  = {
        "views":     "views DESC",
        "purchases": "purchases DESC",
        "revenue":   "revenue DESC",
    }[by]
    sql = f"""
        SELECT
            product_id,
            category,
            countIf(event_type = 'view')        AS views,
            countIf(event_type = 'click')       AS clicks,
            countIf(event_type = 'add_to_cart') AS carts,
            countIf(event_type = 'purchase')    AS purchases,
            sumIf(price, event_type='purchase') AS revenue,
            if(countIf(event_type='view') > 0,
               100.0 * countIf(event_type='purchase') /
               countIf(event_type='view'), 0)   AS cvr_pct
        FROM {TABLE}
        WHERE timestamp >= {since}
        GROUP BY product_id, category
        ORDER BY {order}
        LIMIT {limit}
    """
    result = await client.query(sql)
    return {"window": window, "by": by, "data": _row_to_dict(result)}


@app.get("/metrics/top-categories", tags=["Metrics"])
async def top_categories(
    window: str = Query("24h"),
):
    """Aggregated funnel stats broken down by product category."""
    client = await get_client()
    since  = _parse_window(window)
    sql = f"""
        SELECT
            category,
            countIf(event_type = 'view')        AS views,
            countIf(event_type = 'click')       AS clicks,
            countIf(event_type = 'add_to_cart') AS carts,
            countIf(event_type = 'purchase')    AS purchases,
            sumIf(price, event_type='purchase') AS revenue,
            if(countIf(event_type='view') > 0,
               100.0 * countIf(event_type='purchase') /
               countIf(event_type='view'), 0)   AS cvr_pct,
            if(countIf(event_type='purchase') > 0,
               sumIf(price, event_type='purchase') /
               countIf(event_type='purchase'), 0) AS aov
        FROM {TABLE}
        WHERE timestamp >= {since}
        GROUP BY category
        ORDER BY revenue DESC
    """
    result = await client.query(sql)
    return {"window": window, "data": _row_to_dict(result)}


@app.get("/metrics/users/{user_id}", tags=["Metrics"])
async def user_journey(
    user_id: str,
    window:  str = Query("7d"),
):
    """Full event history and summary stats for a single user."""
    client = await get_client()
    since  = _parse_window(window)

    summary_sql = f"""
        SELECT
            count()                                  AS total_events,
            countIf(event_type = 'view')             AS views,
            countIf(event_type = 'click')            AS clicks,
            countIf(event_type = 'add_to_cart')      AS carts,
            countIf(event_type = 'purchase')         AS purchases,
            sumIf(price, event_type = 'purchase')    AS total_spent,
            uniqExact(product_id)                    AS unique_products_viewed,
            min(timestamp)                           AS first_seen,
            max(timestamp)                           AS last_seen
        FROM {TABLE}
        WHERE user_id = '{user_id}'
          AND timestamp >= {since}
    """
    summary_result = await client.query(summary_sql)
    summary = dict(zip(summary_result.column_names, summary_result.result_rows[0]))
    for k in ("first_seen", "last_seen"):
        if isinstance(summary.get(k), datetime):
            summary[k] = summary[k].isoformat()

    if summary["total_events"] == 0:
        raise HTTPException(status_code=404, detail=f"No events found for user '{user_id}'")

    events_sql = f"""
        SELECT event_id, event_type, product_id, price, timestamp, category
        FROM {TABLE}
        WHERE user_id = '{user_id}'
          AND timestamp >= {since}
        ORDER BY timestamp ASC
        LIMIT 200
    """
    events_result = await client.query(events_sql)
    events = _row_to_dict(events_result)
    for e in events:
        if isinstance(e.get("timestamp"), datetime):
            e["timestamp"] = e["timestamp"].isoformat()

    return {"user_id": user_id, "window": window, "summary": summary, "events": events}


@app.get("/metrics/revenue", tags=["Metrics"])
async def revenue(
    window: str = Query("24h"),
    bucket: Literal["minute", "hour", "day"] = Query("hour"),
):
    """Revenue over time plus totals and AOV."""
    client = await get_client()
    since  = _parse_window(window)
    trunc  = {"minute": "toStartOfMinute", "hour": "toStartOfHour", "day": "toStartOfDay"}[bucket]
    sql = f"""
        SELECT
            {trunc}(timestamp)  AS bucket,
            count()             AS orders,
            sum(price)          AS revenue,
            avg(price)          AS aov
        FROM {TABLE}
        WHERE event_type = 'purchase'
          AND timestamp >= {since}
        GROUP BY bucket
        ORDER BY bucket ASC
    """
    result = await client.query(sql)
    rows   = _row_to_dict(result)
    for r in rows:
        if isinstance(r.get("bucket"), datetime):
            r["bucket"] = r["bucket"].isoformat()

    total_revenue = sum(r["revenue"] for r in rows)
    total_orders  = sum(r["orders"]  for r in rows)
    overall_aov   = total_revenue / total_orders if total_orders else 0

    return {
        "window":        window,
        "bucket":        bucket,
        "total_revenue": round(total_revenue, 2),
        "total_orders":  total_orders,
        "overall_aov":   round(overall_aov, 2),
        "timeseries":    rows,
    }


@app.get("/metrics/realtime", tags=["Metrics"])
async def realtime():
    """
    Rolling 60-second window for live dashboards.
    Returns per-minute buckets + current events-per-second rate.
    """
    client = await get_client()
    sql = f"""
        SELECT
            toStartOfMinute(timestamp) AS bucket,
            countIf(event_type = 'view')        AS views,
            countIf(event_type = 'click')       AS clicks,
            countIf(event_type = 'add_to_cart') AS carts,
            countIf(event_type = 'purchase')    AS purchases,
            count()                             AS total
        FROM {TABLE}
        WHERE timestamp >= now() - INTERVAL 2 MINUTE
        GROUP BY bucket
        ORDER BY bucket ASC
    """
    result = await client.query(sql)
    rows   = _row_to_dict(result)
    for r in rows:
        if isinstance(r.get("bucket"), datetime):
            r["bucket"] = r["bucket"].isoformat()

    eps = 0.0
    if rows:
        eps = round(rows[-1]["total"] / 60.0, 2)

    return {"events_per_sec": eps, "buckets": rows}
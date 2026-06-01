#!/usr/bin/env python3
"""Metrics endpoints."""

from fastapi import APIRouter, Query, HTTPException
from typing import Literal, Optional
from ..db import get_client, TABLE
from ..utils import row_to_dict, sql_equals, parse_window, format_iso_timestamps

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/overview")
async def overview(
    window: str = Query("24h", description="Time window: 1h/6h/24h/7d/30d"),
):
    """Top-level KPIs: events, CVR, revenue, AOV, unique users."""
    client = await get_client()
    since  = parse_window(window)
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


@router.get("/funnel")
async def funnel(
    window:   str           = Query("24h"),
    category: Optional[str] = Query(None),
):
    """Full funnel with absolute counts and step-over-step drop-off rates."""
    client     = await get_client()
    since      = parse_window(window)
    cat_filter = f"AND {sql_equals('category', category)}" if category else ""
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


@router.get("/timeseries")
async def timeseries(
    window:     str     = Query("24h"),
    bucket:     Literal["minute", "hour", "day"] = Query("hour"),
    event_type: Optional[str] = Query(None),
):
    """Event counts bucketed by time for charting."""
    client    = await get_client()
    since     = parse_window(window)
    trunc     = {"minute": "toStartOfMinute", "hour": "toStartOfHour", "day": "toStartOfDay"}[bucket]
    et_filter = f"AND {sql_equals('event_type', event_type)}" if event_type else ""
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
    rows   = row_to_dict(result)
    format_iso_timestamps(rows, ["bucket"])
    return {"window": window, "bucket": bucket, "data": rows}


@router.get("/top-products")
async def top_products(
    window: str = Query("24h"),
    by:     Literal["views", "purchases", "revenue"] = Query("revenue"),
    limit:  int = Query(10, ge=1, le=100),
):
    """Top N products ranked by views, purchases, or revenue."""
    client = await get_client()
    since  = parse_window(window)
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
    return {"window": window, "by": by, "data": row_to_dict(result)}


@router.get("/top-categories")
async def top_categories(
    window: str = Query("24h"),
):
    """Aggregated funnel stats broken down by product category."""
    client = await get_client()
    since  = parse_window(window)
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
    return {"window": window, "data": row_to_dict(result)}


@router.get("/users/{user_id}")
async def user_journey(
    user_id: str,
    window:  str = Query("7d"),
):
    """Full event history and summary stats for a single user."""
    client = await get_client()
    since  = parse_window(window)

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
        WHERE {sql_equals('user_id', user_id)}
          AND timestamp >= {since}
    """
    summary_result = await client.query(summary_sql)
    summary = dict(zip(summary_result.column_names, summary_result.result_rows[0]))
    format_iso_timestamps([summary], ["first_seen", "last_seen"])

    if summary["total_events"] == 0:
        raise HTTPException(status_code=404, detail=f"No events found for user '{user_id}'")

    events_sql = f"""
        SELECT event_id, event_type, product_id, price, timestamp, category
        FROM {TABLE}
        WHERE {sql_equals('user_id', user_id)}
          AND timestamp >= {since}
        ORDER BY timestamp ASC
        LIMIT 200
    """
    events_result = await client.query(events_sql)
    events = row_to_dict(events_result)
    format_iso_timestamps(events, ["timestamp"])

    return {"user_id": user_id, "window": window, "summary": summary, "events": events}


@router.get("/revenue")
async def revenue(
    window: str = Query("24h"),
    bucket: Literal["minute", "hour", "day"] = Query("hour"),
):
    """Revenue over time plus totals and AOV."""
    client = await get_client()
    since  = parse_window(window)
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
    rows   = row_to_dict(result)
    format_iso_timestamps(rows, ["bucket"])

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


@router.get("/realtime")
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
    rows   = row_to_dict(result)
    format_iso_timestamps(rows, ["bucket"])

    eps = 0.0
    if rows:
        eps = round(rows[-1]["total"] / 60.0, 2)

    return {"events_per_sec": eps, "buckets": rows}

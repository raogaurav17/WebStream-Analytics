#!/usr/bin/env python3
"""Raw events endpoint."""

from fastapi import APIRouter, Query
from typing import Optional
from ..db import get_client, TABLE
from ..utils import row_to_dict, sql_equals, parse_window, format_iso_timestamps

router = APIRouter()

@router.get("/events", tags=["Raw Data"])
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
    since  = parse_window(window)
    wheres = [f"timestamp >= {since}"]
    if event_type:
        wheres.append(sql_equals("event_type", event_type))
    if category:
        wheres.append(sql_equals("category", category))
    if user_id:
        wheres.append(sql_equals("user_id", user_id))

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
    rows   = row_to_dict(result)
    format_iso_timestamps(rows, ["timestamp"])
    return {"data": rows, "limit": limit, "offset": offset}

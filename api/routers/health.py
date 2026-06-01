#!/usr/bin/env python3
"""Health check endpoint."""

from fastapi import APIRouter
from ..db import get_client

router = APIRouter()

@router.get("/health", tags=["System"])
async def health():
    """Liveness + ClickHouse connectivity check."""
    client = await get_client()
    result = await client.query("SELECT count() FROM default.events")
    total  = result.result_rows[0][0]
    return {"status": "ok", "clickhouse": "connected", "total_events": total}

#!/usr/bin/env python3
"""ClickHouse async client."""

import clickhouse_connect
import os
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

CH_HOST = os.getenv("CH_HOST", "localhost")
CH_PORT = int(os.getenv("CH_PORT", "8123"))
CH_USER = os.getenv("CH_USER", "default")
CH_PASSWORD = os.getenv("CH_PASSWORD", "")
CH_DB = os.getenv("CH_DB", "default")
TABLE = f"{CH_DB}.events"

_async_client: clickhouse_connect.driver.AsyncClient | None = None


async def get_client() -> clickhouse_connect.driver.AsyncClient:
    """Get a shared ClickHouse async client."""
    global _async_client
    if _async_client is None:
        raise HTTPException(status_code=503, detail="ClickHouse client not initialised")
    return _async_client


async def connect_to_db():
    """Connect to ClickHouse."""
    global _async_client
    _async_client = await clickhouse_connect.get_async_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
        database=CH_DB,
    )
    await _async_client.query("SELECT 1")
    print(f"Connected to ClickHouse at {CH_HOST}:{CH_PORT}")


async def close_db_connection():
    """Close the ClickHouse connection."""
    global _async_client
    if _async_client:
        await _async_client.close()
        print("ClickHouse async connection closed")

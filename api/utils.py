#!/usr/bin/env python3
"""API utility functions."""

from fastapi import HTTPException
from datetime import datetime

def row_to_dict(result) -> list[dict]:
    """Convert clickhouse_connect QueryResult to list of dicts."""
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def sql_string(value: str) -> str:
    """Return a safely quoted ClickHouse string literal."""
    return "'" + value.replace("'", "''") + "'"


def sql_equals(column: str, value: str) -> str:
    """Build a simple equality predicate for a trusted column name."""
    return f"{column} = {sql_string(value)}"


def parse_window(window: str) -> str:
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

def format_iso_timestamps(rows: list[dict], fields: list[str]):
    """Convert datetime objects in query results to ISO 8601 strings."""
    for r in rows:
        for field in fields:
            if isinstance(r.get(field), datetime):
                r[field] = r[field].isoformat()

#!/usr/bin/env python3
"""
E-Commerce Analytics API
FastAPI + ClickHouse — read-only analytics layer over the events table.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .db import connect_to_db, close_db_connection
from .routers import health, events, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    await connect_to_db()
    yield
    await close_db_connection()


app = FastAPI(
    title="WebStream Analytics API",
    description="Real-time analytics over the Kafka -> ClickHouse events pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(events.router)
app.include_router(metrics.router)

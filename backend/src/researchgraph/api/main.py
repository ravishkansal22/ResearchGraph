"""FastAPI Application Entry Point for ResearchGraph Backend."""

from __future__ import annotations

import time
from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from researchgraph.api.router import api_router
from researchgraph.core.config import settings
from researchgraph.core.logging import setup_logging

setup_logging(debug=settings.debug)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production backend for ResearchGraph: An evidence-grounded scientific discovery platform "
        "designed to identify non-obvious cross-domain connections, verify research gaps, "
        "detect negative knowledge, and formulate falsifiable research hypotheses."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Any:
    """Track request processing latency and inject X-Process-Time header."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response


@app.get("/")
def root_endpoint() -> dict[str, str]:
    """Root welcome message and documentation links."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "documentation": "/docs",
        "api_prefix": settings.api_prefix,
        "status": "online",
    }


# Register all API endpoints
app.include_router(api_router, prefix=settings.api_prefix)

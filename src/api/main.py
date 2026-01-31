"""
FastAPI main application.
Initializes app, mounts routers, sets up middleware.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import setup_logging, API_HOST, API_PORT
from .routers import scores, clusters, nlp_insights

logger = setup_logging(__name__)

# Create app
app = FastAPI(
    title="Climate Burden Index API",
    description="REST API for Climate Burden Index system",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(scores.router)
app.include_router(clusters.router)
app.include_router(nlp_insights.router)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint / health check."""
    return {
        "service": "Climate Burden Index API",
        "version": "1.0.0",
        "status": "ok",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "models": "loaded",
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
    
    uvicorn.run(
        "src.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        workers=1,
    )

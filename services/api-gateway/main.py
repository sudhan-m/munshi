from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
import os
import logging
from .router import create_gateway_router
from .cache import get_gateway_cache, close_gateway_cache
from .middleware import (
    create_rate_limit_middleware,
    create_response_cache_middleware,
    create_logging_middleware
)
from .config import get_gateway_settings
from dotenv import load_dotenv

load_dotenv()

settings = get_gateway_settings()

app = FastAPI(
    title="API Gateway",
    description="Secure API Gateway with Redis caching, rate limiting, and authentication",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Add Redis-based middleware in proper order
app.middleware("http")(create_logging_middleware())
app.middleware("http")(create_rate_limit_middleware())
app.middleware("http")(create_response_cache_middleware())

@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    """Add request ID and timing middleware"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", "unknown"),
            "status_code": exc.status_code
        }
    )

@app.get("/")
async def root():
    return {
        "message": "API Gateway is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "auth": "/auth/*",
            "protected": "/protected/{service_name}/*",
            "services": "/services"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "api-gateway"
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize Redis cache connection on startup."""
    cache = get_gateway_cache()
    if cache.is_connected():
        logging.info("API Gateway connected to Redis cache")
    else:
        logging.warning("API Gateway failed to connect to Redis cache")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up Redis cache connection on shutdown."""
    close_gateway_cache()
    logging.info("API Gateway Redis cache connection closed")

gateway_router = create_gateway_router()
app.include_router(gateway_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_GATEWAY_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
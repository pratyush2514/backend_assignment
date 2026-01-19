"""
Main FastAPI application
Production-ready quiz generation and performance analytics platform
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.config import settings
from app.database import init_db
from app.api import chapters, quizzes, analytics
from app.utils.rate_limiter import rate_limiter

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend platform for PDF-based learning with AI-powered quiz generation",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests"""
    
    # Skip rate limiting for health check and docs -- comment out to enable rate limiting on these endpoints
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    try:
        await rate_limiter.check_rate_limit(request)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content=e.detail
        ) 
    
    response = await call_next(request)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully"""
    
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Format HTTP exceptions consistently"""
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    
    Returns service status and dependencies
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Quiz Generation & Performance Analytics API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(chapters.router)
app.include_router(quizzes.router)
app.include_router(analytics.router)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    logger.info("Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings

# Create FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade expense tracking API",
    version="0.1.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - redirects to API root."""
    return RedirectResponse(url=f"{settings.api_prefix}/")


@app.get("/docs")
async def docs_redirect():
    """Docs redirect - redirects to versioned docs."""
    return RedirectResponse(url=f"{settings.api_prefix}/docs")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT, "version": "0.1.0"}


@app.get(f"{settings.api_prefix}/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Welcome to ExpenseTracker API",
        "version": settings.API_VERSION,
        "docs": f"{settings.api_prefix}/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level=settings.LOG_LEVEL.lower()
    )

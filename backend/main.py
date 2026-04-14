from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from database import create_tables
from routers import auth, audit, accounts

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="AdCoherence API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS must be added before the exception handler so its headers are always present
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler that returns JSON instead of crashing — crucially this
    lets the CORS middleware still attach its headers to the response, so the
    browser sees a real error message rather than a network failure.
    """
    import logging
    logging.getLogger("uvicorn.error").exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(accounts.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

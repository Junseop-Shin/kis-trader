import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .middleware.audit_middleware import AuditMiddleware
from .routers import auth, market, accounts, strategies, backtest

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting KIS Trader backend...")

    # APScheduler jobs will be registered in later phases
    scheduler.start()
    logger.info("APScheduler started")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("KIS Trader backend shutdown")


app = FastAPI(
    title="KIS Trader API",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware
app.add_middleware(AuditMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(market.router)
app.include_router(accounts.router)
app.include_router(strategies.router)
app.include_router(backtest.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}

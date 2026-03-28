import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .middleware.audit_middleware import AuditMiddleware
from .services.analytics import track
from .routers import auth, market, accounts, strategies, backtest, trading
from .workers.anomaly_detector import check_anomalies
from .workers.kis_token_refresher import refresh_kis_tokens
from .workers.trading_scheduler import (
    execute_pending_orders,
    generate_signals_and_queue_orders,
    send_daily_reports,
    send_weekly_reports,
)

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting KIS Trader backend...")

    # Register APScheduler jobs
    # Signal generation: weekdays 15:35
    scheduler.add_job(
        generate_signals_and_queue_orders,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=35),
        id="generate_signals",
        name="Generate trading signals after market close",
    )
    # Execute pending orders: weekdays 09:05
    scheduler.add_job(
        execute_pending_orders,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=5),
        id="execute_orders",
        name="Execute pending T+1 orders at market open",
    )
    # Daily reports: weekdays 16:30
    scheduler.add_job(
        send_daily_reports,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=30),
        id="daily_reports",
        name="Send daily performance reports",
    )
    # Weekly reports: Friday 17:00
    scheduler.add_job(
        send_weekly_reports,
        CronTrigger(day_of_week="fri", hour=17, minute=0),
        id="weekly_reports",
        name="Send weekly performance reports",
    )
    # Anomaly detection: every 5 minutes during trading hours
    scheduler.add_job(
        check_anomalies,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/5"),
        id="anomaly_check",
        name="Check for price anomalies",
    )
    # KIS token refresh: weekdays 08:30
    scheduler.add_job(
        refresh_kis_tokens,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=30),
        id="kis_token_refresh",
        name="Refresh KIS API access tokens",
    )

    scheduler.start()
    logger.info("APScheduler started with 6 jobs")

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
app.include_router(trading.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.post("/analytics/pageview", status_code=202)
async def pageview(req: dict):
    """Proxy pageview events from frontend to ingestor."""
    track(settings.INGESTOR_URL, "pageview", path=req.get("path"), title=req.get("title"))
    return {"queued": 1}

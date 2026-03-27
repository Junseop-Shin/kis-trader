"""
Data collector scheduler.
Runs initial bulk load if database is empty, then daily updates at 16:00 weekdays.
"""
import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from collector import (
    _get_engine,
    _get_session_factory,
    collect_daily_update,
    collect_stock_list,
    initial_bulk_load,
    is_database_empty,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/kistrader")


async def daily_job():
    engine = _get_engine(DATABASE_URL)
    session_factory = _get_session_factory(engine)
    try:
        await collect_daily_update(session_factory)
    finally:
        await engine.dispose()


async def stock_list_job():
    engine = _get_engine(DATABASE_URL)
    session_factory = _get_session_factory(engine)
    try:
        await collect_stock_list(session_factory)
    finally:
        await engine.dispose()


async def startup_check():
    """Check if initial bulk load is needed."""
    engine = _get_engine(DATABASE_URL)
    session_factory = _get_session_factory(engine)
    try:
        empty = await is_database_empty(session_factory)
        if empty:
            logger.info("Database is empty. Running initial bulk load...")
            await initial_bulk_load(session_factory)
        else:
            logger.info("Database has data. Skipping initial bulk load.")
    finally:
        await engine.dispose()


def main():
    scheduler = AsyncIOScheduler()

    # Daily price update: weekdays at 16:00
    scheduler.add_job(
        daily_job,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0),
        id="daily_update",
        name="Daily price and fundamentals update",
    )

    # Weekly stock list refresh: Mondays at 06:00
    scheduler.add_job(
        stock_list_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="stock_list_refresh",
        name="Weekly stock list refresh",
    )

    scheduler.start()
    logger.info("Data collector scheduler started")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(startup_check())

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down")


if __name__ == "__main__":
    main()

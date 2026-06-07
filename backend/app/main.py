import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.database import close_db, init_db
from app.services.monitor import run_price_check

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler = AsyncIOScheduler()

    async def job():
        try:
            checked, alerts = await run_price_check()
            logger.info("Price check: routes=%s alerts=%s", checked, alerts)
        except Exception:
            logger.exception("Price check failed")

    if settings.travelpayouts_token:
        scheduler.add_job(
            job,
            "interval",
            hours=max(1, settings.check_interval_hours),
            id="price_check",
        )
        scheduler.start()
    else:
        logger.warning("TRAVELPAYOUTS_TOKEN не задан — фоновые проверки отключены")

    yield
    scheduler.shutdown(wait=False)
    await close_db()


app = FastAPI(title="Flight Alerts API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

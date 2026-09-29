import logging
import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.endpoints import router as api_router
from app.schemas import HealthResponse
from app.services.max_bot import MaxBot
from app.services.reminder_service import ReminderService


logger = logging.getLogger("businesscontrol")


# Для текущего MVP автоматически создаём таблицы при запуске.
# Перед production-развёртыванием эту логику можно заменить
# полноценными миграциями Alembic.
init_db()

max_bot = MaxBot()
reminder_service = ReminderService(max_bot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    reminder_task = asyncio.create_task(reminder_service.run())

    try:
        yield
    finally:
        reminder_service.stop()
        await reminder_task
        await max_bot.close()


app = FastAPI(
    lifespan=lifespan,
    title="BusinessControl API",
    description="Backend сервис самопроверки бизнеса по нормативным требованиям",
    version="0.1.0",
)


# Настройки CORS берём из конфигурации приложения.
# В CORS_ORIGINS должны быть указаны конкретные домены,
# а не "*", если используется allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирует основные параметры каждого HTTP-запроса."""

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        process_time = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "%s %s -> 500 (%.2f ms)",
            request.method,
            request.url.path,
            process_time,
        )

        raise

    process_time = (time.perf_counter() - start_time) * 1000

    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )

    return response


# Подключаем API-роуты приложения.
# Префикс /api применяется ко всем API-эндпоинтам.
app.include_router(
    api_router,
    prefix="/api",
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["service"],
)
def health_check() -> HealthResponse:
    """Проверяет, что API запущено."""

    return HealthResponse(
        status="ok",
        service="businesscontrol",
    )
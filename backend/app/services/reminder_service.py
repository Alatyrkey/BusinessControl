import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Reminder
from app.services.max_bot import MaxBot


logger = logging.getLogger(__name__)


REMINDER_TEXT = (
    "🔔 Напоминание: время самопроверки\n\n"
    "Прошло 30 дней с последней самопроверки "
    "вашего торгового объекта.\n\n"
    "Рекомендуем пройти повторный чек-лист "
    "по СанПиН 2.3.6.4281-26, чтобы убедиться "
    "в отсутствии новых нарушений."
)


class ReminderService:
    """Фоновая служба автоматических напоминаний."""

    def __init__(self, bot: MaxBot) -> None:
        self.bot = bot
        self._stop_event = asyncio.Event()

    async def check_reminders(self) -> None:
        """Проверить напоминания и отправить сообщения."""

        db: Session = SessionLocal()

        try:
            now = datetime.now(timezone.utc)

            reminders = (
                db.query(Reminder)
                .filter(
                    Reminder.is_active.is_(True),
                    Reminder.next_notification_at.isnot(None),
                    Reminder.next_notification_at <= now,
                )
                .all()
            )

            for reminder in reminders:
                try:
                    business = reminder.business

                    if business is None:
                        continue

                    chat_id = getattr(
                        business,
                        "max_chat_id",
                        None,
                    )

                    if chat_id is None:
                        logger.warning(
                            "Для business_id=%s не найден MAX chat_id",
                            reminder.business_id,
                        )
                        continue

                    await self.bot.send_message(
                        REMINDER_TEXT,
                        chat_id=chat_id,
                    )

                    reminder.last_notification_at = now
                    reminder.next_notification_at = (
                        now
                        + __import__("datetime").timedelta(
                            days=reminder.period_days
                        )
                    )

                    db.commit()

                    logger.info(
                        "Напоминание отправлено. business_id=%s chat_id=%s",
                        reminder.business_id,
                        chat_id,
                    )

                except Exception:
                    db.rollback()

                    logger.exception(
                        "Ошибка отправки напоминания. business_id=%s",
                        reminder.business_id,
                    )

        finally:
            db.close()

    async def run(self) -> None:
        """Запустить фоновую проверку напоминаний."""

        logger.info("Сервис напоминаний запущен.")

        while not self._stop_event.is_set():
            try:
                await self.check_reminders()

            except Exception:
                logger.exception(
                    "Ошибка сервиса напоминаний.",
                )

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        """Остановить сервис напоминаний."""

        self._stop_event.set()
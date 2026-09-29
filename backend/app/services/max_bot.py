import asyncio
import logging
from typing import Any

import httpx

from app.config import settings
from app.database import SessionLocal
from app.models import Business, Checklist, ChecklistItem


logger = logging.getLogger(__name__)


UPDATE_TYPES = "bot_started,message_created,message_callback"


WELCOME_TEXT = (
    "Здравствуйте!  \n\n"
    "Бизнес Контроль - сервис самопроверки\n"
    "торговых объектов и рынков, реализующих\n"
    "пищевую продукцию.\n\n"
    "Основан на требованиях СанПиН 2.3.6.4281-26.\n\n"
    "За 30 минут вы пройдёте чек-лист\n"
    "и получите:\n"
    "🗺️ Карту санитарных рисков объекта\n"
    "📋 Список нарушений с приоритетами\n"
    "🛠️Пошаговые инструкции по устранению\n\n"
    "Готовы проверить свой бизнес?"
)

MENU_TEXT = "Выберите действие:"

START_CHECK_PAYLOAD = "start_check"
MY_CHECKS_PAYLOAD = "my_checks"
LAST_RESULT_PAYLOAD = "last_result"



class MaxApiError(Exception):
    """Ошибка при обращении к MAX Bot API."""


class MaxBot:
    """Клиент MAX Bot API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.MAX_API_BASE_URL.rstrip("/"),
            headers={
                "Authorization": settings.MAX_BOT_TOKEN,
            },
            timeout=httpx.Timeout(
                15.0,
                read=40.0,
            ),
            verify=False,
        )

        self._marker: int | None = None
        self._stop_event = asyncio.Event()

    async def get_last_checklist_result(
        self,
        user_id: int,
    ) -> str:
        """Сформировать краткий результат последней проверки."""

        db = SessionLocal()

        try:
            business = (
                db.query(Business)
                .filter(Business.user_id == user_id)
                .order_by(Business.updated_at.desc())
                .first()
            )

            if business is None:
                return (
                    "📊 У вас пока нет проверок.\n\n"
                    "Сначала запустите самопроверку в приложении."
                )

            checklist = (
                db.query(Checklist)
                .filter(Checklist.business_id == business.id)
                .order_by(
                    Checklist.updated_at.desc(),
                    Checklist.id.desc(),
                )
                .first()
            )

            if checklist is None:
                return (
                    f"📊 Для бизнеса «{business.name}» "
                    "пока нет проверок."
                )

            items = (
                db.query(ChecklistItem)
                .filter(
                    ChecklistItem.checklist_id == checklist.id,
                )
                .all()
            )

            total = len(items)
            checked = sum(
                item.result is not None
                for item in items
            )
            no = sum(
                item.result == "no"
                for item in items
            )
            unknown = sum(
                item.result == "unknown"
                for item in items
            )
            not_applicable = sum(
                item.result == "not_applicable"
                for item in items
            )

            if checklist.status == "completed":
                status_text = "завершена"
            elif checklist.status == "finished_early":
                status_text = "завершена досрочно"
            else:
                status_text = "в процессе"

            return (
                "📊 Последний результат\n\n"
                f"🏢 {business.name}\n"
                f"Статус: {status_text}\n\n"
                f"Проверено: {checked} из {total}\n"
                f"❌ Нарушений: {no}\n"
                f"❓ Не уверен: {unknown}\n"
                f"➖ Не относится: {not_applicable}"
            )

        finally:
            db.close()

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""

        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict:
        """Выполнить запрос к MAX API."""

        try:
            response = await self._client.request(
                method,
                path,
                **kwargs,
            )

        except httpx.RequestError as exc:
            logger.error(
                "Ошибка сети MAX API: %s",
                exc,
            )
            raise MaxApiError(
                f"Ошибка сети MAX API: {exc}"
            ) from exc

        if response.status_code >= 400:
            logger.error(
                "MAX API error: %s %s -> %s: %s",
                method,
                path,
                response.status_code,
                response.text,
            )

            raise MaxApiError(
                f"MAX API вернул HTTP {response.status_code}"
            )

        return response.json()

    async def get_me(self) -> dict:
        """Получить информацию о боте."""

        return await self._request(
            "GET",
            "/me",
        )

    async def get_updates(
        self,
        marker: int | None = None,
        limit: int = 100,
        timeout: int = 30,
    ) -> tuple[list[dict], int | None]:
        """Получить события через Long Polling."""

        params: dict[str, Any] = {
            "limit": limit,
            "timeout": timeout,
            "types": UPDATE_TYPES,
        }

        if marker is not None:
            params["marker"] = marker

        data = await self._request(
            "GET",
            "/updates",
            params=params,
            timeout=httpx.Timeout(
                15.0,
                read=timeout + 10,
            ),
        )

        updates = data.get("updates", [])
        next_marker = data.get("marker")

        return updates, next_marker

    async def send_message(
        self,
        text: str,
        *,
        chat_id: int,
    ) -> dict:
        """Отправить текстовое сообщение."""

        return await self._request(
            "POST",
            "/messages",
            params={
                "chat_id": chat_id,
            },
            json={
                "text": text,
            },
        )

    async def send_main_menu(
        self,
        chat_id: int,
        text: str = MENU_TEXT,
    ) -> None:
        """Показать главное меню бота."""

        await self._request(
            "POST",
            "/messages",
            params={
                "chat_id": chat_id,
            },
            json={
                "text": text,
                "attachments": [
                    {
                        "type": "inline_keyboard",
                        "payload": {
                            "buttons": [
                                [
                                    {
                                        "type": "open_app",
                                        "text": "🚀 Начать самопроверку",
                                        "web_app": "t44_hakaton_max_bot",
                                    }
                                ],
                                [
                                    {
                                        "type": "callback",
                                        "text": "📋 Мои проверки",
                                        "payload": MY_CHECKS_PAYLOAD,
                                    },
                                    {
                                        "type": "callback",
                                        "text": "📊 Последний результат",
                                        "payload": LAST_RESULT_PAYLOAD,
                                    },
                                ],
                            ]
                        },
                    }
                ],
            },
        )


    async def handle_bot_started(
        self,
        update: dict,
    ) -> None:
        """Обработать запуск бота."""

        chat_id = update.get("chat_id")

        if chat_id is None:
            logger.warning(
                "bot_started без chat_id: %s",
                update,
            )
            return

        logger.info(
            "Пользователь запустил бота. chat_id=%s",
            chat_id,
        )

        try:
            await self.send_main_menu(
                chat_id=chat_id,
                text=WELCOME_TEXT,
            )

        except MaxApiError:
            logger.exception(
                "Не удалось отправить приветствие. chat_id=%s",
                chat_id,
            )

    async def handle_message_created(
        self,
        update: dict,
    ) -> None:
        """Обработать входящее сообщение."""

        message = update.get("message") or {}
        body = message.get("body") or {}

        text = body.get("text", "")
        chat_id = update.get("chat_id")

        if not text or chat_id is None:
            return

        logger.info(
            "Получено сообщение. chat_id=%s text=%r",
            chat_id,
            text,
        )

    async def handle_message_callback(
        self,
        update: dict,
    ) -> None:
        """Обработать нажатие callback-кнопки."""

        callback = update.get("callback") or {}
        payload = callback.get("payload")
        chat_id = update.get("chat_id")

        user = update.get("user") or {}
        user_id = user.get("user_id")

        if user_id is None:
            logger.warning(
                "message_callback без user.user_id: %s",
                update,
            )
            return
        if chat_id is None:
            logger.warning(
                "message_callback без chat_id: %s",
                update,
            )
            return
    
        logger.info(
            "Нажата callback-кнопка. chat_id=%s payload=%r",
            chat_id,
            payload,
        )

        if payload == MY_CHECKS_PAYLOAD:
            db = SessionLocal()

            try:
                businesses = (
                    db.query(Business)
                    .filter(Business.user_id == user_id)
                    .order_by(Business.updated_at.desc())
                    .all()
                )

                if not businesses:
                    await self.send_message(
                        "📋 У вас пока нет добавленных бизнесов.\n\n"
                        "Добавьте бизнес в приложении BusinessControl.",
                        chat_id=chat_id,
                    )
                    return

                lines = ["📋 Ваши проверки:\n"]

                for business in businesses[:10]:
                    checklist = (
                        db.query(Checklist)
                        .filter(
                            Checklist.business_id == business.id,
                        )
                        .order_by(
                            Checklist.updated_at.desc(),
                            Checklist.id.desc(),
                        )
                        .first()
                    )

                    if checklist is None:
                        status = "не начата"
                    elif checklist.status == "draft":
                        status = "в процессе"
                    elif checklist.status == "finished_early":
                        status = "завершена досрочно"
                    elif checklist.status == "completed":
                        status = "завершена"
                    else:
                        status = checklist.status

                    lines.append(
                        f"• {business.name} — {status}"
                    )

                await self.send_message(
                    "\n".join(lines),
                    chat_id=chat_id,
                )

            finally:
                db.close()

        elif payload == LAST_RESULT_PAYLOAD:
            result_text = await self.get_last_checklist_result(
               user_id=user_id,
            )

            await self.send_message(
                result_text,
                chat_id=chat_id,
            )

        else:
            logger.info(
                "Неизвестный callback payload: %r",
                payload,
            )

    async def handle_update(
        self,
        update: dict,
    ) -> None:
        """Обработать событие MAX."""

        update_type = update.get("update_type")

        if update_type == "bot_started":
            await self.handle_bot_started(update)

        elif update_type == "message_created":
            await self.handle_message_created(update)

        elif update_type == "message_callback":
            await self.handle_message_callback(update)

        else:
            logger.info(
                "Неизвестный тип события: %s",
                update_type,
            )

    async def run_polling(self) -> None:
        """Запустить Long Polling."""

        logger.info("MAX бот запущен.")

        me = await self.get_me()

        logger.info(
            "Бот: %s (@%s), user_id=%s",
            me.get("name"),
            me.get("username"),
            me.get("user_id"),
        )

        while not self._stop_event.is_set():
            try:
                updates, next_marker = await self.get_updates(
                    marker=self._marker,
                )

                if next_marker is not None:
                    self._marker = next_marker

                for update in updates:
                    try:
                        await self.handle_update(update)

                    except Exception:
                        logger.exception(
                            "Ошибка обработки update: %s",
                            update,
                        )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "Ошибка MAX polling. Повтор через 3 секунды.",
                )
                await asyncio.sleep(3)

    def stop(self) -> None:
        """Остановить polling."""

        self._stop_event.set()
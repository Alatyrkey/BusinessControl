import asyncio
import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


UPDATE_TYPES = "bot_started,message_created"


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
            response = await self._request(
                "POST",
                "/messages",
                params={
                    "chat_id": chat_id,
                },
                json={
                    "text": WELCOME_TEXT,
                    "attachments": [
                        {
                            "type": "inline_keyboard",
                            "payload": {
                                "buttons": [
                                    [
                                        {
                                            "type": "open_app",
                                            "text": "Начать самопроверку",
                                            "web_app": "t44_hakaton_max_bot",
                                        }
                                    ]
                                ]
                            },
                        }
                    ],
                },
            )

            print("MAX SEND RESPONSE:")
            print(response)

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
import json

from fastapi import Depends, Header, HTTPException, status

from app.config import settings
from app.services.max_auth import validate_max_init_data
from app.database import get_db


# Сессия БД - алиас без лишней обёртки
get_database = get_db


def get_max_init_data(
    x_init_data: str = Header(..., alias="X-Init-Data"),
) -> str:
    """
    Извлекает initData из заголовка.
    
    FastAPI сам проверит наличие заголовка.
    Эта функция нужна только как точка входа для зависимости.
    """
    return x_init_data


def get_current_user_id(
    init_data: str = Depends(get_max_init_data),
) -> int:
    """
    Проверяет подпись initData MAX и возвращает user_id пользователя.

    Без этой проверки злоумышленник мог бы подделать запрос
    и получить доступ к чужим данным.
    """
    parsed = validate_max_init_data(
        init_data,
        settings.MAX_BOT_TOKEN,
    )

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидная подпись initData",
        )

    user_str = parsed.get("user")

    if not user_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует поле user в initData",
        )

    try:
        user_data = json.loads(user_str)
        return int(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось извлечь user_id из initData",
        )

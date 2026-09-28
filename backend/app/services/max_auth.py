import hashlib
import hmac
from urllib.parse import parse_qsl


def validate_max_init_data(
    init_data: str,
    bot_token: str,
) -> dict[str, str] | None:
    """
    Проверяет подпись initData от MAX и возвращает параметры,
    если данные прошли проверку
    """
    try:
        params = parse_qsl(
            init_data,
            keep_blank_values=True,
        )
    except ValueError:
        return None

    # Каждый параметр должен встречаться ровно один раз
    keys = [key for key, value in params]

    if len(keys) != len(set(keys)):
        return None

    hash_values = [value for key, value in params if key == "hash"]

    # Параметр hash должен быть ровно один
    if len(hash_values) != 1:
        return None

    received_hash = hash_values[0]

    # Убираем hash из данных, которые участвуют в проверке
    data_pairs = [
        (key, value)
        for key, value in params
        if key != "hash"
    ]

    # Сортируем параметры по ключу - так требует алгоритм MAX
    data_pairs.sort(key=lambda item: item[0])

    # Формируем строку для проверки подписи
    launch_params = "\n".join(
        f"{key}={value}"
        for key, value in data_pairs
    )

    # Формируем секретный ключ из токена бота
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Вычисляем подпись переданных данных
    calculated_hash = hmac.new(
        key=secret_key,
        msg=launch_params.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Сравниваем подписи безопасным способом, чтобы избежать timing-атак
    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    return dict(data_pairs)
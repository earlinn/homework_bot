class HTTPStatusError(Exception):
    """Вызывается, когда API вернул код ответа, не равный 200 (не ОК)."""

    pass


class UndocumentedHomeworkStatusError(Exception):
    """Вызывается, если API передало неизвестный статус домашней работы."""

    pass


class NoHomeworksKeyInResponseError(TypeError):
    """
    Вызывается, если в ответе API отсутствует ключ homeworks.
    Наследник TypeError, поскольку иначе не проходят тесты (tests/test_bot.py).
    """

    pass


class NoCurrentDateKeyInResponseError(Exception):
    """Вызывается, если в ответе API отсутствует ключ current_date."""

    pass

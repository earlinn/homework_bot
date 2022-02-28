class UndocumentedHomeworkStatusError(Exception):
    """Вызывается, если API передало неизвестный статус домашней работы."""

    pass


class NoHomeworksKeyInResponseError(TypeError):
    """Вызывается, если в ответе API отсутствует ключ homeworks."""

    pass

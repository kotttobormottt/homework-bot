class MessageNotSendedException(Exception):
    """Сообщение не отправлено."""


class APIRequestException(Exception):
    """Ошибка при запросе API."""


class WrongAPIAnswerException(Exception):
    """Некорректный ответ API."""


class APIStatusCodeException(Exception):
    """Сервис недоступен."""


class HomeworkStatusException(Exception):
    """Неверный статус домашней работы."""

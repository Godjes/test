class ExceptionStatusError(Exception):
    """Класс исключения при не корректном статусе ответа."""

    def __init__(self, message):
        self.message = message


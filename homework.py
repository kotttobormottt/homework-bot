import logging
import os
import sys
import time
from typing import Dict, List

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def send_message(bot: telegram.Bot, message: str):
    """Отправляет сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение "{message}"')
    except telegram.error.TelegramError:
        raise exceptions.MessageNotSendedException('Сообщение не отправлено')


def get_api_answer(current_timestamp: int = 0) -> Dict:
    """Делает запрос к API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException as err:
        raise exceptions.APIRequestException(
            f'Ошибка {err} при получении ответа: '
            f'{ENDPOINT}, {HEADERS}, {params}'
        )
    if homework_statuses.status_code != requests.codes.ok:
        raise exceptions.APIStatusCodeException(
            f'Ответ сервера {homework_statuses.status_code}'
        )
    logger.info('Ответ получен')
    homework = homework_statuses.json()
    if ('error' or 'code') in homework:
        raise exceptions.WrongAPIAnswerException('Ошибка json')
    return homework


def check_response(response: Dict) -> List:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Не словарь')
    if response.get('current_date') is None:
        raise KeyError('Отсутствует current_date')
    homeworks = response["homeworks"]
    if not isinstance(homeworks, list):
        raise TypeError('Не список')
    return homeworks


def parse_status(homework: Dict[str, str]) -> str:
    """Извлекает из информации о  домашней работе."""
    homework_name = homework['homework_name']
    if homework_name is None:
        raise KeyError('Домашняя работа не найдена')
    homework_status = homework['status']
    if not homework_status:
        raise KeyError('Статус домашней работы не найден')
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        raise exceptions.HomeworkStatusException(
            'Вердикт по домашней работе не нвйден'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет наличие обязательных переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    logger.debug("Бот запущен")
    if check_tokens() is False:
        logger.critical("Отсутствуют переменные окружения")
        sys.exit("Прервать: Отсутствуют переменные окружения")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_status = None
    last_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks: List = check_response(response)
            if len(homeworks) == 0:
                logger.info('Список проверенных ДЗ пуст')
                continue
            homework_status = homeworks[0].get('status')
            message = parse_status(homeworks[0])
            if homework_status != current_status:
                current_status = homework_status
                logger.info(message)
                send_message(bot, message)
            logger.debug('Статус не изменился')
        except exceptions.MessageNotSendedException as bot_err:
            logger.error(f'Сбой при отправке сообщения: {bot_err}')
        except Exception as err:
            message = f'Сбой при работе в программе: {err}'
            logger.error(message)
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log',
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
    )
    logger.addHandler(logging.StreamHandler())
    main()

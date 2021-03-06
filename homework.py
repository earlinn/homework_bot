from http import HTTPStatus
import logging
import os
import sys
import time

from dotenv import load_dotenv
import requests
import telegram

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(console_handler)
formatter = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)
console_handler.setFormatter(formatter)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет в Telegram чат сообщения."""
    logger.info('Начало отправки сообщения в Telegram чат.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Окончание отправки сообщения в Telegram чат.')
        logger.info(f'Бот отправил сообщение: {message}.')
    except Exception as error:
        logger.error(
            f'Ошибка отправки сообщения в Telegram чат: {error.__class__}.')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        query_kwargs = {
            'url': ENDPOINT,
            'headers': HEADERS,
            'params': params,
        }
        response = requests.get(**query_kwargs)
    except Exception as error:
        logger.error(f'Ошибка при формировании запроса к эндпойнту: {error}.')
        # этот raise нужен, чтобы попасть в функцию main,
        # которая вызовет функцию send_message, чтобы бот отправил
        # сообщение об этой ошибке в чат.
        # Сам бот определен в функции main, так было в прекоде.
        raise error
    if response.status_code != HTTPStatus.OK:
        raise exceptions.HTTPStatusError(
            f'Эндпойнт {ENDPOINT} недоступен! '
            f'API вернул код {response.status_code}.'
        )
    return response.json()


def check_response(response):
    """
    Проверяет корректность ответа API-сервиса.
    Возвращает список домашних работ.
    """
    # ситуация с отсутствием переменной response теперь обрабатывается
    # в блоке except функции get_api_answer
    if 'homeworks' not in response:
        raise exceptions.NoHomeworksKeyInResponseError(
            'Ключ homeworks отсутствует в ответе API!')
    if 'current_date' not in response:
        raise exceptions.NoCurrentDateKeyInResponseError(
            'Ключ current_date отсутствует в ответе API!')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарём!')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'В ответе API по ключу homeworks значение не является списком!')
    if not isinstance(response['current_date'], int):
        raise TypeError(
            'В ответе API по ключу current_date значение не является целым!')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if not homework_status:
        raise KeyError('В домашней работе отсутствует ключ `homework_status`!')

    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.UndocumentedHomeworkStatusError(
            f'Статуса {homework_status} нет в словаре HOMEWORK_STATUSES!')

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность необходимых для бота переменных окружения."""
    required_environment_variables = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    # применён цикл for, чтобы указать в logger.critical имя конкретного token
    for token in required_environment_variables:
        if not required_environment_variables[token]:
            logger.critical(
                f'Отсутствует {token}!')
            return False
    return True


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format=(
            '%(asctime)s - %(levelname)s - '
            '%(funcName)s: %(lineno)d - %(message)s'
        ),
        filename='main.log',
        level=logging.INFO,
        datefmt='%d-%m-%Y %H:%M:%S'
    )

    if not check_tokens():
        logger.critical(
            'Отсутствуют обязательные переменные окружения! '
            'Программа принудительно остановлена.')
        sys.exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    prev_error_report = {}

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.debug('Новых статусов по домашним работам нет.')
            for homework in homeworks:
                homework_status = parse_status(homework)
                homework_name = homework['homework_name']
                logger.info(
                    f'Статус домашней работы {homework_name} обновлён.')
                send_message(bot, homework_status)
            current_timestamp = int(time.time())

        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            current_error_report = {
                error.__class__.__name__: str(error)
            }
            if current_error_report != prev_error_report:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                prev_error_report = current_error_report.copy()
            time.sleep(RETRY_TIME)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

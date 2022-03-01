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
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    query_kwargs = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params,
    }

    response = requests.get(**query_kwargs)
    if response.status_code != HTTPStatus.OK:
        raise Exception(
            f'Эндпойнт {ENDPOINT} недоступен! '
            f'API вернул код {response.status_code}.'
        )
    return response.json()


def check_response(response):
    """
    Проверяет корректность ответа API-сервиса.
    Возвращает список домашних работ.
    """
    if not response:
        raise Exception(f'Ошибка при запросе к API: {Exception}!')
    if 'homeworks' not in response:
        raise exceptions.NoHomeworksKeyInResponseError(
            'Ключ homeworks отсутствует в ответе API!')
    if type(response) is not dict:
        raise TypeError('Ответ API не является словарём!')
    if type(response['homeworks']) is not list:
        raise TypeError(
            'В ответе API по ключу homeworks значение не является списком!')
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
    for token in required_environment_variables:
        if not required_environment_variables[token]:
            logger.critical(
                f'Отсутствует {token}! Программа принудительно остановлена.')
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
        raise KeyboardInterrupt(
            'Отсутствуют обязательные переменные окружения!')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_list = check_response(response)
            if homeworks_list == []:
                logger.debug('Новых статусов по домашним работам нет.')
            for homework in homeworks_list:
                homework_status = parse_status(homework)
                homework_name = homework['homework_name']
                send_message(bot, homework_status)
                logger.info((
                    'В Telegram чат отправлено сообщение '
                    f'о статусе домашней работы {homework_name}.'
                ))

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except telegram.error.Unauthorized as error:
            logger.error(
                'Неверный TELEGRAM_TOKEN! Ошибка telegram.error.Unauthorized.')
            raise error

        except telegram.error.BadRequest as error:
            logger.error(
                'Неверный TELEGRAM_CHAT_ID! Ошибка telegram.error.BadRequest.')
            raise error

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(f'Сбой в работе программы: {error}')
            logger.info('В Telegram чат отправлено сообщение об ошибке.')
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()

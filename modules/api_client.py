# ./modules/api_client.py
"""
Модуль для работы с API сервера ElOrgEDS.
Получает общий AES-ключ.
"""

import requests
import base64
import urllib3
import yaml
import os

from modules.main_functions import write_log
from settings import MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST, MODULE_LOG_FILE_ERROR

# Отключаем предупреждения SSL (ТОЛЬКО ДЛЯ САМОПОДПИСАННЫХ СЕРТИФИКАТОВ!)
# В реальном продакшене НЕ ДЕЛАЙТЕ ЭТО! Используйте правильные сертификаты.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_shared_aes_key(api_url: str, api_token: str, verify_ssl: bool = False) -> bytes:
    """
    Получает общий AES-ключ из API сервера.

    Args:
        api_url: Базовый URL API сервера (например, "https://192.168.140.55").
        api_token: Токен аутентификации для API.
        verify_ssl: Проверять ли SSL-сертификаты (False для самоподписанных).

    Returns:
        32-байтовый общий AES-ключ.

    Raises:
        RuntimeError: Если не удалось получить ключ или он неверного формата.
        requests.RequestException: Если произошла ошибка сети.
    """
    try:
        # 1. Формируем URL для запроса ключа
        url = f"{api_url.rstrip('/')}/api/v1/key/get"

        # 2. Подготавливаем заголовки аутентификации
        headers = {
            "Authorization": f"Bearer {api_token}"
        }

        # 3. Выполняем HTTPS GET-запрос
        print()
        write_log(f"[api_client] Попытка подключения к API по адресу '{url}'"
                  f" для получения общего AES-ключа...",MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        response = requests.get(url, headers=headers, verify=verify_ssl, timeout=30)

        # 4. Проверяем статус ответа
        response.raise_for_status() # Выбрасывает исключение для 4xx, 5xx

        # 5. Парсим JSON-ответ
        data = response.json()

        # 6. Извлекаем Base64-строку ключа
        encrypted_key_b64 = data.get("shared_aes_key")
        if not encrypted_key_b64:
            raise RuntimeError("API response did not contain a 'shared_aes_key'.")

        # 7. Декодируем Base64
        key_bytes = base64.b64decode(encrypted_key_b64)

        # 8. Проверяем длину ключа
        if len(key_bytes) != 32:
            error_message = f"Decoded shared AES key is not 32 bytes long. Length: {len(key_bytes)} bytes."
            write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                      "error", MODULE_LOG_FILE_ERROR)
            raise RuntimeError(error_message)


        write_log(f"[api_client] Общий AES-ключ (32 байта) успешно получен из API.",
                  MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        return key_bytes

    except requests.exceptions.SSLError as ssl_err:
        error_message = f"Ошибка SSL при подключении к API: {ssl_err}"
        write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(error_message) from ssl_err
    except requests.exceptions.ConnectionError as conn_err:
        error_message = f"Ошибка подключения к API: {conn_err}"
        write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(error_message) from conn_err
    except requests.exceptions.Timeout as timeout_err:
        error_message = f"Таймаут при подключении к API: {timeout_err}"
        write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(error_message) from timeout_err
    except requests.exceptions.RequestException as req_err:
        error_message = f"Ошибка запроса к API: {req_err}"
        write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(error_message) from req_err
    except ValueError as ve: # Ошибка декодирования Base64
        error_message = f"Ошибка декодирования Base64 ключа из API: {ve}"
        write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(error_message) from ve
    except Exception as e:
        error_message = f"Неожиданная ошибка в get_shared_aes_key: {e}"
        write_log(error_message, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(error_message) from e
# modules/api_client.py
"""
Модуль для работы с API сервера ElOrgEDS.
Получает общий AES-ключ.
"""

import requests
import base64
import urllib3
import yaml
import os

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
        print(f"[api_client] Попытка подключения к API по адресу '{url}' для получения общего AES-ключа...")
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
            raise RuntimeError(f"Decoded shared AES key is not 32 bytes long. Length: {len(key_bytes)} bytes.")

        print("[api_client] Общий AES-ключ (32 байта) успешно получен из API.")
        return key_bytes

    except requests.exceptions.SSLError as ssl_err:
        raise RuntimeError(f"Ошибка SSL при подключении к API: {ssl_err}") from ssl_err
    except requests.exceptions.ConnectionError as conn_err:
        raise RuntimeError(f"Ошибка подключения к API: {conn_err}") from conn_err
    except requests.exceptions.Timeout as timeout_err:
        raise RuntimeError(f"Таймаут при подключении к API: {timeout_err}") from timeout_err
    except requests.exceptions.RequestException as req_err:
        raise RuntimeError(f"Ошибка запроса к API: {req_err}") from req_err
    except ValueError as ve: # Ошибка декодирования Base64
        raise RuntimeError(f"Ошибка декодирования Base64 ключа из API: {ve}") from ve
    except Exception as e:
        raise RuntimeError(f"Неожиданная ошибка в get_shared_aes_key: {e}") from e

# --- ФУНКЦИЯ ЗАГРУЗКИ КОНФИГУРАЦИИ ---
def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    Загружает конфигурацию из YAML-файла.

    Args:
        config_path: Путь к файлу конфигурации.

    Returns:
        Словарь с конфигурацией.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ValueError("Файл конфигурации должен содержать словарь.")
        print(f"[api_client] Конфигурация успешно загружена из '{config_path}'.")
        return config
    except FileNotFoundError:
        raise RuntimeError(f"Файл конфигурации '{config_path}' не найден.")
    except yaml.YAMLError as ye:
        raise RuntimeError(f"Ошибка парсинга YAML в файле '{config_path}': {ye}") from ye
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки конфигурации из '{config_path}': {e}") from e
# --- /ФУНКЦИЯ ЗАГРУЗКИ КОНФИГУРАЦИИ ---
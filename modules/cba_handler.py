# ./modules/cba_handler.py
"""
Модуль для работы с .cba файлами.
Чтение, запись, шифрование/дешифрование паролей.
"""

import os

from settings import MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST, MODULE_LOG_FILE_ERROR
from . import crypto # Импортируем модуль crypto из того же папки
from .main_functions import write_log


def read_encrypted_cba(file_path: str, aes_key: bytes) -> str:
    """
    Читает зашифрованный пароль из .cba файла, дешифрует его и возвращает.
    Ожидается, что .cba файлы в кодировке UTF-8 с BOM.

    Args:
        file_path: Путь к .cba файлу.
        aes_key: 32-байтовый AES-ключ для дешифрования.

    Returns:
        Расшифрованный пароль.
    """
    try:
        if not os.path.exists(file_path):
            write_log(f"Файл '.cba' '{file_path}' не найден.", MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                      "error", MODULE_LOG_FILE_ERROR)
            raise FileNotFoundError(f"Файл '.cba' '{file_path}' не найден.")

        write_log(f"[cba_handler] Чтение зашифрованного пароля из .cba файла: '{file_path}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        # 1. Читаем содержимое файла (Base64-строка) в кодировке UTF-8 с BOM
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            encrypted_password_b64 = f.read().strip()

        if not encrypted_password_b64:
            write_log(f"Файл '.cba' '{file_path}' пуст.",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            raise ValueError(f"Файл '.cba' '{file_path}' пуст.")

        # 2. Дешифруем пароль
        write_log("[cba_handler] Дешифрование пароля...",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        decrypted_password = crypto.func_DecryptText_NEW(encrypted_password_b64, aes_key)

        write_log(f"[cba_handler] Пароль из файла '{file_path}' успешно прочитан и расшифрован.")
        return decrypted_password

    except Exception as e:
        write_log(f"Ошибка чтения/дешифрования .cba файла '{file_path}': {e}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
        raise RuntimeError(f"Ошибка чтения/дешифрования .cba файла '{file_path}': {e}") from e

def write_encrypted_cba(password: str, file_path: str, aes_key: bytes):
    """
    Шифрует пароль и записывает его в .cba файл.
    .cba файлы будут записываться в кодировке UTF-8 с BOM.

    Args:
        password: Пароль для шифрования.
        file_path: Путь, куда сохранить .cba файл.
        aes_key: 32-байтовый AES-ключ для шифрования.
    """
    try:
        # 1. Шифруем пароль
        write_log("[cba_handler] Шифрование пароля...",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        encrypted_password_b64 = crypto.func_EncryptText_NEW(password, aes_key)

        # 2. Записываем в файл в кодировке UTF-8 с BOM
        write_log(f"[cba_handler] Запись зашифрованного пароля в .cba файл: '{file_path}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            f.write(encrypted_password_b64)

        write_log(f"[cba_handler] Пароль успешно зашифрован и записан в файл '{file_path}' (UTF-8 с BOM).",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

    except Exception as e:
        write_log(f"Ошибка шифрования/записи .cba файла '{file_path}': {e}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
        raise RuntimeError(f"Ошибка шифрования/записи .cba файла '{file_path}': {e}") from e
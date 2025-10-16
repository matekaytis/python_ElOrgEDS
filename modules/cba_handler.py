# modules/cba_handler.py
"""
Модуль для работы с .cba файлами.
Чтение, запись, шифрование/дешифрование паролей.
"""

import os
from . import crypto # Импортируем модуль crypto из того же папки

def read_encrypted_cba(file_path: str, aes_key: bytes) -> str:
    """
    Читает зашифрованный пароль из .cba файла, дешифрует его и возвращает.

    Args:
        file_path: Путь к .cba файлу.
        aes_key: 32-байтовый AES-ключ для дешифрования.

    Returns:
        Расшифрованный пароль.
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл '.cba' '{file_path}' не найден.")

        print(f"[cba_handler] Чтение зашифрованного пароля из .cba файла: '{file_path}'...")
        # 1. Читаем содержимое файла (Base64-строка)
        with open(file_path, 'r', encoding='utf-8') as f:
            encrypted_password_b64 = f.read().strip()

        if not encrypted_password_b64:
            raise ValueError(f"Файл '.cba' '{file_path}' пуст.")

        # 2. Дешифруем пароль
        print("[cba_handler] Дешифрование пароля...")
        decrypted_password = crypto.func_DecryptText_NEW(encrypted_password_b64, aes_key)

        print(f"[cba_handler] Пароль из файла '{file_path}' успешно прочитан и расшифрован.")
        return decrypted_password

    except Exception as e:
        raise RuntimeError(f"Ошибка чтения/дешифрования .cba файла '{file_path}': {e}") from e

def write_encrypted_cba(password: str, file_path: str, aes_key: bytes):
    """
    Шифрует пароль и записывает его в .cba файл.

    Args:
        password: Пароль для шифрования.
        file_path: Путь, куда сохранить .cba файл.
        aes_key: 32-байтовый AES-ключ для шифрования.
    """
    try:
        # 1. Шифруем пароль
        print("[cba_handler] Шифрование пароля...")
        encrypted_password_b64 = crypto.func_EncryptText_NEW(password, aes_key)

        # 2. Записываем в файл
        print(f"[cba_handler] Запись зашифрованного пароля в .cba файл: '{file_path}'...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_password_b64)

        print(f"[cba_handler] Пароль успешно зашифрован и записан в файл '{file_path}'.")

    except Exception as e:
        raise RuntimeError(f"Ошибка шифрования/записи .cba файла '{file_path}': {e}") from e
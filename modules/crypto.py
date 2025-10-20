# ./modules/crypto.py
"""
Модуль для шифрования/дешифрования данных с использованием AES-256-CBC (.NET Framework совместимый).
Совместим с обновлёнными PowerShell-функциями func_EncryptText_NEW и func_DecryptText_NEW.
"""

import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from modules.main_functions import write_log
from settings import MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST, MODULE_LOG_FILE_ERROR

# --- НАСТРОЙКИ ---
# Размер блока AES (128 бит = 16 байт)
AES_BLOCK_SIZE_BYTES = 16
# Длина IV для CBC (16 байт)
AES_CBC_IV_LENGTH_BYTES = 16
# --- /НАСТРОЙКИ ---

# --- ФУНКЦИИ ШИФРОВАНИЯ/ДЕШИФРОВАНИЯ ---
# Data encrypt (NEW - AES-256-CBC, Python Compatible)
def func_EncryptText_NEW(plaintext: str, key: bytes) -> str:
    """
    Шифрует строку plaintext с использованием AES-256-CBC и возвращает Base64-строку.
    Формат: Base64(IV + Ciphertext)
    Совместим с PowerShell func_EncryptText_NEW (AES-256-CBC).

    Args:
        plaintext: Строка для шифрования.
        key: 32-байтовый ключ AES.

    Returns:
        Base64-строка, содержащая IV и зашифрованный текст.
    """
    if len(key) != 32:
        write_log("Ключ должен быть длиной 32 байта (256 бит) для AES-256-CBC.", MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
        raise ValueError("Ключ должен быть длиной 32 байта (256 бит) для AES-256-CBC.")

    try:
        # 1. Преобразуем строку в байты UTF-8
        plaintext_bytes = plaintext.encode('utf-8')

        # 2. Создаем AES объект (CBC)
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        backend = default_backend()
        # Генерируем случайный IV (16 байт для AES CBC)
        iv = os.urandom(16)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)

        # 3. Создаем шифратор
        # ИСПРАВЛЕНО: .encryptor() вместо .create_encryptor()
        encryptor = cipher.encryptor()

        # 4. Добавляем PKCS7 padding
        from cryptography.hazmat.primitives import padding
        padder = padding.PKCS7(128).padder() # 128 бит = 16 байт для AES
        padded_plaintext_bytes = padder.update(plaintext_bytes) + padder.finalize()

        # 5. Шифруем
        ciphertext = encryptor.update(padded_plaintext_bytes) + encryptor.finalize()

        # 6. Освобождаем ресурсы
        # ИСПРАВЛЕНО: Убраны .dispose(), так как в Python это не требуется
        # encryptor.dispose() # <-- УДАЛЕНО
        # cipher.dispose()   # <-- УДАЛЕНО

        # 7. Объединяем IV и Ciphertext
        combined_bytes = iv + ciphertext

        # 8. Кодируем в Base64
        encrypted_string = base64.b64encode(combined_bytes).decode('utf-8')

        return encrypted_string

    except Exception as e:
        write_log(f"Ошибка в func_EncryptText_NEW (AES-256-CBC): {e}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
        raise RuntimeError(f"Ошибка в func_EncryptText_NEW (AES-256-CBC): {e}") from e

# Decrypt data (NEW - AES-256-CBC, Python Compatible)
def func_DecryptText_NEW(encrypted_b64: str, key: bytes) -> str:
    """
    Дешифрует строку, зашифрованную func_EncryptText_NEW, с использованием AES-256-CBC.
    Формат: Base64(IV + Ciphertext)
    Совместим с PowerShell func_DecryptText_NEW (AES-256-CBC).

    Args:
        encrypted_b64: Base64-строка, содержащая IV + Ciphertext.
        key: 32-байтовый ключ AES.

    Returns:
        Расшифрованная строка UTF-8.
    """
    if len(key) != 32:
        write_log("Ключ должен быть длиной 32 байта (256 бит) для AES-256-CBC.", MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
        raise ValueError("Ключ должен быть длиной 32 байта (256 бит) для AES-256-CBC.")

    try:
        # 1. Декодируем Base64
        combined_bytes = base64.b64decode(encrypted_b64)

        # 2. Проверяем минимальную длину (IV 16 + хотя бы 1 блок 16 = 32 байта)
        if len(combined_bytes) < 32:
            write_log(f"Недостаточная длина данных для CBC (менее 32 байт). Длина: {len(combined_bytes)}", MODULE_LOG_FILE_ALL,
                      MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
            raise ValueError(f"Недостаточная длина данных для CBC (менее 32 байт). Длина: {len(combined_bytes)}")

        # 3. Извлекаем IV (первые 16 байт)
        iv = combined_bytes[:16]

        # 4. Извлекаем Ciphertext (остальное)
        ciphertext_length = len(combined_bytes) - 16
        ciphertext = combined_bytes[16:]

        # 5. Создаем AES объект (CBC)
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        backend = default_backend()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)

        # 6. Создаем дешифратор
        # ИСПРАВЛЕНО: .decryptor() вместо .create_decryptor()
        decryptor = cipher.decryptor()

        # 7. Дешифруем
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # 8. Освобождаем ресурсы
        # ИСПРАВЛЕНО: Убраны .dispose(), так как в Python это не требуется
        # decryptor.dispose() # <-- УДАЛЕНО
        # cipher.dispose()   # <-- УДАЛЕНО

        # 9. Удаляем PKCS7 padding
        from cryptography.hazmat.primitives import padding
        unpadder = padding.PKCS7(128).unpadder() # 128 бит = 16 байт для AES
        plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()

        # 10. Преобразуем байты в строку UTF-8
        decrypted_string = plaintext_bytes.decode('utf-8')

        return decrypted_string

    except Exception as e:
        write_log(f"Ошибка в func_DecryptText_NEW (AES-256-CBC): {e}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
        raise RuntimeError(f"Ошибка в func_DecryptText_NEW (AES-256-CBC): {e}") from e

# --- /ФУНКЦИИ ШИФРОВАНИЯ/ДЕШИФРОВАНИЯ ---

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С МАССИВАМИ ---
# Эти функции имитируют старый/новый func_EncryptArray/func_DecryptArray

def func_EncryptArray_NEW(data_csv: list[dict], aes_key: bytes) -> list[dict]:
    """
    Шифрует значения в списке словарей (как строки CSV) с использованием AES-256-CBC.
    """
    if not data_csv:
        return []

    columns = list(data_csv[0].keys()) if data_csv else []
    encrypted_array = []

    for row in data_csv:
        new_row = {}
        for col in columns:
            plain_value = row.get(col, "")
            if not isinstance(plain_value, str):
                plain_value = str(plain_value)
            if not plain_value:
                encrypted_value = ""
            else:
                try:
                    # ВАЖНО: Здесь должна быть вызвана РЕАЛЬНАЯ новая функция шифрования
                    encrypted_value = func_EncryptText_NEW(plain_value, aes_key)
                    if encrypted_value is None:
                        write_log("Шифрование новым методом вернуло None.",MODULE_LOG_FILE_ALL,
                                  MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
                        raise ValueError("Шифрование новым методом вернуло None.")
                except Exception as e:
                    write_log(f"Предупреждение: Ошибка шифрования для ячейки "
                              f"[{row.get('__index__', '?')}][{col}]: {e}", MODULE_LOG_FILE_ALL,
                              MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
                    raise ValueError(f"Ошибка шифрования для ячейки [{row.get('__index__', '?')}][{col}]: {e}")
                    # Продолжаем с пустым значением или останавливаем. Выберем продолжение.
                    encrypted_value = "" # Или пустая строка, в зависимости от логики
            new_row[col] = encrypted_value
        # Для отладки можно добавить индекс строки
        # new_row['__index__'] = data_csv.index(row)
        encrypted_array.append(new_row)

    return [row for row in encrypted_array if any(v for v in row.values() if v)] # Фильтруем пустые строки

def func_DecryptArray_NEW(data_csv: list[dict], aes_key: bytes) -> list[dict]:
    """
    Дешифрует значения в списке словарей (как строки CSV), зашифрованные AES-256-CBC.
    """
    if not data_csv:
        return []

    columns = list(data_csv[0].keys()) if data_csv else []
    decrypted_array = []

    for row in data_csv:
        new_row = {}
        for col in columns:
            encrypted_value = row.get(col, "")
            if not isinstance(encrypted_value, str) or not encrypted_value or encrypted_value.startswith("#"):
                decrypted_value = encrypted_value
            else:
                try:
                    # ВАЖНО: Здесь должна быть вызвана РЕАЛЬНАЯ новая функция дешифрования
                    decrypted_value = func_DecryptText_NEW(encrypted_value, aes_key)
                    if decrypted_value is None:
                        write_log("Дешифрование новым методом вернуло None.", MODULE_LOG_FILE_ALL,
                                  MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
                        raise ValueError("Дешифрование новым методом вернуло None.")
                except Exception as e:
                    write_log(f"Предупреждение: Ошибка дешифрования для ячейки "
                              f"[{row.get('__index__', '?')}][{col}]: {e}", MODULE_LOG_FILE_ALL,
                              MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
                    raise ValueError(f"Ошибка дешифрования для ячейки [{row.get('__index__', '?')}][{col}]: {e}")
                    # Продолжаем с пустым значением или останавливаем. Выберем продолжение.
                    decrypted_value = "" # Или пустая строка, в зависимости от логики
            new_row[col] = decrypted_value
        # Для отладки можно добавить индекс строки
        # new_row['__index__'] = data_csv.index(row)
        decrypted_array.append(new_row)

    return [row for row in decrypted_array if any(v for v in row.values() if v)] # Фильтруем пустые строки
# --- /ФУНКЦИИ ДЛЯ РАБОТЫ С МАССИВАМИ ---
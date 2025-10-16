# modules/crypto.py
"""
Модуль для шифрования/дешифрования данных с использованием AES-256-CBC (.NET Framework совместимый).
Совместим с обновлёнными PowerShell-функциями func_EncryptText_NEW и func_DecryptText_NEW.
"""

import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# --- НАСТРОЙКИ ---
# Размер блока AES (128 бит = 16 байт)
AES_BLOCK_SIZE_BYTES = 16
# Длина IV для CBC (16 байт)
AES_CBC_IV_LENGTH_BYTES = 16
# --- /НАСТРОЙКИ ---

# Data encrypt (NEW - AES-256-CBC, .NET Framework Compatible)
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
        raise ValueError("Ключ должен быть длиной 32 байта (256 бит) для AES-256-CBC.")

    try:
        # 1. Преобразуем строку в байты UTF-8
        plaintext_bytes = plaintext.encode('utf-8')

        # 2. Создаем AES объект (CBC)
        aes = Cipher(algorithms.AES(key), modes.CBC(), backend=default_backend())
        aes.algorithm.mode._initialization_vector = os.urandom(AES_CBC_IV_LENGTH_BYTES) # Устанавливаем IV

        # 3. Создаем шифратор
        encryptor = aes.create_encryptor()

        # 4. Добавляем PKCS7 padding
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_plaintext_bytes = padder.update(plaintext_bytes) + padder.finalize()

        # 5. Шифруем
        ciphertext = encryptor.update(padded_plaintext_bytes) + encryptor.finalize()

        # 6. Освобождаем ресурсы
        encryptor.dispose()
        aes.dispose()

        # 7. Объединяем IV и Ciphertext
        combined_bytes = aes.algorithm.mode._initialization_vector + ciphertext

        # 8. Кодируем в Base64
        encrypted_string = base64.b64encode(combined_bytes).decode('utf-8')

        return encrypted_string

    except Exception as e:
        raise RuntimeError(f"Ошибка в func_EncryptText_NEW (AES-256-CBC): {e}") from e

# Decrypt data (NEW - AES-256-CBC, .NET Framework Compatible)
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
        raise ValueError("Ключ должен быть длиной 32 байта (256 бит) для AES-256-CBC.")

    try:
        # 1. Декодируем Base64
        combined_bytes = base64.b64decode(encrypted_b64)

        # 2. Проверяем минимальную длину (IV 16 + хотя бы 1 блок 16 = 32 байта)
        if len(combined_bytes) < 32:
            raise ValueError(f"Недостаточная длина данных для CBC (менее 32 байт). Длина: {len(combined_bytes)}")

        # 3. Извлекаем IV (первые 16 байт)
        iv = combined_bytes[:AES_CBC_IV_LENGTH_BYTES]

        # 4. Извлекаем Ciphertext (остальное)
        ciphertext_length = len(combined_bytes) - AES_CBC_IV_LENGTH_BYTES
        ciphertext = combined_bytes[AES_CBC_IV_LENGTH_BYTES:]

        # 5. Создаем AES объект (CBC)
        aes = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

        # 6. Создаем дешифратор
        decryptor = aes.create_decryptor()

        # 7. Дешифруем
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # 8. Освобождаем ресурсы
        decryptor.dispose()
        aes.dispose()

        # 9. Удаляем PKCS7 padding
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()

        # 10. Преобразуем байты в строку UTF-8
        decrypted_string = plaintext_bytes.decode('utf-8')

        return decrypted_string

    except Exception as e:
        raise RuntimeError(f"Ошибка в func_DecryptText_NEW (AES-256-CBC): {e}") from e

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
                         raise ValueError("Шифрование новым методом вернуло None.")
                except Exception as e:
                     print(f"Предупреждение: Ошибка шифрования для ячейки [{row.get('__index__', '?')}][{col}]: {e}")
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
            if not isinstance(encrypted_value, str):
                encrypted_value = str(encrypted_value)
            if not encrypted_value:
                decrypted_value = ""
            else:
                try:
                    # ВАЖНО: Здесь должна быть вызвана РЕАЛЬНАЯ новая функция дешифрования
                    decrypted_value = func_DecryptText_NEW(encrypted_value, aes_key)
                    if decrypted_value is None:
                         raise ValueError("Дешифрование новым методом вернуло None.")
                except Exception as e:
                    print(f"Предупреждение: Ошибка дешифрования для ячейки [{row.get('__index__', '?')}][{col}]: {e}")
                    # Продолжаем с пустым значением или останавливаем. Выберем продолжение.
                    decrypted_value = "" # Или пустая строка, в зависимости от логики
            new_row[col] = decrypted_value
        # Для отладки можно добавить индекс строки
        # new_row['__index__'] = data_csv.index(row)
        decrypted_array.append(new_row)

    return [row for row in decrypted_array if any(v for v in row.values() if v)] # Фильтруем пустые строки
# --- /ФУНКЦИИ ДЛЯ РАБОТЫ С МАССИВАМИ ---
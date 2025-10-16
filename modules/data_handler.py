# modules/data_handler.py
"""
Модуль для работы с CSV-файлами.
Чтение, запись, шифрование/дешифрование данных.
"""

import pandas as pd
import os
from . import crypto # Импортируем модуль crypto из того же папки

def read_encrypted_csv(file_path: str, aes_key: bytes) -> pd.DataFrame:
    """
    Читает зашифрованный CSV-файл, дешифрует его и возвращает DataFrame.

    Args:
        file_path: Путь к зашифрованному CSV-файлу.
        aes_key: 32-байтовый AES-ключ для дешифрования.

    Returns:
        DataFrame с расшифрованными данными.
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл '{file_path}' не найден.")

        print(f"[data_handler] Чтение зашифрованного CSV-файла: '{file_path}'...")
        # 1. Читаем CSV в DataFrame
        df_encrypted = pd.read_csv(file_path, encoding='utf-8')

        # 2. Преобразуем DataFrame в список словарей
        data_csv_list = df_encrypted.to_dict('records')

        # 3. Дешифруем массив
        print("[data_handler] Дешифрование данных...")
        data_decrypted_list = crypto.func_DecryptArray_NEW(data_csv_list, aes_key)

        # 4. Преобразуем обратно в DataFrame
        df_decrypted = pd.DataFrame(data_decrypted_list)

        print(f"[data_handler] Файл '{file_path}' успешно прочитан и расшифрован. Количество строк: {len(df_decrypted)}.")
        return df_decrypted

    except Exception as e:
        raise RuntimeError(f"Ошибка чтения/дешифрования CSV-файла '{file_path}': {e}") from e

def write_encrypted_csv(df: pd.DataFrame, file_path: str, aes_key: bytes):
    """
    Шифрует данные из DataFrame и записывает их в зашифрованный CSV-файл.

    Args:
        df: DataFrame с данными для шифрования.
        file_path: Путь, куда сохранить зашифрованный CSV-файл.
        aes_key: 32-байтовый AES-ключ для шифрования.
    """
    try:
        # 1. Преобразуем DataFrame в список словарей
        data_csv_list = df.to_dict('records')

        # 2. Шифруем массив
        print("[data_handler] Шифрование данных...")
        data_encrypted_list = crypto.func_EncryptArray_NEW(data_csv_list, aes_key)

        # 3. Преобразуем обратно в DataFrame
        df_encrypted = pd.DataFrame(data_encrypted_list)

        # 4. Записываем в CSV
        print(f"[data_handler] Запись зашифрованного CSV-файла: '{file_path}'...")
        df_encrypted.to_csv(file_path, index=False, encoding='utf-8')
        print(f"[data_handler] Файл '{file_path}' успешно зашифрован и записан.")

    except Exception as e:
        raise RuntimeError(f"Ошибка шифрования/записи CSV-файла '{file_path}': {e}") from e
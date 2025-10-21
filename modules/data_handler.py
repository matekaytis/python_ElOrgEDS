# ./modules/data_handler.py
"""
Модуль для работы с CSV-файлами.
Чтение, запись, шифрование/дешифрование данных.
"""
import os
import sys

import pandas as pd

from settings import MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST, MODULE_LOG_FILE_ERROR
from . import crypto  # Импортируем модуль crypto из того же папки
from .main_functions import write_log
from .notifications import show_popup_notification


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
            write_log(f"Файл '{file_path}' не найден.",MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            raise FileNotFoundError(f"Файл '{file_path}' не найден.")

        write_log(f"[data_handler] Чтение зашифрованного CSV-файла: '{file_path}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        # 1. Читаем CSV в DataFrame
        df_encrypted = pd.read_csv(file_path, encoding='utf-8', skiprows=1)

        # 2. Преобразуем DataFrame в список словарей
        data_csv_list = df_encrypted.to_dict('records')

        # 3. Дешифруем массив
        write_log("[data_handler] Дешифрование данных...",MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        data_decrypted_list = crypto.func_DecryptArray_NEW(data_csv_list, aes_key)

        # 4. Преобразуем обратно в DataFrame
        df_decrypted = pd.DataFrame(data_decrypted_list)
        df_arm_clean = df_decrypted.dropna(how="all")
        if df_arm_clean.empty:
            raise ValueError("[data_handler] CSV не содержит строк с реальными данными: все строки пустые или полностью NULL.")

        write_log(f"[data_handler] Файл '{file_path}' успешно прочитан и расшифрован. "
                  f"Количество строк: {len(df_decrypted)}.", MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        return df_decrypted

    except Exception as e:
        error_message = f"[data_handler] Ошибка чтения/дешифрования CSV-файла '{file_path}': {e}"
        write_log(error_message, MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error", MODULE_LOG_FILE_ERROR)
        # raise RuntimeError(f"Ошибка чтения/дешифрования CSV-файла '{file_path}': {e}") from e
        show_popup_notification(
            "MODULE_FILE",
            error_message,
            "critical",  # ← бесконечное уведомление
            0
        )
        sys.exit(1)

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
        write_log("[data_handler] Шифрование данных...", MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        data_encrypted_list = crypto.func_EncryptArray_NEW(data_csv_list, aes_key)

        # 3. Преобразуем обратно в DataFrame
        df_encrypted = pd.DataFrame(data_encrypted_list)

        # 4. Записываем в CSV
        write_log(f"[data_handler] Запись зашифрованного CSV-файла: '{file_path}'...",
                  MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        df_encrypted.to_csv(file_path, index=False, encoding='utf-8')
        write_log(f"[data_handler] Файл '{file_path}' успешно зашифрован и записан.",
                  MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)

    except Exception as e:
        error_message = f"[data_handler] Ошибка шифрования/записи CSV-файла '{file_path}': {e}"
        write_log(error_message, MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,"error", MODULE_LOG_FILE_ERROR)
        show_popup_notification(
            "MODULE_FILE",
            error_message,
            "critical",  # ← бесконечное уведомление
            0
        )
        sys.exit(1)
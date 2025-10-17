# ElOrgEDS_ARM_silent.py
"""
Основной скрипт для автоматического режима клиента ElOrgEDS (Python/Linux).
"""

import os
import shutil
import subprocess
import sys

from contextlib import redirect_stderr

from settings import (SILENT_LOG_FILE_ALL, SILENT_LOG_FILE_LAST, SILENT_LOG_FILE_ERROR, SCRIPT_DIR, DATA_DIR,
                      SHARED_DIR, SHARED_NETWORK_PATH, LOGS_DIR, TEST_CBA, TEST_CSV, API_URL, API_TOKEN,
                      MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST, MODULE_LOG_FILE_ERROR, LOCK_FILE_SILENT)

from modules import api_client, data_handler, cba_handler, exceptions
from modules.main_functions import write_log, is_network_share_accessible, update_log, is_folder_not_empty, \
    ensure_mounted, prevent_multiple_instances, get_files_info, save_to_csv, clear_folder_files

# Принудительно использовать X11 вместо Wayland
if "WAYLAND_DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
from modules.notifications import show_popup_notification

# --- /НАСТРОЙКИ ---
TITLE_APP = "'ElOrgEDS ARM - тихий режим'"

# --- НАЧАЛО ЛОГИРОВАНИЯ ---
# Очистка/создание лог-файла
update_log(SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST,SILENT_LOG_FILE_ERROR)
update_log(MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,MODULE_LOG_FILE_ERROR)

write_log("==========================================",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log(f" {TITLE_APP} (Python/Linux)",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log("==========================================",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
prevent_multiple_instances(LOCK_FILE_SILENT)
write_log(f"Блокировка повторного запуска {TITLE_APP} успешно установлена",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log(f"Путь к скрипту: {SCRIPT_DIR}",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log(f"Путь к данным: {DATA_DIR}",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log(f"Путь к полученным данным: {SHARED_DIR}",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log(f"Путь к общим данным: {SHARED_NETWORK_PATH}",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log(f"Путь к логам: {LOGS_DIR}",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
write_log("------------------------------------------",
          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
# --- /НАЧАЛО ЛОГИРОВАНИЯ ---



# --- ГЛАВНАЯ ЛОГИКА ElOrgEDS ARM - тихий режим ---
def main():
    """Главная функция silent-режима."""
    try:
        # --- УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ ---
        start_message = "Программа начала работу. Дождитесь уведомления об успешном завершении работы."
        show_popup_notification(
            TITLE_APP,
            start_message,
            "normal",
            15000
        )
        write_log(f"Путь к общей сетевой папке из конфига: {SHARED_NETWORK_PATH}",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)

        # 1. Получение общего AES-ключа из API
        write_log("Получение общего AES-ключа из API...",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
        shared_aes_key = api_client.get_shared_aes_key(API_URL, API_TOKEN, verify_ssl=False)
        write_log(f"Общий AES-ключ успешно получен. Длина: {len(shared_aes_key)} байт.",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)

        # 2. Основные действия программы (пример)
        write_log("Начало основной логики ElOrgEDS ARM - тихий режим...",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
        write_log("------------------------------------------",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)

        ensure_mounted()

        # Убедитесь, что целевая папка существует
        if not is_network_share_accessible(SHARED_NETWORK_PATH, timeout=5.0):
            error_message = "Нет доступа к сетевой папке, проверьте доступ!"
            write_log(error_message,SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST,"error",SILENT_LOG_FILE_ERROR)
            raise exceptions.NetworkAccessError(error_message)

        # Убедитесь, что целевая папка не пустая
        if not is_folder_not_empty(SHARED_NETWORK_PATH):
            error_message = "Сетевая папка пустая!"
            write_log(error_message, SILENT_LOG_FILE_ALL, SILENT_LOG_FILE_LAST, "error", SILENT_LOG_FILE_ERROR)
            raise exceptions.NetworkAccessError(error_message)

        write_log(f"Началось копирование данных в папку {SHARED_DIR}",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)

        # Очищаем всё содержимое в SHARED_DIR
        clear_folder_files(SHARED_DIR)

        # Копируем всё содержимое SHARED_NETWORK_DIR в SHARED_DIR
        for item in os.listdir(SHARED_NETWORK_PATH):
            s = os.path.join(SHARED_NETWORK_PATH, item)
            d = os.path.join(SHARED_DIR, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)  # dirs_exist_ok=True — для Python 3.8+
            else:
                shutil.copy2(s, d)
        write_log(f"Закончилось копирование данных в папку {SHARED_DIR}",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
        info_files = get_files_info(SHARED_DIR)
        output_csv = os.path.join(SCRIPT_DIR,"test","info_files.csv")
        save_to_csv(info_files,output_csv)
        write_log(f"Информация о {len(info_files)} файлах сохранена в {output_csv}",
                  SILENT_LOG_FILE_ALL, SILENT_LOG_FILE_LAST)

        # Пример: Чтение и дешифрование DB_InfoARM.csv
        db_info_arm_path = os.path.join(SHARED_DIR, "DB_InfoARM.csv")
        if os.path.exists(db_info_arm_path):
            write_log(f"Чтение и дешифрование '{db_info_arm_path}'...")
            try:
                df_arm = data_handler.read_encrypted_csv(db_info_arm_path, shared_aes_key)
                # Здесь можно добавить логику обработки df_arm
                df_arm.to_csv(TEST_CSV, index=False, encoding='utf-8')
                write_log(f"Файл '{db_info_arm_path}' успешно прочитан и расшифрован. "
                          f"Количество записей: {len(df_arm)}",SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
            except Exception as e:
                write_log(f"Ошибка при чтении/дешифровании '{db_info_arm_path}': {e}",SILENT_LOG_FILE_ALL,
                          SILENT_LOG_FILE_LAST,"error",SILENT_LOG_FILE_ERROR)
        else:
             write_log(f"Файл '{db_info_arm_path}' не найден. Пропущен.",SILENT_LOG_FILE_ALL,
                       SILENT_LOG_FILE_LAST,"error",SILENT_LOG_FILE_ERROR)

        # Пример: Чтение и дешифрование .cba файла
        # Предположим, у нас есть файл 2A5E7E091D5A403157DAAF996EF315DB.cba
        # example_cba_filename = "2A5E7E091D5A403157DAAF996EF315DB.cba"
        # example_cba_path = os.path.join(SHARED_DIR,"1C", example_cba_filename)
        # if os.path.exists(example_cba_path):
        #     write_log(f"Чтение и дешифрование '{example_cba_path}'...")
        #     try:
        #         pwd_from_cba = cba_handler.read_encrypted_cba(example_cba_path, shared_aes_key)
        #         with open(TEST_CBA, 'w', encoding='utf-8') as f2:
        #             f2.write(pwd_from_cba)
        #         write_log(f"Пароль из '{example_cba_filename}' успешно прочитан и расшифрован.")
        #         # Здесь можно использовать пароль, например, для распаковки .7z архива
        #     except Exception as e:
        #         write_log(f"Ошибка при чтении/дешифровании '{example_cba_path}': {e}")
        # else:
        #      write_log(f"Файл '{example_cba_path}' не найден. Пропущен.")

        # --- /ОСНОВНАЯ ЛОГИКА ElOrgEDS ARM - тихий режим ---
        write_log("------------------------------------------",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
        write_log(f"Выполнение {TITLE_APP} успешно завершено.",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
        write_log("==========================================",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)

        # --- УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ ---
        final_message = "Программа завершена успешно."
        show_popup_notification(
            TITLE_APP,
            final_message,
            "normal",
            15000
        )
        # --- /УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ ---

    except Exception as e:
        error_message = f"КРИТИЧЕСКАЯ ОШИБКА: {e}"
        write_log(error_message,SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST,"error",SILENT_LOG_FILE_ERROR)
        # В реальном приложении здесь можно отправить уведомление, записать в системный лог и т.д.
        show_popup_notification(
            TITLE_APP,
            error_message,
            "critical",  # ← бесконечное уведомление
            0
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
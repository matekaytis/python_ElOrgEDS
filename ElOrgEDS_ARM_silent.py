# ./ElOrgEDS_ARM_silent.py
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

from modules import api_client, data_handler, cba_handler, exceptions, server_sync
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

        # --- НОВОЕ: СИНХРОНИЗАЦИЯ ДАННЫХ С СЕРВЕРОМ ---
        write_log("Начало синхронизации данных с сервером...",
                  SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
        try:
            # Передаем ТОЛЬКО ключ, все остальные параметры берутся из settings.py
            server_sync.func_LoadingDataThisServer(shared_aes_key)
            if server_sync.global_ResultSynchServer == 1:
                write_log("Синхронизация данных с сервером успешно завершена.",
                          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
                write_log(f"Область применения для этого ПК: {server_sync.global_MyAccessApp}",
                          SILENT_LOG_FILE_ALL,SILENT_LOG_FILE_LAST)
            else:
                write_log("Синхронизация данных с сервером НЕ УДАЛАСЬ.",SILENT_LOG_FILE_ALL,
                          SILENT_LOG_FILE_LAST,"error",SILENT_LOG_FILE_ERROR)
                # В зависимости от логики, можно выйти или продолжить
                sys.exit(1)
        except Exception as e:
            write_log(f"Ошибка синхронизации данных с сервером: {e}",SILENT_LOG_FILE_ALL,
                      SILENT_LOG_FILE_LAST,"error",SILENT_LOG_FILE_ERROR)
            sys.exit(1)
        # --- /НОВОЕ: СИНХРОНИЗАЦИЯ ДАННЫХ С СЕРВЕРОМ ---

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
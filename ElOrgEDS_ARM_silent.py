# ElOrgEDS_ARM_silent.py
"""
Основной скрипт для автоматического режима клиента ElOrgEDS (Python/Linux).
"""

import os
import shutil
import subprocess
import sys

from contextlib import redirect_stderr
from settings import (SILENT_LOG_FILE, SCRIPT_DIR, DATA_DIR, SHARED_DIR,
                      SHARED_NETWORK_PATH, LOGS_DIR, TEST_CBA, TEST_CSV, API_URL, API_TOKEN, MODULE_LOG_FILE)

from modules import api_client, data_handler, cba_handler, exceptions
from modules.main_functions import write_log, is_network_share_accessible
# Принудительно использовать X11 вместо Wayland
if "WAYLAND_DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
from modules.notifications import show_popup_notification


# --- /НАСТРОЙКИ ---
TITLE_APP = "ElOrgEDS ARM - тихий режим"

# --- НАЧАЛО ЛОГИРОВАНИЯ ---
# Очистка/создание лог-файла
if os.path.exists(SILENT_LOG_FILE):
    with open(SILENT_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("") # Очищаем файл
else:
    os.makedirs(os.path.dirname(SILENT_LOG_FILE), exist_ok=True)
    with open(SILENT_LOG_FILE, "w", encoding="utf-8") as f:
        pass # Создаем пустой файл

if not os.path.exists(MODULE_LOG_FILE):
    os.makedirs(os.path.dirname(MODULE_LOG_FILE), exist_ok=True)
    with open(MODULE_LOG_FILE, "w", encoding="utf-8") as f:
        pass  # Создаем пустой файл

write_log("==========================================",SILENT_LOG_FILE)
write_log(f" {TITLE_APP} (Python/Linux)",SILENT_LOG_FILE)
write_log("==========================================",SILENT_LOG_FILE)
write_log(f"Путь к скрипту: {SCRIPT_DIR}",SILENT_LOG_FILE)
write_log(f"Путь к данным: {DATA_DIR}",SILENT_LOG_FILE)
write_log(f"Путь к полученным данным: {SHARED_DIR}",SILENT_LOG_FILE)
write_log(f"Путь к общим данным: {SHARED_NETWORK_PATH}",SILENT_LOG_FILE)
write_log(f"Путь к логам: {LOGS_DIR}",SILENT_LOG_FILE)
write_log("------------------------------------------",SILENT_LOG_FILE)
# --- /НАЧАЛО ЛОГИРОВАНИЯ ---



# --- ГЛАВНАЯ ЛОГИКА SILENT MODE ---
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
        # --- /УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ ---
        # 1. Загрузка конфигурации
        write_log("Загрузка конфигурации...",SILENT_LOG_FILE)
        # paths = config.get('paths', {}) # Можно использовать, если нужно
        write_log(f"Путь к общей сетевой папке из конфига: {SHARED_NETWORK_PATH}",SILENT_LOG_FILE)

        # 2. Получение общего AES-ключа из API
        write_log("Получение общего AES-ключа из API...",SILENT_LOG_FILE)
        shared_aes_key = api_client.get_shared_aes_key(API_URL, API_TOKEN, verify_ssl=False)
        write_log(f"Общий AES-ключ успешно получен. Длина: {len(shared_aes_key)} байт.",SILENT_LOG_FILE)

        # 3. Основные действия программы (пример)
        write_log("Начало основной логики silent mode...",SILENT_LOG_FILE)
        write_log("------------------------------------------",SILENT_LOG_FILE)

        # Убедитесь, что целевая папка существует
        if is_network_share_accessible(SHARED_NETWORK_PATH, timeout=5.0):
            pass
        else:
            raise exceptions.NetworkAccessError("Нет доступа к сетевой папке, проверьте доступ!")
        write_log(f"Началось копирование данных в папку {SHARED_DIR}",SILENT_LOG_FILE)

        # Копируем всё содержимое SHARED_NETWORK_DIR в SHARED_DIR
        for item in os.listdir(SHARED_NETWORK_PATH):
            s = os.path.join(SHARED_NETWORK_PATH, item)
            d = os.path.join(SHARED_DIR, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)  # dirs_exist_ok=True — для Python 3.8+
            else:
                shutil.copy2(s, d)
        write_log(f"Закончилось копирование данных в папку {SHARED_DIR}",SILENT_LOG_FILE)

        # Пример: Чтение и дешифрование DB_InfoARM.csv
        # db_info_arm_path = os.path.join(SHARED_DIR, "DB_InfoARM.csv")
        # if os.path.exists(db_info_arm_path):
        #     write_log(f"Чтение и дешифрование '{db_info_arm_path}'...")
        #     try:
        #         df_arm = data_handler.read_encrypted_csv(db_info_arm_path, shared_aes_key)
        #         df_arm.to_csv(TEST_CSV, index=False, encoding='utf-8')
        #         write_log(f"Файл '{db_info_arm_path}' успешно прочитан и расшифрован. Количество записей: {len(df_arm)}")
        #         # Здесь можно добавить логику обработки df_arm
        #     except Exception as e:
        #         write_log(f"Ошибка при чтении/дешифровании '{db_info_arm_path}': {e}")
        # else:
        #      write_log(f"Файл '{db_info_arm_path}' не найден. Пропущен.")

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

        # --- /ОСНОВНАЯ ЛОГИКА SILENT MODE ---
        write_log("------------------------------------------",SILENT_LOG_FILE)
        write_log(f"{TITLE_APP} завершен.",SILENT_LOG_FILE)
        write_log("==========================================",SILENT_LOG_FILE)

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
        write_log(error_message,SILENT_LOG_FILE)
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
# modules/server_sync.py
"""
Модуль для синхронизации данных с серверной сетевой папкой.
Реализует функцию func_LoadingDataThisServer из PowerShell.
"""

import os
import shutil
import subprocess
from sys import exception

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import ipaddress
import socket

import modules.exceptions
# --- ИМПОРТ НАСТРОЕК ИЗ settings.py ---
# Предполагается, что settings.py находится в корне проекта
# и содержит переменные: SHARED_NETWORK_PATH, NAME_NET_INTERFACE, MASK_NET
from settings import (SHARED_NETWORK_PATH, NAME_NET_INTERFACE, MASK_NET, SCRIPT_DIR, MODULE_LOG_FILE_ALL,
                      MODULE_LOG_FILE_LAST, MODULE_LOG_FILE_ERROR, DATA_DIR, SHARED_DIR)
# --- /ИМПОРТ НАСТРОЕК ---

from . import crypto, data_handler # Импортируем модули из того же пакета
from .main_functions import write_log, is_network_share_accessible, clear_folder_files
from .notifications import show_popup_notification

# --- НАСТРОЙКИ ---
# Глобальные переменные для хранения результата
global_ResultSynchServer: int = 0 # 1 = успех, 0 = неудача
global_MyAccessApp: str = "" # AreaApp из DB_InfoARM.csv

# --- /НАСТРОЙКИ ---

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_local_ip_address(name_net: str, mask_net: str) -> str:
    """
    Получает IP-адрес локальной машины, используя имя интерфейса или маску сети.
    Имитирует логику PowerShell: Get-NetIPAddress | Where-Object InterfaceAlias -Match "$NameNet"

    Args:
        name_net: Имя сетевого интерфейса (например, "eth0").
        mask_net: Маска сети (например, "192.168.140.").

    Returns:
        IP-адрес в формате строки.
    """
    try:
        # 1. Получаем список сетевых интерфейсов и их IP-адресов
        # Используем `hostname -i` или `ip addr` (в зависимости от дистрибутива)
        write_log("[server_sync] Получение IP-адресов через hostname -i...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        result = subprocess.run(['hostname', '-i'], capture_output=True, text=True, check=True)
        ip_addresses = result.stdout.strip().split()

        if not ip_addresses:
            # Альтернатива: используем socket.gethostbyname(socket.gethostname())
            write_log("[server_sync] hostname -I не вернул адресов, пробуем socket.gethostbyname...",
                      MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
            hostname = socket.gethostname()
            ip_addresses = [socket.gethostbyname(hostname)]
            if not ip_addresses or ip_addresses == ['127.0.0.1']:
                 raise RuntimeError("Не удалось получить IP-адреса.")

        write_log(f"[server_sync] Найденные IP-адреса: {ip_addresses}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 2. Фильтруем по имени интерфейса (если указано)
        # На Linux это сложно сделать напрямую через hostname -I.
        # name_net в Linux это имя интерфейса (eth0, wlan0 и т.д.)
        # hostname -I не дает имя интерфейса.
        # Можно использовать `ip addr show dev <name_net>` если name_net указан.
        if name_net:
            write_log(f"[server_sync] Фильтрация по имени интерфейса '{name_net}'...",
                      MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
            try:
                # Получаем IP для конкретного интерфейса
                result_dev = subprocess.run(['ip', 'addr', 'show', 'dev', name_net],
                                            capture_output=True, text=True, check=True)
                # Простой парсинг вывода `ip addr` для извлечения IPv4
                import re
                ipv4_matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)/\d+', result_dev.stdout)
                if ipv4_matches:
                    ip_addresses = ipv4_matches
                    write_log(f"[server_sync] IP-адреса для интерфейса '{name_net}': {ip_addresses}",
                              MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
                else:
                    write_log(f"[server_sync] Не найдено IPv4 адресов для интерфейса '{name_net}'.",
                               MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
                    raise modules.exceptions.NetworkSettingsError(f"[server_sync] Не найдено IPv4 адресов "
                                                                  f"для интерфейса '{name_net}'.")
            except subprocess.CalledProcessError:
                 write_log(f"[server_sync] Ошибка при получении IP для интерфейса "
                           f"'{name_net}' через `ip addr`. Используются все найденные адреса.",
                           MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)

        # 3. Фильтруем по маске сети (если указана)
        if mask_net:
            write_log(f"[server_sync] Фильтрация по маске сети '{mask_net}'...",
                      MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
            filtered_ips = [ip for ip in ip_addresses if ip.startswith(mask_net)]
            if len(filtered_ips) == 1:
                write_log(f"[server_sync] Найден единственный IP, соответствующий маске: {filtered_ips[0]}",
                          MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
                return filtered_ips[0]
            elif len(filtered_ips) > 1:
                # Если несколько IP соответствуют маске, выбираем первый
                write_log(f"[server_sync] Предупреждение: Найдено несколько IP-адресов, "
                          f"соответствующих маске '{mask_net}'. Выбран первый: '{filtered_ips[0]}'.",
                          MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
                return filtered_ips[0]
            else:
                write_log(f"[server_sync] Предупреждение: Ни один IP-адрес не соответствует маске "
                          f"'{mask_net}'. Проверка всех адресов.",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
                # Продолжаем с первым из всех найденных
                return ip_addresses[0] if ip_addresses else "127.0.0.1"

        # 4. Если маска не указана, возвращаем первый IP
        write_log(f"[server_sync] Маска сети не указана. Возвращаем первый найденный IP: "
                  f"{ip_addresses[0] if ip_addresses else '127.0.0.1'}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        return ip_addresses[0] if ip_addresses else "127.0.0.1"

    except subprocess.CalledProcessError as cpe:
        write_log(f"[server_sync] Ошибка вызова hostname -I или ip addr: {cpe}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
        raise RuntimeError(f"Ошибка вызова hostname -I или ip addr: {cpe}") from cpe
    except Exception as e:
        write_log(f"[server_sync] Ошибка получения локального IP-адреса: {e}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
        raise RuntimeError(f"Ошибка получения локального IP-адреса: {e}") from e

def edit_access(data_access: str) -> str:
    """
    Редактирует значение AreaApp, заменяя специальные названия на стандартные.
    Имитирует логику PowerShell функции EditAccess.

    Args:
        data_access: Исходное значение AreaApp.

    Returns:
        Отредактированное значение AreaApp.
    """
    # Убираем пробелы в начале и конце
    data_access = data_access.strip()

    # Заменяем специальные названия
    access_map = {
        "1C-Отчетность": "1C",
        "АИС БП-ЭК": "AISBP-EK",
        "ЕИС или ГМУ": "EIS",
        "СБИС": "SBIS"
    }

    return access_map.get(data_access, data_access) # Возвращаем оригинальное значение, если совпадений нет

def split_area_app(area_app_str: str, delimiter: str = ";") -> List[str]:
    """
    Разделяет строку AreaApp по разделителю и редактирует каждую часть.

    Args:
        area_app_str: Строка с AreaApp, разделёнными delimiter.
        delimiter: Разделитель (по умолчанию ";").

    Returns:
        Список отредактированных AreaApp.
    """
    if not area_app_str:
        return []

    parts = area_app_str.split(delimiter)
    edited_parts = []
    for part in parts:
        part = part.strip()
        if part: # Игнорируем пустые части
            edited_part = edit_access(part)
            edited_parts.append(edited_part)
    return edited_parts

# --- /ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

# --- ОСНОВНАЯ ФУНКЦИЯ СИНХРОНИЗАЦИИ ---
def func_LoadingDataThisServer(aes_key: bytes):
    """
    Синхронизирует данные с серверной сетевой папкой.
    Реализует логику func_LoadingDataThisServer из PowerShell.

    Args:
        aes_key: 32-байтовый общий AES-ключ.
    """
    global global_ResultSynchServer, global_MyAccessApp

    try:
        write_log("[server_sync] Начало синхронизации данных с сервером...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        write_log("------------------------------------------",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 1. Загрузка конфигурации из settings.py (уже импортирована)
        write_log("[server_sync] Загрузка конфигурации из settings.py...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        write_log(f"[server_sync] SHARED_NETWORK_PATH из settings.py: {SHARED_NETWORK_PATH}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        write_log(f"[server_sync] NAME_NET_INTERFACE из settings.py: {NAME_NET_INTERFACE}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        write_log(f"[server_sync] MASK_NET из settings.py: {MASK_NET}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 2. Получение IP-адреса локальной машины
        pc_ip = get_local_ip_address(NAME_NET_INTERFACE,MASK_NET)
        write_log(f"[server_sync] Локальный IP-адрес: {pc_ip}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 3. Проверка доступности общей сетевой папки
        write_log(f"[server_sync] Проверка доступности общей сетевой папки: '{SHARED_NETWORK_PATH}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        if not is_network_share_accessible(SHARED_NETWORK_PATH):
             error_msg = f"Общая сетевая папка '{SHARED_NETWORK_PATH}' недоступна."
             write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                       "error",MODULE_LOG_FILE_ERROR)
             raise RuntimeError(error_msg)

        write_log(f"[server_sync] Общая сетевая папка '{SHARED_NETWORK_PATH}' доступна.",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 4. Определение путей (уже импортированы из settings.py)
        write_log(f"[server_sync] Путь к данным: {DATA_DIR}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        write_log(f"[server_sync] Путь к полученным данным: {SHARED_DIR}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 5. Очистка локальной папки shared
        write_log(f"[server_sync] Очистка локальной папки shared: '{SHARED_DIR}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        if os.path.exists(SHARED_DIR):
            clear_folder_files(SHARED_DIR)
        else:
            os.makedirs(SHARED_DIR, exist_ok=True)
        write_log(f"[server_sync] Локальная папка shared очищена/создана.", "info")

        # 6. Копирование данных из общей сетевой папки в локальную shared
        write_log(f"[server_sync] Копирование данных из общей сетевой папки '{SHARED_NETWORK_PATH}'"
                  f" в локальную '{SHARED_DIR}'...",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        try:
            # Используем shutil.copytree для рекурсивного копирования
            # Но copytree требует, чтобы целевая папка НЕ существовала
            # Поэтому используем distutils.dir_util.copy_tree или просто копируем содержимое
            for item in os.listdir(SHARED_NETWORK_PATH):
                s = os.path.join(SHARED_NETWORK_PATH, item)
                d = os.path.join(SHARED_DIR, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)
                    write_log(f"[server_sync]   -> Скопирован файл: '{item}'",MODULE_LOG_FILE_ALL,
                              MODULE_LOG_FILE_LAST)
                elif os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                    write_log(f"[server_sync]   -> Скопирована папка: '{item}'",MODULE_LOG_FILE_ALL,
                              MODULE_LOG_FILE_LAST)
        except Exception as e:
            error_msg = f"Ошибка копирования данных из общей сетевой папки: {e}"
            write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            raise RuntimeError(error_msg) from e
        write_log(f"[server_sync] Данные успешно скопированы.",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 7. Чтение и дешифрование DB_InfoARM.csv
        db_info_arm_path = os.path.join(SHARED_DIR, "DB_InfoARM.csv")
        write_log(f"[server_sync] Чтение и дешифрование '{db_info_arm_path}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        if not os.path.exists(db_info_arm_path):
            error_msg = f"Файл 'DB_InfoARM.csv' не найден в общей сетевой папке '{SHARED_NETWORK_PATH}'."
            write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            raise FileNotFoundError(error_msg)

        try:
            # Используем data_handler для чтения и дешифрования CSV
            df_arm = data_handler.read_encrypted_csv(db_info_arm_path, aes_key)
            write_log(f"[server_sync] Файл 'DB_InfoARM.csv' успешно прочитан и расшифрован. "
                      f"Количество записей: {len(df_arm)}.",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        except Exception as e:
            error_msg = f"Ошибка чтения/дешифрования 'DB_InfoARM.csv': {e}"
            write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            raise RuntimeError(error_msg) from e

        # 8. Фильтрация по IP-адресу
        write_log(f"[server_sync] Фильтрация записей по IP-адресу '{pc_ip}'...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        # Предполагаем, что в DataFrame есть колонка 'IPaddress'
        df_filtered_by_ip = df_arm[df_arm['IPaddress'] == pc_ip] # Используем == для точного совпадения
        # df_filtered_by_ip = df_arm[df_arm['IPaddress'].str.contains(pc_ip, na=False)] # Альтернатива, если нужен частичный матч

        if df_filtered_by_ip.empty:
            error_msg = "Данный компьютер не имеет доступа (IP не найден в DB_InfoARM.csv)!"
            write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            show_popup_notification(
                "Ошибка синхронизации",
                error_msg,
                "critical",
                0 # Бесконечно
            )
            # Удаляем папку shared
            if os.path.exists(SHARED_DIR):
                shutil.rmtree(SHARED_DIR)
                write_log(f"[server_sync] Папка '{SHARED_DIR}' удалена из-за отсутствия доступа.",
                          MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
            global_ResultSynchServer = 0
            return # Выходим из функции

        # 9. Извлечение AreaApp
        # Предполагаем, что в DataFrame есть колонка 'AreaApp'
        data_access_raw = df_filtered_by_ip.iloc[0]['AreaApp'] # Берем первую (и, скорее всего, единственную) запись
        if not data_access_raw or pd.isna(data_access_raw):
            error_msg = f"У записи компьютера с IP '{pc_ip}' отсутствует значение AreaApp!"
            write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error",MODULE_LOG_FILE_ERROR)
            show_popup_notification(
                "Ошибка синхронизации",
                error_msg,
                "critical",
                0 # Бесконечно
            )
            # Удаляем папку shared
            if os.path.exists(SHARED_DIR):
                shutil.rmtree(SHARED_DIR)
                write_log(f"[server_sync] Папка '{SHARED_DIR}' удалена из-за отсутствия AreaApp.",
                          MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
            global_ResultSynchServer = 0
            return # Выходим из функции

        global_MyAccessApp = data_access_raw
        text_inform = f"Данный компьютер имеет доступ \"{data_access_raw}\""
        write_log(f"[server_sync] {text_inform}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        # 10. Анализ AreaApp и удаление ненужных папок
        write_log(f"[server_sync] Анализ AreaApp и удаление ненужных папок...",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        # Получаем список всех папок в shared
        list_area = [d for d in os.listdir(SHARED_DIR) if os.path.isdir(os.path.join(SHARED_DIR, d))]
        delete_area = []

        # Разделяем AreaApp по ;
        arr_access = split_area_app(data_access_raw, ";")
        write_log(f"[server_sync] Разрешённые области применения: {arr_access}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

        if len(arr_access) > 1:
            # Если несколько областей
            for area_dir in list_area:
                if area_dir not in arr_access:
                    delete_area.append(area_dir)
        else:
            # Если одна область
            single_access = edit_access(data_access_raw) # Редактируем, если нужно
            for area_dir in list_area:
                if area_dir != single_access:
                    delete_area.append(area_dir)

        write_log(f"[server_sync] Папки для удаления: {delete_area}",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        # Удаляем ненужные папки
        for area_to_delete in delete_area:
            area_path = os.path.join(SHARED_DIR, area_to_delete)
            if os.path.exists(area_path):
                try:
                    shutil.rmtree(area_path)
                    write_log(f"[server_sync]   -> Удалена папка: '{area_to_delete}'",
                              MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
                except Exception as e:
                    write_log(f"[server_sync]   -> Ошибка удаления папки '{area_to_delete}': {e}",
                              MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)

        # 11. Установка флага успеха
        global_ResultSynchServer = 1
        write_log("[server_sync] Синхронизация данных с сервером успешно завершена.",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        write_log("------------------------------------------",
                  MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)

    except Exception as e:
        error_msg = f"КРИТИЧЕСКАЯ ОШИБКА в func_LoadingDataThisServer: {e}"
        write_log(f"[server_sync] {error_msg}",MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                  "error",MODULE_LOG_FILE_ERROR)
        show_popup_notification(
            "Критическая ошибка синхронизации",
            error_msg,
            "critical",
            0 # Бесконечно
        )
        # Удаляем папку shared при критической ошибке
        if os.path.exists(SHARED_DIR):
            shutil.rmtree(SHARED_DIR)
            write_log(f"[server_sync] Папка '{SHARED_DIR}' удалена из-за критической ошибки.",
                      MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
        global_ResultSynchServer = 0
        raise # Пробрасываем исключение дальше

# --- /ОСНОВНАЯ ФУНКЦИЯ СИНХРОНИЗАЦИИ ---
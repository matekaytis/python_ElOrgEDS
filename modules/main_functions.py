# ./modules/main_functions.py
import csv
import fcntl
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from settings import SHARED_NETWORK_PATH, SERVER_PATH, CREDENTIALS, USER, MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST, \
    MODULE_LOG_FILE_ERROR


# --- ФУНКЦИЯ ПОДГОТОВКИ ЛОГИРОВАНИЯ ---
def update_log(logfile_all: str = "", logfile_last: str = "", logfile_error: str= ""):
    if os.path.exists(logfile_last):
        with open(logfile_last, "w", encoding="utf-8") as f:
            f.write("") # Очищаем файл
    else:
        os.makedirs(os.path.dirname(logfile_last), exist_ok=True)
        with open(logfile_last, "w", encoding="utf-8") as f:
            pass # Создаем пустой файл

    if not os.path.exists(logfile_all):
        os.makedirs(os.path.dirname(logfile_all), exist_ok=True)
        with open(logfile_all, "w", encoding="utf-8") as f:
            pass  # Создаем пустой файл

    if not os.path.exists(logfile_error):
        os.makedirs(os.path.dirname(logfile_error), exist_ok=True)
        with open(logfile_error, "w", encoding="utf-8") as f:
            pass  # Создаем пустой файл
# --- \ФУНКЦИЯ ПОДГОТОВКИ ЛОГИРОВАНИЯ ---

# --- ФУНКЦИЯ ЛОГИРОВАНИЯ ---
def write_log(message: str, logfile_all: str = "", logfile_last: str = "",
              mode: str = "normal", logfile_error: str= ""):

    """Записывает сообщение в лог-файл и на консоль."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    try:
        if os.path.exists(logfile_last):
            with open(logfile_last, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        if os.path.exists(logfile_all):
            with open(logfile_all, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        if mode == "error":
            if os.path.exists(logfile_error):
                with open(logfile_error, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
    except Exception as e:
        subprocess.run([
            "notify-send", "-u", "cricical", "-t", 300, "ГЛАВНЫЕ ФУНКЦИИ", f"{e}"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --- /ФУНКЦИЯ ЛОГИРОВАНИЯ ---

# --- ФУНКЦИЯ ПРОВЕРКИ ДОСТУПА К СЕТЕВОЙ ПАПКЕ ---

def is_network_share_accessible(path: str, timeout: float = 5.0) -> bool:
    """
    Проверяет доступность сетевой папки с таймаутом.
    Возвращает True, если папка доступна и можно прочитать её содержимое.
    """
    result = [False]

    def try_access():
        try:
            p = Path(path)
            if p.is_dir():
                # Попытка прочитать хотя бы один элемент (или просто listdir)
                next(p.iterdir(), None)  # не читает всё, останавливается на первом
                result[0] = True
        except (OSError, PermissionError, FileNotFoundError):
            result[0] = False

    thread = threading.Thread(target=try_access)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Таймаут — поток не завершился
        return False

    return result[0]
# --- /ФУНКЦИЯ ПРОВЕРКИ ДОСТУПА К СЕТЕВОЙ ПАПКЕ ---

# --- ФУНКЦИЯ ПРОВЕРКИ ПАПКИ НА ПУСТОТУ ---
def is_folder_not_empty(folder_path):
    path = Path(folder_path)
    return path.is_dir() and any(path.iterdir())
# --- /ФУНКЦИЯ ПРОВЕРКИ ПАПКИ НА ПУСТОТУ ---

# --- ФУНКЦИЯ ОЧИСТКИ ПАПКИ ---
def clear_folder_files(folder_path):
    folder = Path(folder_path)
    if folder.exists():
        for item in folder.iterdir():
            if item.is_file():
                item.unlink()  # удаляет файл

# --- /ФУНКЦИЯ ОЧИСТКИ ПАПКИ ---

# --- ФУНКЦИИ ДЛЯ МОНТИРОВАНИЯ СЕТЕВОЙ ПАПКИ ---
def is_mounted(mount_point):
    """Проверяет, смонтирована ли точка."""
    try:
        with open("/proc/mounts", "r") as f:
            mounts = f.read()
        return mount_point in mounts
    except Exception as e:
        write_log(f"Ошибка при проверке монтирования: {e}",MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST,"error",MODULE_LOG_FILE_ERROR)
        return False

def mount_share():
    """Выполняет монтирование сетевой папки."""
    cmd = [
        "sudo", "mount", "-t", "cifs",
        "-o", f"credentials={CREDENTIALS},uid={USER},gid={USER},iocharset=utf8,file_mode=0777,dir_mode=0777",
        SERVER_PATH, SHARED_NETWORK_PATH
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            write_log(f"Папка '{SERVER_PATH}' успешно смонтирована на путь '{SHARED_NETWORK_PATH}'",
                      MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST)
            return True
        else:
            write_log(f"Ошибка монтирования: {result.stderr.strip()}", MODULE_LOG_FILE_ALL,
                      MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
            return False
    except Exception as e:
        write_log(f"Исключение при монтировании: {e}", MODULE_LOG_FILE_ALL,
                  MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
        return False

def ensure_mounted(max_retries=10, delay=5):
    """Пытается гарантировать, что папка смонтирована."""
    for attempt in range(1, max_retries + 1):
        if is_mounted(SHARED_NETWORK_PATH):
            write_log(f"Папка '{SERVER_PATH}' уже смонтирована на путь '{SHARED_NETWORK_PATH}'",
                      MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
            return True

        write_log(f"Попытка {attempt}/{max_retries}: "
                  f"монтируем папку '{SERVER_PATH}' на путь '{SHARED_NETWORK_PATH}'",
                  MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
        if mount_share():
            return True

        if attempt < max_retries:
            write_log(f"Не удалось смонтировать папку '{SERVER_PATH}' на путь '{SHARED_NETWORK_PATH}'."
                      f" Повтор через {delay} сек...", MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST,
                      "error", MODULE_LOG_FILE_ERROR)
            time.sleep(delay)

    write_log(f"Не удалось смонтировать папку '{SERVER_PATH}' на путь '{SHARED_NETWORK_PATH}'"
              f" после всех попыток.", MODULE_LOG_FILE_ALL,MODULE_LOG_FILE_LAST, "error", MODULE_LOG_FILE_ERROR)
    return False
# --- /ФУНКЦИИ ДЛЯ МОНТИРОВАНИЯ СЕТЕВОЙ ПАПКИ ---

# --- ФУНКЦИЯ БЛОКИРОВКИ ПОВТОРНОГО ЗАПУСКА ---
def prevent_multiple_instances(lock_file):
    try:
        # Открываем файл для записи (создаём, если не существует)
        fp = open(lock_file, "w")
        # Пытаемся установить эксклюзивную неблокирующую блокировку
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Сохраняем дескриптор, чтобы он не закрылся
        prevent_multiple_instances.lock_file = fp
        # Записываем PID текущего процесса (опционально, для отладки)
        fp.write(str(os.getpid()))
        fp.flush()
        write_log(f"Защита от повторного запуска установлена успешно",
                  MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST)
    except (IOError, OSError):
        # Блокировка не удалась — скрипт уже запущен
        write_log(f"Блокировка не удалась — скрипт уже запущен", MODULE_LOG_FILE_ALL, MODULE_LOG_FILE_LAST,
                  "error", MODULE_LOG_FILE_ERROR)
        sys.exit(1)
# --- /ФУНКЦИЯ БЛОКИРОВКИ ПОВТОРНОГО ЗАПУСКА ---

# --- ФУНКЦИЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ФАЙЛАХ ---
def get_files_info(root_folder: str):
    root = Path(root_folder)
    files_info = []

    for file_path in root.rglob('*'):  # рекурсивно
        if file_path.is_file():
            stat = file_path.stat()
            files_info.append({
                'path': str(file_path),
                'name': file_path.name,
                'size_bytes': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    return files_info
# --- /ФУНКЦИЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ФАЙЛАХ ---

# --- ФУНКЦИЯ ВЫГРУЗКИ ИНФОРМАЦИИ О ФАЙЛАХ В ФАЙЛ---
def save_to_csv(files_info, output_file: str):
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if not files_info:
            f.write("No files found.\n")
            return
        writer = csv.DictWriter(f, fieldnames=files_info[0].keys())
        writer.writeheader()
        writer.writerows(files_info)
# --- /ФУНКЦИЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ФАЙЛАХ ---


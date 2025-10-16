import threading
from datetime import datetime
from pathlib import Path


# --- ФУНКЦИЯ ЛОГИРОВАНИЯ ---
def write_log(message: str, logfile: str):

    """Записывает сообщение в лог-файл и на консоль."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry) # Вывод на консоль
    try:
        with open(logfile, "a", encoding="utf-8") as f1:
            f1.write(log_entry + "\n")
    except Exception as e:
        print(f"[ЛОГ] Ошибка записи в лог-файл: {e}")
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
# modules/notifications.py
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QProgressBar
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import subprocess
import os
import sys
from contextlib import redirect_stderr
from settings import MODULE_LOG_FILE
from modules.main_functions import write_log


class TimedNotification(QWidget):
    def __init__(self, title: str, message: str, timeout: int = 10, button_text=None,
                 button_action=None, color_bg: str = "#90EE90", color_timer: str = "#006400"):
        super().__init__()
        self.button_action = button_action
        self.remaining = timeout if timeout > 0 else None
        self.total_timeout = max(1, timeout)

        # Флаги окна
        self.setWindowFlags(
            Qt.WindowType.Popup |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Фиксированная ширина, динамическая высота
        self.setFixedWidth(320)
        self.setMinimumHeight(120)
        self.setMaximumHeight(400)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color_bg};
                border-radius: 8px;
            }}
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # --- 1. Крестик в правом верхнем углу ---
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch()  # растягиваемое пространство слева
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #191970;
                border: none;
                border-radius: 10px;
                padding: 0 0 0 0;
            }
            QPushButton:hover {
                color: #ADD8E6;
                background-color: #800000;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_bar_layout.addWidget(close_btn)
        main_layout.addLayout(top_bar_layout)

        # --- 2. Текст таймера ---
        self.countdown_label = QLabel("")
        self.countdown_label.setFont(QFont("Sans", 8, QFont.Weight.Bold))
        self.countdown_label.setStyleSheet(f"color: {color_timer}")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.countdown_label)

        # --- 3. Заголовок ---
        title_label = QLabel(title)
        title_label.setFont(QFont("Sans", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #191970;")
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title_label.setMaximumWidth(self.width() - 20)  # ширина окна - отступы
        main_layout.addWidget(title_label)

        # --- 4. Прокручиваемый текст сообщения ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")

        text_label = QLabel(message)
        text_label.setFont(QFont("Sans", 10))
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.TextFormat.PlainText)
        text_label.setStyleSheet("color: #000000; padding: 0 0 0 0;")
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text_label.setMaximumWidth(self.width() - 20)
        scroll_area.setWidget(text_label)
        main_layout.addWidget(scroll_area)

        # --- 5. Кнопка действия (опционально) ---
        if button_text:
            btn = QPushButton(button_text)
            btn.clicked.connect(self.on_button)
            btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: white;
                            border: none;
                            padding: 6px;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #c0392b;
                        }
                    """)
            main_layout.addWidget(btn)

        # --- 6. Прогресс-бар ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if self.total_timeout > 0 else 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {color_bg};
            }}
            QProgressBar::chunk {{
                background-color: {color_timer};
                border-radius: 3px;
            }}
        """)
        main_layout.addWidget(self.progress_bar)

        self.setLayout(main_layout)

        # Запуск таймера
        if self.remaining is not None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.tick)
            self.timer.start(1000)
            self.update_countdown_label()

    def showEvent(self, event):
        super().showEvent(event)
        self._adjust_height()
        self._move_to_bottom_right()

    def _adjust_height(self):
        """Подстраиваем высоту под содержимое."""
        self.layout().update()
        self.adjustSize()
        calculated_height = self.sizeHint().height()
        final_height = max(self.minimumHeight(), min(calculated_height, self.maximumHeight()))
        self.setFixedHeight(final_height)

    def _move_to_bottom_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = geo.right() - self.width() - 20
            y = geo.bottom() - self.height() - 20
            self.move(x, y)

    def closeEvent(self, event):
        """Гарантируем выход из цикла событий при закрытии окна."""
        super().closeEvent(event)
        QApplication.quit()

    def update_countdown_label(self):
        if self.remaining is not None:
            self.countdown_label.setText(f"Cообщение автоматически закроется через {self.remaining} сек.")
            if self.total_timeout > 0:
                progress = int((self.remaining / self.total_timeout) * 100)
                self.progress_bar.setValue(max(0, progress))
        else:
            self.countdown_label.setText("")
            self.progress_bar.setValue(0)

    def tick(self):
        if self.remaining is not None and self.remaining > 0:
            self.remaining -= 1
            self.update_countdown_label()
            if self.remaining == 0:
                self.close()

    def on_button(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.close()
        if self.button_action:
            self.button_action()


# --- ФУНКЦИЯ ПОКАЗА УВЕДОМЛЕНИЯ ---
def show_popup_notification(title: str, message: str, urgency: str = "normal", timeout_ms: int = 10000):
    try:
        app = QApplication.instance()
        if app is None:
            with open(os.devnull, 'w') as fnull:
                with redirect_stderr(fnull):
                    app = QApplication(sys.argv)
                    app.setQuitOnLastWindowClosed(True)

        timeout_sec = timeout_ms // 1000 if timeout_ms > 0 else 10
        if urgency == "normal":
            notification = TimedNotification(
                title=title,
                message=message,
                timeout=timeout_sec,
            )
            notification.show()
        if urgency == "critical":
            notification = TimedNotification(
                title=title,
                message=message,
                timeout=timeout_sec,
                color_bg="#FFC0CB",
                color_timer="#8B0000",
            )
            notification.show()
        app.exec()

    except Exception as e:
        write_log(f"Ошибка PyQt6-уведомления: {e}", MODULE_LOG_FILE)
        try:
            subprocess.run([
                "notify-send", "-u", urgency, "-t", str(timeout_ms), title, message
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write_log("Fallback: notify-send успешен.", MODULE_LOG_FILE)
        except Exception as fe:
            write_log(f"Fallback не сработал: {fe}", MODULE_LOG_FILE)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QToolBar,
    QMessageBox,
    QHBoxLayout,
)

from UI.Settings.settings import SettingsWindow  # type: ignore[import]
from UI.Homescreen.csv_loader import load_splash_texts
import random
import DataClasses.settings as settings

class HomeScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBJournal - Home")
        self.resize(800, 600)

        # Central content
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("NBJournal")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        (all_splash_texts, no_asterisk_texts, asterisk_texts) = load_splash_texts()
        # Choose a splash text at random
        # If username is set, use any instance and replace * with username, otherwise, use non asterisked version
        if settings.user_settings.preferences.username != "default_user" and asterisk_texts:
            splash_text = random.choice(all_splash_texts).replace("*", settings.user_settings.preferences.username)
        elif no_asterisk_texts:
            splash_text = random.choice(no_asterisk_texts)
        else:
            splash_text = "Welcome to NBJournal!"
        splash_label = QLabel(splash_text)
        splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        splash_label.setStyleSheet("font-style: italic; color: gray; margin-bottom: 16px;")

        subtitle = QLabel("Home")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: gray;")

        # Primary actions
        actions_layout = QHBoxLayout()
        btn_settings = QPushButton("Settings")
        btn_credits = QPushButton("Credits")

        btn_settings.clicked.connect(self.open_settings)
        btn_credits.clicked.connect(self.show_credits)

        actions_layout.addWidget(btn_settings)
        actions_layout.addWidget(btn_credits)

        central_layout.addWidget(title)
        central_layout.addWidget(splash_label)
        central_layout.addWidget(subtitle)
        central_layout.addLayout(actions_layout)

        # Info area
        info = QLabel(
            "Open 'Settings' to configure preferences.\n"
            "See 'Credits' for acknowledgements."
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("margin-top: 24px;")
        central_layout.addWidget(info)

        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # Optional toolbar
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(self.open_settings)
        toolbar.addAction(act_settings)

        act_credits = QAction("Credits", self)
        act_credits.triggered.connect(self.show_credits)
        toolbar.addAction(act_credits)

        # Placeholders for child windows
        self._settings_window = None

    def open_settings(self):
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def show_credits(self):
        QMessageBox.information(
            self,
            "Credits",
            "NBJournal\n\n"
            "Created by: Your Name\n"
            "Thanks to the PyQt6 project.\n\n"
            "Placeholder credits info."
        )


def main():
    app = QApplication(sys.argv)
    window = HomeScreen()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
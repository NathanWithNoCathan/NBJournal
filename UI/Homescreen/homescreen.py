from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import sys

# c:/Users/mccom/Desktop/School shit/College senior/NBJournal/UI/Homescreen/homescreen.py
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QToolBar,
    QMessageBox,
    QDialog,
    QHBoxLayout,
)


class LogsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs")
        self.setModal(False)
        self.resize(600, 400)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Logs view placeholder"))
        # TODO: Replace with actual logs list/table connected to data classes
        self.setLayout(layout)


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(False)
        self.resize(400, 300)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings placeholder"))
        # TODO: Add settings controls and persist them
        self.setLayout(layout)


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

        subtitle = QLabel("Home")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: gray;")

        # Primary actions
        actions_layout = QHBoxLayout()
        btn_view_logs = QPushButton("View Logs")
        btn_settings = QPushButton("Settings")
        btn_credits = QPushButton("Credits")

        btn_view_logs.clicked.connect(self.open_logs)
        btn_settings.clicked.connect(self.open_settings)
        btn_credits.clicked.connect(self.show_credits)

        actions_layout.addWidget(btn_view_logs)
        actions_layout.addWidget(btn_settings)
        actions_layout.addWidget(btn_credits)

        central_layout.addWidget(title)
        central_layout.addWidget(subtitle)
        central_layout.addLayout(actions_layout)

        # Info area
        info = QLabel(
            "Use 'View Logs' to manage your journal entries.\n"
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

        act_view_logs = QAction("View Logs", self)
        act_view_logs.triggered.connect(self.open_logs)
        toolbar.addAction(act_view_logs)

        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(self.open_settings)
        toolbar.addAction(act_settings)

        act_credits = QAction("Credits", self)
        act_credits.triggered.connect(self.show_credits)
        toolbar.addAction(act_credits)

        # Placeholders for child windows
        self._logs_window = None
        self._settings_window = None

    def open_logs(self):
        if self._logs_window is None:
            self._logs_window = LogsWindow(self)
        self._logs_window.show()
        self._logs_window.raise_()
        self._logs_window.activateWindow()

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
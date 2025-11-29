from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
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
    QMenu
)

from UI.Settings.settings import SettingsWindow  # type: ignore[import]
from UI.Homescreen.csv_loader import load_splash_texts
from UI.Homescreen.logs_viewer import LogsViewer
import random
import DataClasses.settings as settings

class HomeScreen(QMainWindow):
    def __init__(self):
        super().__init__()

        # Register this instance as the globally-active homescreen
        # so other UI modules can reference it without importing
        # this file at module-import time.
        from UI.Homescreen import state
        state.active_homescreen = self

        self.setWindowTitle("NBJournal - Home")
        self.resize(800, 600)

        # Central content
        central = QWidget()

        # Root layout: three regions (top, middle, bottom)
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Top region: title + splash, hugging the top ---
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

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

        top_layout.addWidget(title)
        top_layout.addWidget(splash_label)

        # --- Middle region: toggle button + logs viewer filling space ---
        self.logs_viewer = LogsViewer(self)
        self.logs_viewer.setVisible(False)

        toggle_bar = QHBoxLayout()
        toggle_bar.setContentsMargins(0, 0, 0, 0)
        toggle_bar.setSpacing(8)
        toggle_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.toggle_logs_button = QPushButton("Show Logs")
        self.toggle_logs_button.clicked.connect(self.toggle_logs_viewer)
        toggle_bar.addWidget(self.toggle_logs_button)

        middle_layout = QVBoxLayout()
        # Add horizontal margins so the logs viewer doesn't touch window edges
        middle_layout.setContentsMargins(16, 0, 16, 0)
        middle_layout.setSpacing(4)
        middle_layout.addLayout(toggle_bar)
        # logs_viewer takes all vertical stretch in this middle region
        middle_layout.addWidget(self.logs_viewer, stretch=1)

        # --- Bottom region: info label hugging the bottom ---
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        info = QLabel(
            "Click on a log to view it.\n"
            "See the menu in the top left corner for creating, editing, and deleting logs."
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("margin-top: 24px;")

        # Add stretch before info so it hugs the bottom of its region
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(info)

        # --- Assemble root layout: top fixed, middle stretch, bottom fixed ---
        root_layout.addLayout(top_layout)          # no stretch -> size to contents
        root_layout.addLayout(middle_layout, 1)    # stretch -> takes remaining space
        root_layout.addLayout(bottom_layout)       # no stretch -> size to contents

        central.setLayout(root_layout)
        self.setCentralWidget(central)

        # Placeholders for child windows
        self._settings_window = None

        # Currently selected log exposed from the logs viewer
        self.current_log = self.logs_viewer.current_log
        self.logs_viewer.selected_log_changed.connect(self._on_selected_log_changed)

        self._create_menu_bar()
        self._create_shortcuts()

    def open_settings(self):
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _on_selected_log_changed(self, log):
        """Handle updates when the user selects a different log.

        The latest selected `Log` instance is stored on the window as
        `current_log` so other parts of the HomeScreen can react to it.
        """
        self.current_log = log

    def toggle_logs_viewer(self):
        """Show/hide the logs viewer and update the button label."""
        is_visible = self.logs_viewer.isVisible()
        self.logs_viewer.setVisible(not is_visible)
        self.toggle_logs_button.setText("Hide Logs" if not is_visible else "Show Logs")

    def _on_log_saved(self, _log):
        """Handle a log-saved event by reloading the logs viewer."""
        self.logs_viewer.reload_logs()

    def show_credits(self):
        QMessageBox.information(
            self,
            "Credits",
            "NBJournal\n\n"
            "Created by: Nate, Beto, and Emma\n"
            "Thanks to the PyQt6 project.\n\n"
        )

    def _create_menu_bar(self):
        menuBar = self.menuBar()

        # File menu
        fileMenu = menuBar.addMenu("Log")

        self.log_info_action = QAction("Log Info (ctrl+I)", self)
        self.log_info_action.triggered.connect(self._show_log_info)
        fileMenu.addAction(self.log_info_action)

        fileMenu.addSeparator()

        self.new_log_action = QAction("New Log (ctrl+N)", self)
        self.new_log_action.triggered.connect(self._new_log)
        fileMenu.addAction(self.new_log_action)

        self.edit_logs_action = QAction("Edit Log (ctrl+E)", self)
        self.edit_logs_action.triggered.connect(self._edit_log)
        fileMenu.addAction(self.edit_logs_action)

        self.delete_log_action = QAction("Delete Log (ctrl+D)", self)
        self.delete_log_action.triggered.connect(self._delete_log)
        fileMenu.addAction(self.delete_log_action)

        fileMenu.addSeparator()

        self.tag_editor_action = QAction("Tag Editor (ctrl+T)", self)
        self.tag_editor_action.triggered.connect(self._open_tag_editor)
        fileMenu.addAction(self.tag_editor_action)

        # View menu
        viewMenu = menuBar.addMenu("View")

        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.open_settings)
        viewMenu.addAction(self.settings_action)

        self.credits_action = QAction("Credits", self)
        self.credits_action.triggered.connect(self.show_credits)
        viewMenu.addAction(self.credits_action)

        # Help menu
        helpMenu = menuBar.addMenu("Help")

        self.searching_help_action = QAction("Searching Guide", self)
        self.searching_help_action.triggered.connect(lambda: QMessageBox.information(
            self,
            "Search Help",
            "To search logs, type keywords into the search bar above the logs list.\n\n"
            "The search will filter logs by title or description in real-time as you type.\n\n"
            "You can use multiple keywords separated by spaces to narrow down results.\n\n"
            "Special search commands:\n"
            "  sort:asc OR sort:reverse - Sort logs in ascending order.\n"
            "  sort:desc OR sort:forward - Sort logs in descending order (default).\n"
            "  sort:created - Sort logs by creation date.\n"
            "  sort:alphabetical - Sort logs alphabetically by title.\n"
            "  sort:modified - Sort logs by last modified date (default).\n"
            "  tag:<tagname> - Filter logs by specific tag.\n"
            "  body:<keyword> - Search within log body text.\n\n"
            "Example: sort:asc tag:work project\n\n"
            "This would show logs tagged with 'work' and containing 'project' in the title or description, sorted in ascending order."
        ))
        helpMenu.addAction(self.searching_help_action)

        self.info_action = QAction("About NBJournal", self)
        self.info_action.triggered.connect(lambda: QMessageBox.information(
            self,
            "About NBJournal",
            "NBJournal is a personal journaling application designed to help you organize and manage your logs effectively.\n\n"
            "Features include:\n"
            "- Creating, editing, and deleting logs\n"
            "- Tagging logs for easy categorization\n"
            "- Powerful search functionality\n"
            "- Customizable settings and appearance\n"
            "- AI-assisted statistical analysis and summaries\n\n"
            "We hope NBJournal helps you keep track of your thoughts and experiences!"
        ))
        helpMenu.addAction(self.info_action)

    def _create_shortcuts(self):
        """Create keyboard shortcuts for common HomeScreen actions.

        Mirrors the style used in `LogEditorWindow._create_shortcuts`.
        """
        # Log info (Ctrl+I)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self._show_log_info)

        # New log (Ctrl+N)
        QShortcut(QKeySequence.StandardKey.New, self, activated=self._new_log)

        # Edit current log (Ctrl+E)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._edit_log)

        # Delete current log (Ctrl+D)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self._delete_log)

        # Toggle logs viewer visibility (Ctrl+L)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.toggle_logs_viewer)

        # Open tag editor (Ctrl+T)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._open_tag_editor)  

    def _show_log_info(self):
        """Show information about the currently selected log."""
        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to view its information.")
            return

        info_text = (
            f"Name: {self.current_log.name}\n"
            f"Description: {self.current_log.description}\n"
            f"Path: {self.current_log.path}\n"
            f"Created: {self.current_log.created_at.strftime("%Y-%m-%d %H:%M:%S")}\n"
            f"Last modified: {self.current_log.revised_at.strftime("%Y-%m-%d %H:%M:%S")}\n"
            f"Revision count: {len(self.current_log.revision_history) if self.current_log.revision_history else 0}\n"
            f"Tags: {', '.join(tag.name for tag in self.current_log.tags) if self.current_log.tags else 'None'}\n"
        )

        QMessageBox.information(self, "Log Information", info_text)

    def _open_tag_editor(self):
        """Open the Tag Editor window."""
        from UI.TagEditor.tag_editor import TagEditorWindow  # type: ignore[import]

        # Do not allow multiple tag editor windows at once.
        from UI.TagEditor import state as tag_editor_state
        if tag_editor_state.active_tag_editor is not None:
            QMessageBox.information(
                self,
                "Tag Editor Already Open",
                "You already have a tag editor open. Please close it "
                "before opening another.",
            )
            return

        tag_editor = TagEditorWindow(parent=self)
        tag_editor.show()

    def _new_log(self):
        """Create a new Log and open it in the Log Editor."""
        from UI.LogEditor.log_editor import LogEditorWindow  # type: ignore[import]
        from DataClasses.log import Log, LOGS_FOLDER
        import os
        import uuid

        # Do not allow multiple log editor windows at once.
        from UI.LogEditor import state as log_editor_state
        if log_editor_state.active_log_editor is not None:
            QMessageBox.information(
                self,
                "Log Editor Already Open",
                "You already have a log editor open. Please close it "
                "before opening another.",
            )
            return

        # Randomly generate a new log path that does not overwrite
        # an existing file in the `logs` directory.
        # This weird path logic goes up three levels from this file due to the project structure.
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), LOGS_FOLDER)
        os.makedirs(logs_dir, exist_ok=True)

        while True:
            candidate_name = f"log_{uuid.uuid4().hex[:8]}.json"
            candidate_path = os.path.join(logs_dir, candidate_name)
            if not os.path.exists(candidate_path):
                break

        new_log = Log(
            name="",
            description="",
            body="",
            path=candidate_name,
        )

        log_editor = LogEditorWindow(new_log, parent=self)
        log_editor.show()

    def _edit_log(self):
        """Open the currently selected log in the Log Editor."""
        from UI.LogEditor.log_editor import LogEditorWindow  # type: ignore[import]

        # Do not allow multiple log editor windows at once.
        from UI.LogEditor import state as log_editor_state
        if log_editor_state.active_log_editor is not None:
            QMessageBox.information(
                self,
                "Log Editor Already Open",
                "You already have a log editor open. Please close it "
                "before opening another.",
            )
            return

        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to edit.")
            return

        log_editor = LogEditorWindow(self.current_log, parent=self)
        log_editor.show()

    def _delete_log(self):
        """Delete the currently selected log after user confirmation."""
        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the log '{self.current_log.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.current_log.delete()
                QMessageBox.information(self, "Log Deleted", "The log was deleted successfully.")
                self.logs_viewer.reload_logs()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to delete log:\n{exc}")
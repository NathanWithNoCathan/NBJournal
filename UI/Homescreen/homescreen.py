from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
import os
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
    QMenu,
    QProgressDialog,
)

from UI.Settings.settings import SettingsWindow  # type: ignore[import]
from UI.Homescreen.csv_loader import load_splash_texts
from UI.Homescreen.logs_viewer import LogsViewer
import random
import DataClasses.settings as settings
from DataClasses.log import Log


class BackgroundWorker(QObject):
    """Generic worker object for running callables in a QThread.

    Emits `finished` when the function completes successfully and `error`
    with a string message if an exception is raised.
    """

    finished = pyqtSignal()
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, func, *args, uncancelable: bool = False, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._uncancelable = uncancelable

    def run(self):
        try:
            # For uncancelable tasks we just always run the function; any
            # early return must be handled inside the function itself.
            result = self._func(*self._args, **self._kwargs)
            if not self._uncancelable and result == "cancelled":
                self.cancelled.emit()
            else:
                self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))

class HomeScreen(QMainWindow):
    summary_ready = pyqtSignal(str, int)

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
        self.toggle_logs_button.setToolTip("Show or hide the log list (Ctrl+L)")
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

        # Track whether a background AI task is currently running
        self._background_task_running = False
        self._background_progress_dialog = None
        self._background_thread = None
        self._background_worker = None
        self._background_cancelled = False

        # Connect summary signal to UI handler (runs in main thread)
        self.summary_ready.connect(self._show_summary_dialog)

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

        self.remove_all_tags_action = QAction("Remove All Tags from Current Log", self)
        self.remove_all_tags_action.triggered.connect(self._remove_all_tags_current_log)
        fileMenu.addAction(self.remove_all_tags_action)

        self.remove_all_tags_all_shown_logs_action = QAction("Remove All Tags from All Shown Logs", self)
        self.remove_all_tags_all_shown_logs_action.triggered.connect(self._remove_all_tags_all_shown_logs)
        fileMenu.addAction(self.remove_all_tags_all_shown_logs_action)

        fileMenu.addSeparator()

        self.encrypt_selected_log_action = QAction("Encrypt Selected Log", self)
        self.encrypt_selected_log_action.triggered.connect(self._encrypt_selected_log)
        fileMenu.addAction(self.encrypt_selected_log_action)

        self.decrypt_selected_log_action = QAction("Decrypt Selected Log", self)
        self.decrypt_selected_log_action.triggered.connect(self._decrypt_selected_log)
        fileMenu.addAction(self.decrypt_selected_log_action)

        # AI Features menu (single consolidated menu with separators)
        aiMenu = menuBar.addMenu("AI Features")

        # --- Sentiment Analysis ---
        self.sentiment_analysis_on_current_log_action = QAction("Analyze Sentiment of Current Log", self)
        self.sentiment_analysis_on_current_log_action.triggered.connect(self._analyze_current_log_sentiment)
        aiMenu.addAction(self.sentiment_analysis_on_current_log_action)

        self.sentiment_analysis_on_all_shown_logs_action = QAction("Analyze Sentiment of All Shown Logs", self)
        self.sentiment_analysis_on_all_shown_logs_action.triggered.connect(self._analyze_all_shown_logs_sentiment)
        aiMenu.addAction(self.sentiment_analysis_on_all_shown_logs_action)

        self.remove_sentiment_analysis_data_current_log_action = QAction("Remove Sentiment Data from Current Log", self)
        self.remove_sentiment_analysis_data_current_log_action.triggered.connect(self._remove_sentiment_data_current_log)
        aiMenu.addAction(self.remove_sentiment_analysis_data_current_log_action)

        self.remove_sentiment_analysis_data_shown_logs_action = QAction("Remove Sentiment Data from All Shown Logs", self)
        self.remove_sentiment_analysis_data_shown_logs_action.triggered.connect(self._remove_sentiment_data_shown_logs)
        aiMenu.addAction(self.remove_sentiment_analysis_data_shown_logs_action)

        aiMenu.addSeparator()

        # --- Tag Recommendations ---
        self.tag_recommendations_on_current_log_action = QAction("Recommend Tags for Current Log", self)
        self.tag_recommendations_on_current_log_action.triggered.connect(self._recommend_tags_current_log)
        aiMenu.addAction(self.tag_recommendations_on_current_log_action)

        self.tag_recommendations_on_all_shown_logs_action = QAction("Recommend Tags for All Shown Logs", self)
        self.tag_recommendations_on_all_shown_logs_action.triggered.connect(self._recommend_tags_all_shown_logs)
        aiMenu.addAction(self.tag_recommendations_on_all_shown_logs_action)

        self.tag_recommendations_on_all_shown_logs_with_no_tags_action = QAction("Recommend Tags for All Shown Logs with No Tags", self)
        self.tag_recommendations_on_all_shown_logs_with_no_tags_action.triggered.connect(self._recommend_tags_all_shown_logs_with_no_tags)
        aiMenu.addAction(self.tag_recommendations_on_all_shown_logs_with_no_tags_action)

        aiMenu.addSeparator()

        # --- Content Summarization ---
        self.content_summarization_on_current_log_action = QAction("Summarize Current Log Content", self)
        self.content_summarization_on_current_log_action.triggered.connect(self._summarize_current_log)
        aiMenu.addAction(self.content_summarization_on_current_log_action)

        self.content_summarization_on_all_shown_logs_action = QAction("Summarize Content of All Shown Logs", self)
        self.content_summarization_on_all_shown_logs_action.triggered.connect(self._summarize_all_shown_logs)
        aiMenu.addAction(self.content_summarization_on_all_shown_logs_action)

        self.content_summarization_on_current_log_with_custom_prompt_action = QAction("Summarize Current Log (Custom Prompt)", self)
        self.content_summarization_on_current_log_with_custom_prompt_action.triggered.connect(self._summarize_current_log_with_custom_prompt)
        aiMenu.addAction(self.content_summarization_on_current_log_with_custom_prompt_action)

        self.content_summarization_on_all_shown_logs_with_custom_prompt_action = QAction("Summarize All Shown Logs (Custom Prompt)", self)
        self.content_summarization_on_all_shown_logs_with_custom_prompt_action.triggered.connect(self._summarize_all_shown_logs_with_custom_prompt)
        aiMenu.addAction(self.content_summarization_on_all_shown_logs_with_custom_prompt_action)

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
            "  body:<keyword> - Search within log body text.\n"
            "  ! before a term negates the filter, e.g. !tag:personal excludes logs with the 'personal' tag or !name excludes logs with \"name\" in the title or description.\n\n"
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

        self.encryption_decryption_help_action = QAction("Encryption Help", self)
        self.encryption_decryption_help_action.triggered.connect(lambda: QMessageBox.information(
            self,
            "Encryption Help",
            "To encrypt a log, select it from the logs list and choose 'Encrypt Selected Log' from the 'Log' menu. "
            "You will be prompted to enter and confirm a password. Once encrypted, the log's content will be hidden "
            "and can only be accessed by decrypting it with the correct password.\n\n"
            "To decrypt a log, select the encrypted log and choose 'Decrypt Selected Log' from the 'Log' menu. "
            "You will need to enter the password used during encryption to access the log's content again.\n\n"
            "Please remember your passwords, as there is no way to recover encrypted logs without them."
        ))
        helpMenu.addAction(self.encryption_decryption_help_action)

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

    def _remove_all_tags_current_log(self) -> None:
        """Remove all tags from the currently selected log."""
        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to remove tags from.")
            return
        
        if not self.current_log.tags:
            QMessageBox.information(self, "No Tags", "The selected log has no tags to remove.")
            return
        
        confirm = QMessageBox.question(
            self,
            "Confirm Remove Tags",
            "Are you sure you want to remove all tags from the selected log?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.current_log.tags.clear()
            self.current_log.save()
            QMessageBox.information(self, "Tags Removed", "All tags have been removed from the selected log.")
            self.logs_viewer.reload_logs()

    def _remove_all_tags_all_shown_logs(self) -> None:
        """Remove all tags from all logs currently shown in the logs viewer."""
        shown_logs = self.logs_viewer._filtered_logs
        if not shown_logs:
            QMessageBox.information(self, "No Logs Shown", "There are no logs currently shown to remove tags from.")
            return
        
        logs_with_tags = [log for log in shown_logs if log.tags]
        if not logs_with_tags:
            QMessageBox.information(self, "No Tags", "None of the shown logs have tags to remove.")
            return
        
        confirm = QMessageBox.question(
            self,
            "Confirm Remove Tags",
            f"Are you sure you want to remove all tags from the {len(logs_with_tags)} shown logs that have tags?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            for log in logs_with_tags:
                log.tags.clear()
                log.save()
            QMessageBox.information(self, "Tags Removed", "All tags have been removed from the shown logs.")
            self.logs_viewer.reload_logs()

    def _encrypt_selected_log(self) -> None:
        """Encrypt the currently selected log."""
        # Block encryption while a log editor window is open.
        from UI.LogEditor import state as log_editor_state  # type: ignore[import]
        if log_editor_state.active_log_editor is not None:
            QMessageBox.information(
                self,
                "Log Editor Open",
                "Close the Log Editor before encrypting logs.",
            )
            return

        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to encrypt.")
            return
        
        if self.current_log.is_encrypted():
            QMessageBox.information(self, "Log Already Encrypted", "The selected log is already encrypted.")
            return
        
        # Get password from user (basic text box)
        from PyQt6.QtWidgets import QInputDialog, QLineEdit

        password, ok = QInputDialog.getText(self, "Encrypt Log", "Enter a password to encrypt the log:", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return  # User cancelled or entered empty password
        
        # Ask for confirmation
        confirm_password, ok = QInputDialog.getText(self, "Confirm Password", "Re-enter the password to confirm:", QLineEdit.EchoMode.Password)
        if not ok or password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "The passwords do not match. Encryption cancelled.")
            return
        
        try:
            self.current_log.encrypt_with_password(password)
            QMessageBox.information(self, "Log Encrypted", "The selected log has been encrypted successfully.")
            self.logs_viewer.reload_logs()
        except Exception as e:
            QMessageBox.critical(self, "Encryption Error", f"An error occurred while encrypting the log: {str(e)}")

    def _decrypt_selected_log(self) -> None:
        """Decrypt the currently selected log."""
        # Block decryption while a log editor window is open.
        from UI.LogEditor import state as log_editor_state  # type: ignore[import]
        if log_editor_state.active_log_editor is not None:
            QMessageBox.information(
                self,
                "Log Editor Open",
                "Close the Log Editor before decrypting logs.",
            )
            return

        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to decrypt.")
            return
        
        if not self.current_log.is_encrypted():
            QMessageBox.information(self, "Log Not Encrypted", "The selected log is not encrypted.")
            return
        
        # Get password from user (basic text box)
        from PyQt6.QtWidgets import QInputDialog, QLineEdit

        password, ok = QInputDialog.getText(self, "Decrypt Log", "Enter the password to decrypt the log:", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return  # User cancelled or entered empty password
        
        # Check if password works
        if not self.current_log.can_decrypt_with_password(password):
            QMessageBox.warning(self, "Incorrect Password", "The password entered is incorrect. Decryption cancelled.")
            return

        try:
            self.current_log.decrypt_with_password(password)
            QMessageBox.information(self, "Log Decrypted", "The selected log has been decrypted successfully.")
            self.logs_viewer.reload_logs()
        except Exception as e:
            QMessageBox.critical(self, "Decryption Error", f"An error occurred while decrypting the log: {str(e)}")

    # ------------------------------------------------------------------
    # Background task helper
    # ------------------------------------------------------------------

    def _can_start_background_task(self) -> bool:
        """Return True if a background task is allowed to start.

        Disallows starting if a Log Editor or Tag Editor is already open
        or if another background task is already running.
        """
        # Check for open Log Editor
        from UI.LogEditor import state as log_editor_state  # type: ignore[import]
        if log_editor_state.active_log_editor is not None:
            QMessageBox.information(
                self,
                "Log Editor Open",
                "Close the Log Editor before running AI background tasks.",
            )
            return False

        # Check for open Tag Editor
        from UI.TagEditor import state as tag_editor_state  # type: ignore[import]
        if tag_editor_state.active_tag_editor is not None:
            QMessageBox.information(
                self,
                "Tag Editor Open",
                "Close the Tag Editor before running AI background tasks.",
            )
            return False

        if self._background_task_running:
            QMessageBox.information(
                self,
                "Background Task Running",
                "Please wait for the current AI task to finish.",
            )
            return False

        return True

    def _on_background_task_finished(self) -> None:
        """Slot called when the background worker completes successfully."""
        # Only mark as finished if the worker actually completed.
        self._finish_background_task()

    def _on_background_task_error(self, message: str) -> None:
        """Slot called when the background worker reports an error."""
        self._finish_background_task()
        QMessageBox.critical(self, "Background Task Error", message)

    def _on_background_task_cancelled(self) -> None:
        """Slot called when the background worker reports a cancellation."""
        # For now, treat cancellation as simply ending the task UI-wise.
        self._finish_background_task()

    def _start_background_task(self, title: str, label: str, func=None, uncancelable: bool = False, **kwargs) -> None:
        """Mark the beginning of a background task and show progress.

        If `func` is provided, it is executed in a separate `QThread`
        using `BackgroundWorker` so the UI remains responsive.
        """
        # Reset cancellation flag at start of each task
        self._background_cancelled = False
        self._background_task_running = True

        dlg = QProgressDialog(label, "Cancel", 0, 0, self)
        dlg.setWindowTitle(title)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.setValue(0)

        # Wire the cancel button. For uncancelable tasks we keep the work
        # running but notify the user that cancellation is not possible.
        if uncancelable:
            def _inform_uncancelable() -> None:
                QMessageBox.information(
                    self,
                    "Task Cannot Be Cancelled",
                    "This summarization task cannot be cancelled and will "
                    "continue running to completion in the background.",
                )

            dlg.canceled.connect(_inform_uncancelable)
        else:
            dlg.canceled.connect(self._on_background_cancel_pressed)

        # If you later wire real async work, you can connect cancel here.
        self._background_progress_dialog = dlg
        dlg.show()

        # While background task is running, disable actions that must not occur
        self.delete_log_action.setEnabled(False)
        self.tag_editor_action.setEnabled(False)

        if func is not None:
            # Create worker and thread for the long-running function
            self._background_thread = QThread(self)
            self._background_worker = BackgroundWorker(func, uncancelable=uncancelable, **kwargs)
            self._background_worker.moveToThread(self._background_thread)

            # Wire signals
            self._background_thread.started.connect(self._background_worker.run)
            self._background_worker.finished.connect(self._on_background_task_finished)
            self._background_worker.error.connect(self._on_background_task_error)
            self._background_worker.cancelled.connect(self._on_background_task_cancelled)

            # Ensure cleanup when done
            self._background_worker.finished.connect(self._background_thread.quit)
            self._background_worker.error.connect(self._background_thread.quit)
            self._background_worker.cancelled.connect(self._background_thread.quit)
            self._background_thread.finished.connect(self._background_worker.deleteLater)
            self._background_thread.finished.connect(self._clear_background_thread_refs)

            self._background_thread.start()

    def _finish_background_task(self) -> None:
        """Clear background-task state and hide progress UI."""
        self._background_task_running = False

        if self._background_progress_dialog is not None:
            self._background_progress_dialog.hide()
            self._background_progress_dialog.deleteLater()
            self._background_progress_dialog = None

        # Re-enable actions once background work is done
        self.delete_log_action.setEnabled(True)
        self.tag_editor_action.setEnabled(True)

    def _clear_background_thread_refs(self) -> None:
        """Clear references to the background thread/worker after completion."""
        self._background_thread = None
        self._background_worker = None

    def _on_background_cancel_pressed(self) -> None:
        """Set a flag indicating the user has requested cancellation.

        Background worker functions should periodically check
        `self._background_cancelled` (or be passed a reference to it)
        and stop work early when it becomes True.
        """
        self._background_cancelled = True

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

    # === AI Features: Sentiment Analysis ===

    def _analyze_current_log_sentiment(self):
        """Start background task: analyze sentiment of the current log."""
        from AIFeatures.openai_prompter import sentiment_analysis_enabled
        if not sentiment_analysis_enabled():
            QMessageBox.information(
                self,
                "Sentiment Analysis Disabled",
                "The sentiment analysis feature is disabled in settings, or AI features are disabled in general. "
                "Please enable it to use this feature.",
            )
            return

        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to analyze its sentiment.")
            return

        if not self._can_start_background_task():
            return

        from AIFeatures.sentiment_analysis import analyze_log_sentiment

        self._start_background_task(
            title="Analyzing Sentiment",
            label="Analyzing sentiment of the current log...",
            func=analyze_log_sentiment,
            log=self.current_log,
        )

    def _batch_log_sentiment_analysis_worker(self):
        """Worker function to analyze sentiment for all shown logs."""
        from AIFeatures.sentiment_analysis import analyze_log_sentiment

        self._background_progress_dialog.setValue(0)
        self._background_progress_dialog.setMinimum(0)
        self._background_progress_dialog.setMaximum(len(self.logs_viewer._filtered_logs))

        shown_logs = self.logs_viewer._filtered_logs
        for i, log in enumerate(shown_logs):
            if self._background_cancelled:
                return
            analyze_log_sentiment(log)
            self._background_progress_dialog.setValue(i + 1)

    def _analyze_all_shown_logs_sentiment(self):
        """Start background task: analyze sentiment for all shown logs."""
        from AIFeatures.openai_prompter import sentiment_analysis_enabled
        if not sentiment_analysis_enabled():
            QMessageBox.information(
                self,
                "Sentiment Analysis Disabled",
                "The sentiment analysis feature is disabled in settings, or AI features are disabled in general. "
                "Please enable it to use this feature.",
            )
            return

        if not self._can_start_background_task():
            return
        
        from AIFeatures.sentiment_analysis import analyze_log_sentiment

        self._start_background_task(
            title="Analyzing Sentiment",
            label="Analyzing sentiment of all shown logs...",
            func=self._batch_log_sentiment_analysis_worker,
        )

    def _remove_sentiment_data_current_log(self):
        """Remove sentiment data from current log."""
        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to remove its sentiment data.")
            return

        self.current_log.delete_sentiment_analysis()
        QMessageBox.information(
            self,
            "Sentiment Data Removed",
            "Sentiment analysis data has been removed from the current log.",
        )

    def _remove_sentiment_data_shown_logs(self):
        """Start background task: remove sentiment data from all shown logs."""
        shown_logs = self.logs_viewer._filtered_logs
        for log in shown_logs:
            log.delete_sentiment_analysis()

        QMessageBox.information(
            self,
            "Sentiment Data Removed",
            "Sentiment analysis data has been removed from all shown logs.",
        )

    # === AI Features: Tag Recommendations ===

    def _perform_tag_recommendation_worker(self, log: Log):
        """Worker function to recommend tags for the current log."""
        from AIFeatures.tag_recommendations import recommend_tags_for_log

        try:
            res = recommend_tags_for_log(log)
        except Exception as e:
            return

        from DataClasses.tag import tags

        log.tags.clear()
        for tag_name in res.get("selected", []):
            tag = next((t for t in tags if t.name == tag_name), None)
            if tag is not None:
                log.tags.append(tag)
        log.save()

    def _batch_log_tag_recommendation_worker(self, ignore_already_tagged: bool = False):
        """Worker function to recommend tags for all shown logs."""
        from AIFeatures.sentiment_analysis import analyze_log_sentiment

        self._background_progress_dialog.setValue(0)
        self._background_progress_dialog.setMinimum(0)
        self._background_progress_dialog.setMaximum(len(self.logs_viewer._filtered_logs))

        shown_logs = self.logs_viewer._filtered_logs
        for i, log in enumerate(shown_logs):
            if self._background_cancelled:
                return
            if ignore_already_tagged and log.tags:
                self._background_progress_dialog.setValue(i + 1)
                continue
            self._perform_tag_recommendation_worker(log)
            self._background_progress_dialog.setValue(i + 1)

    def _recommend_tags_current_log(self):
        """Start background task: recommend tags for the current log."""
        from AIFeatures.openai_prompter import tag_recommendations_enabled
        if not tag_recommendations_enabled():
            QMessageBox.information(
                self,
                "Tag Recommendations Disabled",
                "The tag recommendations feature is disabled in settings, or AI features are disabled in general. "
                "Please enable it to use this feature.",
            )
            return

        if not self._can_start_background_task():
            return

        self._start_background_task(
            title="Recommending Tags",
            label="Recommending tags for the current log...",
            func=self._perform_tag_recommendation_worker,
            log=self.current_log,
        )

    def _recommend_tags_all_shown_logs(self):
        """Start background task: recommend tags for all shown logs."""
        from AIFeatures.openai_prompter import tag_recommendations_enabled
        if not tag_recommendations_enabled():
            QMessageBox.information(
                self,
                "Tag Recommendations Disabled",
                "The tag recommendations feature is disabled in settings, or AI features are disabled in general. "
                "Please enable it to use this feature.",
            )
            return
        
        if not self._can_start_background_task():
            return

        self._start_background_task(
            title="Recommending Tags",
            label="Recommending tags for all shown logs...",
            func=self._batch_log_tag_recommendation_worker,
            ignore_already_tagged=False,
        )

    def _recommend_tags_all_shown_logs_with_no_tags(self):
        """Start background task: recommend tags for shown logs with no tags."""
        from AIFeatures.openai_prompter import tag_recommendations_enabled
        if not tag_recommendations_enabled():
            QMessageBox.information(
                self,
                "Tag Recommendations Disabled",
                "The tag recommendations feature is disabled in settings, or AI features are disabled in general. "
                "Please enable it to use this feature.",
            )
            return

        if not self._can_start_background_task():
            return

        self._start_background_task(
            title="Recommending Tags",
            label="Recommending tags for all shown logs...",
            func=self._batch_log_tag_recommendation_worker,
            ignore_already_tagged=True,
        )

    def _summarize_log_worker(self, log: Log | list[Log], custom_prompt: str | None = None):
        """Worker function to summarize log(s).

        Runs in a background thread; emits `summary_ready` with the
        resulting markdown so the UI thread can display it.
        """
        from AIFeatures.log_summarization import summarize_logs

        if isinstance(log, list):
            logs = log
        else:
            logs = [log]

        result = summarize_logs(logs, prompt=custom_prompt)

        # Emit signal; the connected slot will show the dialog on the UI thread.
        self.summary_ready.emit(result, len(logs))

    def _show_summary_dialog(self, markdown_text: str, log_count: int) -> None:
        """Show the markdown summary result in a dialog (UI thread)."""
        from UI.Homescreen.markdown_dialog import MarkdownDialog

        dialog_title = "Log Summary" if log_count == 1 else "Logs Summary"
        dlg = MarkdownDialog(dialog_title, markdown_text, parent=self)
        dlg.exec()

    # === AI Features: Content Summarization ===

    def _summarize_current_log(self):
        """Start background task: summarize the current log content."""
        from AIFeatures.openai_prompter import content_summarization_enabled
        if not content_summarization_enabled():
            QMessageBox.information(
                self,
                "Content Summarization Disabled",
                "The content summarization feature is disabled in settings, or AI features are disabled in general. "
                "Please enable it to use this feature.",
            )
            return

        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to summarize.")
            return

        if not self._can_start_background_task():
            return

        self._start_background_task(
            title="Summarizing Log",
            label="Summarizing the current log...",
            uncancelable=True,
            func=self._summarize_log_worker,
            log=self.current_log,
            custom_prompt=None,
        )

    def _summarize_all_shown_logs(self):
        """Start background task: summarize all shown logs."""
        if not self._can_start_background_task():
            return

        self._start_background_task(
            title="Summarizing Logs",
            label="Summarizing all shown logs...",
            func=self._summarize_log_worker,
            log=self.logs_viewer._filtered_logs,
            custom_prompt=None,
            uncancelable=True,
        )

    def _summarize_current_log_with_custom_prompt(self):
        """Start background task: summarize current log with custom prompt."""
        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to summarize.")
            return

        if not self._can_start_background_task():
            return

        from PyQt6.QtWidgets import QInputDialog

        prompt, ok = QInputDialog.getText(
            self,
            "Custom Summary Prompt",
            "Enter a custom prompt to guide the summary:",
        )
        if not ok:
            return

        self._start_background_task(
            title="Summarizing Log",
            label="Summarizing the current log with your custom prompt...",
            func=self._summarize_log_worker,
            log=self.current_log,
            custom_prompt=prompt or None,
            uncancelable=True,
        )

    def _summarize_all_shown_logs_with_custom_prompt(self):
        """Start background task: summarize all shown logs with custom prompt."""
        if not self._can_start_background_task():
            return

        from PyQt6.QtWidgets import QInputDialog

        prompt, ok = QInputDialog.getText(
            self,
            "Custom Summary Prompt",
            "Enter a custom prompt to guide the summary:",
        )
        if not ok:
            return

        self._start_background_task(
            title="Summarizing Logs",
            label="Summarizing all shown logs with your custom prompt...",
            func=self._summarize_log_worker,
            log=self.logs_viewer._filtered_logs,
            custom_prompt=prompt or None,
            uncancelable=True,
        )

    def _open_tag_editor(self):
        """Open the Tag Editor window."""
        # Block opening while a background task is running
        if self._background_task_running:
            QMessageBox.information(
                self,
                "Background Task Running",
                "Wait for the current AI task to finish before opening the Tag Editor.",
            )
            return
        # Prevent opening the tag editor if a tag manager is already open.
        from UI.TagManager import state as tag_manager_state  # type: ignore[import]

        if tag_manager_state.active_tag_manager is not None:
            QMessageBox.information(
                self,
                "Tag Manager Already Open",
                "You already have a tag manager open. Please close it "
                "before opening the tag editor.",
            )
            return

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

        # Block opening while a background task is running
        if self._background_task_running:
            QMessageBox.information(
                self,
                "Background Task Running",
                "Wait for the current AI task to finish before opening the Log Editor.",
            )
            return

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

        # Block opening while a background task is running
        if self._background_task_running:
            QMessageBox.information(
                self,
                "Background Task Running",
                "Wait for the current AI task to finish before opening the Log Editor.",
            )
            return

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

        # Disallow editing encrypted logs.
        if self.current_log.is_encrypted():
            QMessageBox.information(
                self,
                "Encrypted Log",
                "Encrypted logs cannot be edited. Please decrypt the log first.",
            )
            return

        log_editor = LogEditorWindow(self.current_log, parent=self)
        log_editor.show()

    def _delete_log(self):
        """Delete the currently selected log after user confirmation."""
        # Block delete while a background task is running
        if self._background_task_running:
            QMessageBox.information(
                self,
                "Background Task Running",
                "Wait for the current AI task to finish before deleting logs.",
            )
            return

        if self.current_log is None:
            QMessageBox.warning(self, "No Log Selected", "Please select a log to delete.")
            return

        # Disallow deleting encrypted logs.
        if self.current_log.is_encrypted():
            QMessageBox.information(
                self,
                "Encrypted Log",
                "Encrypted logs cannot be deleted. Please decrypt the log first.",
            )
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
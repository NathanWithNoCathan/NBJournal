import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
	QApplication,
	QMainWindow,
	QWidget,
	QVBoxLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QTextEdit,
	QPushButton,
	QToolBar,
	QMessageBox,
)
from PyQt6.QtGui import QAction, QFont

from DataClasses.log import Log
from UI.Homescreen.homescreen import HomeScreen
from UI.LogEditor import state as log_editor_state
from DataClasses.settings import user_settings

class LogEditorWindow(QMainWindow):
	"""Basic editor window for a single Log instance.

	Supports editing title, description and markdown body.
	Additional section buttons are stubbed for future features.
	"""

	def __init__(self, log: Log, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.log = log
		self._dirty = False
		self._auto_save_timer: QTimer | None = None

		self.setWindowTitle("NBJournal - Log Editor")
		self.resize(900, 700)

		self.homescreen: HomeScreen | None = None
		if parent and isinstance(parent, HomeScreen):
			self.homescreen = parent

		# Register this window as the currently active log editor.
		log_editor_state.active_log_editor = self

		self._init_ui()
		self._populate_from_log()
		self._init_auto_save()

	# --- UI setup -----------------------------------------------------
	def _init_ui(self) -> None:
		central = QWidget(self)
		root_layout = QVBoxLayout()
		root_layout.setContentsMargins(10, 10, 10, 10)
		root_layout.setSpacing(8)

		# Title field
		title_label = QLabel("Title")
		self.title_edit = QLineEdit()
		self.title_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))

		# Markdown body editor
		body_label = QLabel("Body (Markdown)")
		self.body_edit = QTextEdit()
		self.body_edit.setAcceptRichText(False)
		self.body_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))

		# Action buttons and status label
		actions_layout = QHBoxLayout()
		self.status_label = QLabel("")
		self.status_label.setStyleSheet("color: #888888; font-size: 10px;")
		self.status_label.setVisible(False)
		actions_layout.addWidget(self.status_label)
		actions_layout.addStretch(1)
		self.btn_save = QPushButton("Save")
		self.btn_cancel = QPushButton("Close")
		actions_layout.addWidget(self.btn_save)
		actions_layout.addWidget(self.btn_cancel)

		# Assemble layout
		root_layout.addWidget(title_label)
		root_layout.addWidget(self.title_edit)
		root_layout.addWidget(body_label)
		root_layout.addWidget(self.body_edit, 1)
		root_layout.addLayout(actions_layout)

		central.setLayout(root_layout)
		self.setCentralWidget(central)

		# Wiring signals
		self.btn_save.clicked.connect(self.save_log)
		self.btn_cancel.clicked.connect(self.close)
		self.title_edit.textChanged.connect(self._mark_dirty)
		self.body_edit.textChanged.connect(self._mark_dirty)

		self._create_menu_bar()
		self._update_window_modified()

	def _init_auto_save(self) -> None:
		"""Initialize auto-save timer based on global settings interval."""
		from DataClasses.settings import user_settings

		interval_minutes = user_settings.preferences.autosave_interval
		if interval_minutes and interval_minutes > 0:
			self._auto_save_timer = QTimer(self)
			self._auto_save_timer.setInterval(int(interval_minutes * 60_000))
			self._auto_save_timer.timeout.connect(self._auto_save_if_dirty)
			self._auto_save_timer.start()

	# --- Data binding -------------------------------------------------
	def _populate_from_log(self) -> None:
		"""Fill widgets from the current Log instance."""
		self.title_edit.setText(self.log.name)
		self.body_edit.setPlainText(self.log.body)
		self._dirty = False
		self._update_window_modified()

	def _update_log_from_widgets(self) -> None:
		"""Copy data from widgets back into the Log instance."""
		self.log.name = self.title_edit.text()
		self.log.body = self.body_edit.toPlainText()
		self.log.add_revision()
		self._dirty = False
		self._update_window_modified()

	# --- Actions ------------------------------------------------------
	def save_log(self) -> None:
		"""Update the Log object and persist it using its `save` method."""
		# If log has no title, prevent saving
		if self.title_edit.text().strip() == "":
			QMessageBox.warning(self, "Warning", "Log must have a title before saving.")
			return

		self._update_log_from_widgets()
		try:
			self.log.save()
		except Exception as exc:  # pragma: no cover - UI feedback
			QMessageBox.critical(self, "Error", f"Failed to save log:\n{exc}")
			return

		self._show_status("Saved")

		# Notify the homescreen (if available) that a log was saved so
		# it can refresh the logs list via its LogsViewer.
		if self.homescreen is not None:
			try:
				self.homescreen._on_log_saved(self.log)
			except Exception:
				pass

	def _auto_save_if_dirty(self) -> None:
		"""Auto-save the log if there are unsaved changes."""
		if not self._dirty:
			return
		# Avoid modal dialogs for auto-save; just skip if invalid.
		if self.title_edit.text().strip() == "":
			return
		self._update_log_from_widgets()
		try:
			self.log.save()
		except Exception:
			return
		self._show_status("Auto-saved")

	def _mark_dirty(self) -> None:
		"""Mark the editor as having unsaved changes."""
		self._dirty = True
		self._update_window_modified()

	def _update_window_modified(self) -> None:
		self.setWindowModified(self._dirty)

	def _show_status(self, text: str, duration_ms: int = 2000) -> None:
		"""Show a small transient text label indicating save status."""
		self.status_label.setText(text)
		self.status_label.setVisible(True)
		QTimer.singleShot(duration_ms, lambda: self.status_label.setVisible(False))

	def closeEvent(self, event):  # type: ignore[override]
		"""Prompt to save if there are unsaved changes before closing."""
		if self._dirty:
			res = QMessageBox.question(
				self,
				"Unsaved Changes",
				"The log has unsaved changes. Do you want to save before closing?",
				QMessageBox.StandardButton.Yes
				| QMessageBox.StandardButton.No
				| QMessageBox.StandardButton.Cancel,
				QMessageBox.StandardButton.Yes,
			)
			if res == QMessageBox.StandardButton.Cancel:
				event.ignore()
				return
			elif res == QMessageBox.StandardButton.Yes:
				self.save_log()
				# If still dirty (e.g. save failed), do not close.
				if self._dirty:
					event.ignore()
					return
		# Clear global reference when the window is actually closing.
		log_editor_state.active_log_editor = None
		event.accept()

	def _create_menu_bar(self):
		menuBar = self.menuBar()

		# View menu
		viewMenu = menuBar.addMenu("View")

		self.settings_action = QAction("Settings", self)
		if self.homescreen is not None:
			self.settings_action.triggered.connect(self.homescreen.open_settings)
		viewMenu.addAction(self.settings_action)
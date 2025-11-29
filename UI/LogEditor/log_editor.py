import sys

from PyQt6.QtCore import Qt
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
from PyQt6.QtGui import QAction

from DataClasses.log import Log
from UI.Homescreen.homescreen import HomeScreen

class LogEditorWindow(QMainWindow):
	"""Basic editor window for a single Log instance.

	Supports editing title, description and markdown body.
	Additional section buttons are stubbed for future features.
	"""

	def __init__(self, log: Log, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.log = log

		self.setWindowTitle("NBJournal - Log Editor")
		self.resize(900, 700)

		self.homescreen: HomeScreen | None = None
		if parent and isinstance(parent, HomeScreen):
			self.homescreen = parent

		self._init_ui()
		self._populate_from_log()

	# --- UI setup -----------------------------------------------------
	def _init_ui(self) -> None:
		central = QWidget(self)
		root_layout = QVBoxLayout()
		root_layout.setContentsMargins(10, 10, 10, 10)
		root_layout.setSpacing(8)

		# Title field
		title_label = QLabel("Title")
		self.title_edit = QLineEdit()

		# Markdown body editor
		body_label = QLabel("Body (Markdown)")
		self.body_edit = QTextEdit()
		self.body_edit.setAcceptRichText(False)

		# Action buttons
		actions_layout = QHBoxLayout()
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

		self._create_menu_bar()

	# --- Data binding -------------------------------------------------
	def _populate_from_log(self) -> None:
		"""Fill widgets from the current Log instance."""
		self.title_edit.setText(self.log.name)
		self.body_edit.setPlainText(self.log.body)

	def _update_log_from_widgets(self) -> None:
		"""Copy data from widgets back into the Log instance."""
		self.log.name = self.title_edit.text()
		self.log.body = self.body_edit.toPlainText()
		self.log.add_revision()

	# --- Actions ------------------------------------------------------
	def save_log(self) -> None:
		"""Update the Log object and persist it using its `save` method."""
		# If log has no title, prevent saving
		if self.log.name.strip() == "":
			QMessageBox.warning(self, "Warning", "Log must have a title before saving.")
			return

		self._update_log_from_widgets()
		try:
			self.log.save()
		except Exception as exc:  # pragma: no cover - UI feedback
			QMessageBox.critical(self, "Error", f"Failed to save log:\n{exc}")
			return

		QMessageBox.information(self, "Saved", "Log saved successfully.")

		# Notify the homescreen (if available) that a log was saved so
		# it can refresh the logs list via its LogsViewer.
		if self.homescreen is not None:
			try:
				self.homescreen._on_log_saved(self.log)
			except Exception:
				pass

	def _create_menu_bar(self):
		menuBar = self.menuBar()

		# View menu
		viewMenu = menuBar.addMenu("View")

		self.settings_action = QAction("Settings", self)
		self.settings_action.triggered.connect(self.homescreen.open_settings)
		viewMenu.addAction(self.settings_action)
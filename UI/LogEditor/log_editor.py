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

from DataClasses.log import Log


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

		# Description field
		desc_label = QLabel("Description")
		self.description_edit = QLineEdit()

		# Toolbar for future features (tags, markdown helpers, etc.)
		toolbar_layout = QHBoxLayout()

		self.btn_tags = QPushButton("Tags")
		self.btn_log_settings = QPushButton("Log Settings")
		self.btn_password = QPushButton("Password")
		self.btn_media = QPushButton("Embed Media")

		# Currently these are placeholders; they can later open dialogs
		for btn in (self.btn_tags, self.btn_log_settings, self.btn_password, self.btn_media):
			btn.setEnabled(False)
			toolbar_layout.addWidget(btn)
		toolbar_layout.addStretch(1)

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
		root_layout.addWidget(desc_label)
		root_layout.addWidget(self.description_edit)
		root_layout.addLayout(toolbar_layout)
		root_layout.addWidget(body_label)
		root_layout.addWidget(self.body_edit, 1)
		root_layout.addLayout(actions_layout)

		central.setLayout(root_layout)
		self.setCentralWidget(central)

		# Optional top toolbar with save/close
		toolbar = QToolBar("Log Editor", self)
		self.addToolBar(toolbar)

		btn_save_toolbar = QPushButton("Save")
		btn_close_toolbar = QPushButton("Close")
		toolbar.addWidget(btn_save_toolbar)
		toolbar.addWidget(btn_close_toolbar)

		# Wiring signals
		self.btn_save.clicked.connect(self.save_log)
		self.btn_cancel.clicked.connect(self.close)
		btn_save_toolbar.clicked.connect(self.save_log)
		btn_close_toolbar.clicked.connect(self.close)

	# --- Data binding -------------------------------------------------
	def _populate_from_log(self) -> None:
		"""Fill widgets from the current Log instance."""
		self.title_edit.setText(self.log.name)
		self.description_edit.setText(self.log.description)
		self.body_edit.setPlainText(self.log.body)

	def _update_log_from_widgets(self) -> None:
		"""Copy data from widgets back into the Log instance."""
		self.log.name = self.title_edit.text()
		self.log.description = self.description_edit.text()
		self.log.body = self.body_edit.toPlainText()
		self.log.add_revision()

	# --- Actions ------------------------------------------------------
	def save_log(self) -> None:
		"""Update the Log object and persist it using its `save` method."""
		self._update_log_from_widgets()
		try:
			self.log.save()
		except Exception as exc:  # pragma: no cover - UI feedback
			QMessageBox.critical(self, "Error", f"Failed to save log:\n{exc}")
			return

		QMessageBox.information(self, "Saved", "Log saved successfully.")


def main() -> None:
	"""Small manual test harness for the Log editor.

	Creates a temporary Log instance and opens it in the editor.
	"""

	# Simple default log – in real usage, pass a real Log instance
	demo_log = Log(
		name="New Log",
		description="",
		body="",
		path="demo_log.json",
	)

	app = QApplication(sys.argv)
	window = LogEditorWindow(demo_log)
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()


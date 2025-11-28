from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QHBoxLayout,
	QListWidget,
	QListWidgetItem,
	QLabel,
	QTextBrowser,
)

from DataClasses.log import Log, logs


class LogsViewer(QWidget):
	"""Widget that lists logs and shows the selected one side‑by‑side.

	This widget is intended to be embedded directly in other layouts
	(e.g. the `HomeScreen` central layout).  It exposes the currently
	selected `Log` via the `selected_log_changed` signal and the
	`current_log` property.
	"""

	selected_log_changed = pyqtSignal(object)  # emits `Log | None`

	def __init__(self, parent: Optional[QWidget] = None) -> None:
		super().__init__(parent)
		self._logs: list[Log] = logs
		self._current_log: Optional[Log] = None

		self._init_ui()
		self._populate_list()

	@property
	def current_log(self) -> Optional[Log]:
		"""Return the currently selected `Log`, if any."""
		return self._current_log

	def _init_ui(self) -> None:
		root_layout = QHBoxLayout()
		root_layout.setContentsMargins(0, 0, 0, 0)
		root_layout.setSpacing(8)

		# Left: list of logs
		list_layout = QVBoxLayout()
		list_label = QLabel("Logs")
		self.list_widget = QListWidget()
		self.list_widget.setSelectionMode(
			QListWidget.SelectionMode.SingleSelection
		)
		self.list_widget.currentItemChanged.connect(self._on_list_selection_changed)

		list_layout.addWidget(list_label)
		list_layout.addWidget(self.list_widget, 1)

		# Right: basic preview of selected log
		preview_layout = QVBoxLayout()
		self.preview_title = QLabel()
		self.preview_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
		self.preview_title.setStyleSheet("font-weight: bold; font-size: 14px;")

		self.preview_description = QLabel()
		self.preview_description.setWordWrap(True)
		self.preview_description.setStyleSheet("color: gray;")

		self.preview_body = QTextBrowser()
		self.preview_body.setOpenExternalLinks(True)

		preview_layout.addWidget(self.preview_title)
		preview_layout.addWidget(self.preview_description)
		preview_layout.addWidget(self.preview_body, 1)

		root_layout.addLayout(list_layout, 1)
		root_layout.addLayout(preview_layout, 2)

		self.setLayout(root_layout)

	def _populate_list(self) -> None:
		self.list_widget.clear()
		for log in self._logs:
			item = QListWidgetItem(log.name)
			# store the Log instance on the item for easy lookup
			item.setData(Qt.ItemDataRole.UserRole, log)
			self.list_widget.addItem(item)

		if self._logs:
			self.list_widget.setCurrentRow(0)

	def reload_logs(self) -> None:
		"""Reload the logs from the shared `logs` collection and refresh UI."""
		# Re-bind to the global `logs` list in case it changed elsewhere.
		from DataClasses.log import logs as global_logs  # local import to avoid cycles
		self._logs = global_logs
		self._populate_list()

	def _on_list_selection_changed(
		self,
		current: Optional[QListWidgetItem],
		previous: Optional[QListWidgetItem],  # noqa: ARG002 - kept for signal
	) -> None:
		log: Optional[Log]
		if current is None:
			log = None
		else:
			log = current.data(Qt.ItemDataRole.UserRole)

		self._current_log = log
		self._update_preview()
		self.selected_log_changed.emit(log)

	def _update_preview(self) -> None:
		log = self._current_log
		if log is None:
			self.preview_title.setText("")
			self.preview_description.setText("")
			self.preview_body.setHtml("")
			return

		self.preview_title.setText(log.name)
		self.preview_description.setText(log.description)
		# Treat the log body as markdown-like text rendered via basic HTML.
		# QTextBrowser understands a subset of HTML; if the body already
		# contains markdown, it can be pre-converted to HTML before
		# assignment. For now, we assume `log.body` holds HTML/markdown-
		# compatible content.
		self.preview_body.setMarkdown(log.body)
		
    
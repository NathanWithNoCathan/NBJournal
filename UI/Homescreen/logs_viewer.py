from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QHBoxLayout,
	QListWidget,
	QListWidgetItem,
	QLineEdit,
	QLabel,
	QTextBrowser,
)
from PyQt6.QtGui import QFont

from DataClasses.log import Log, logs
from DataClasses.settings import user_settings

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
		self._filtered_logs: list[Log] = list(self._logs)
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

		# Left: search + list of logs
		list_layout = QVBoxLayout()
		list_label = QLabel("Logs")
		self.search_bar = QLineEdit()
		self.search_bar.textChanged.connect(self._on_search_text_changed)

		self.list_widget = QListWidget()
		self.list_widget.setSelectionMode(
			QListWidget.SelectionMode.SingleSelection
		)
		self.list_widget.currentItemChanged.connect(self._on_list_selection_changed)

		list_layout.addWidget(list_label)
		list_layout.addWidget(self.search_bar)
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
		# Set font according to app settings
		self.preview_body.setFont(QFont(user_settings.log_viewer.font, user_settings.log_viewer.font_size))
		self.preview_body.setOpenExternalLinks(True)

		preview_layout.addWidget(self.preview_title)
		preview_layout.addWidget(self.preview_description)
		preview_layout.addWidget(self.preview_body, 1)

		root_layout.addLayout(list_layout, 1)
		root_layout.addLayout(preview_layout, 2)

		self.setLayout(root_layout)

	def _populate_list(self) -> None:
		self.list_widget.clear()

		# Ensure filters are applied
		self._apply_search_filter(self.search_bar.text())

		for log in self._filtered_logs:
			item = QListWidgetItem(log.name)
			# store the Log instance on the item for easy lookup
			item.setData(Qt.ItemDataRole.UserRole, log)
			self.list_widget.addItem(item)

		if self._filtered_logs:
			self.list_widget.setCurrentRow(0)

	def reload_logs(self) -> None:
		"""Reload the logs from the shared `logs` collection and refresh UI."""
		# Re-bind to the global `logs` list in case it changed elsewhere.
		from DataClasses.log import logs as global_logs  # local import to avoid cycles
		self._logs = global_logs
		self._filtered_logs = self._logs
		self._apply_search_filter()
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

	def _on_search_text_changed(self, text: str) -> None:
		"""Update the filtered list of logs when the search text changes."""
		# Populate list already applies the search filter
		self._populate_list()

	def _apply_search_filter(self, query: str = "") -> None:
		"""Filter and sort logs based on the provided query.

		This is the single place where searching/sorting logic lives so it can
		be easily extended.
		"""
		normalized = query.strip().lower()
		# Default sort is modified date descending
		sort = "modified"
		reversed_sort = True

		if not normalized:
			self._filtered_logs = list(self._logs)
		else:
			# Split query into list of queries
			# Queries are either just words to match the title/description
			# Or key:value pairs to match specific fields, e.g. "tag:work"
			# key:value pairs can be written as key:"value with quotes to include spaces"

			queries = []
			current = ""
			in_quotes = False
			for char in normalized:
				if char == '"':
					in_quotes = not in_quotes
				elif char == " " and not in_quotes:
					if current:
						queries.append(current)
						current = ""
				else:
					current += char
			if current:
				queries.append(current)

			# Check for sorting directive
			if "sort:alphabetical" in queries:
				sort = "alphabetical"
				queries.remove("sort:alphabetical")
			elif "sort:created" in queries:
				sort = "created"
				queries.remove("sort:created")
			elif "sort:modified" in queries:
				sort = "modified"
				queries.remove("sort:modified")

			# Reversed sort
			if "sort:reverse" in queries:
				reversed_sort = True
				queries.remove("sort:reverse")
			elif "sort:desc" in queries:
				reversed_sort = True
				queries.remove("sort:desc")

			# Forward sort
			if "sort:asc" in queries:
				reversed_sort = False
				queries.remove("sort:asc")
			elif "sort:forward" in queries:
				reversed_sort = False
				queries.remove("sort:forward")

			# Filtering
			def matches(log: Log) -> bool:
				for q in queries:
					if ":" in q:
						# key:value pair
						key, value = q.split(":", 1)
						value = value.strip('"')
						if key == "tag":
							if not any(t.name.lower() == value for t in log.tags):
								return False
						if key == "body":
							if value not in (log.body or "").lower():
								return False
						else:
							# Unknown key; ignore
							return False
					else:
						# simple word match in title or description
						if q not in (log.name or "").lower() and q not in (log.description or "").lower():
							return False
				return True
			
			# Apply filtering
			self._filtered_logs = [log for log in self._logs if matches(log)]

		# Default sort: alphabetical by title; customize this as needed.
		if sort == "alphabetical":
			self._filtered_logs.sort(key=lambda log: log.name.lower() if log.name else "")
		elif sort == "created":
			self._filtered_logs.sort(key=lambda log: log.created_at or 0)
		elif sort == "modified":
			self._filtered_logs.sort(key=lambda log: log.revised_at or 0)

		if reversed_sort:
			self._filtered_logs.reverse()

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
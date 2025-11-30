import sys
import os

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
	QFileDialog
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
		self.title_container = QWidget()
		title_layout = QVBoxLayout()
		title_layout.setContentsMargins(0, 0, 0, 0)
		title_label = QLabel("Title")
		self.title_edit = QLineEdit()
		self.title_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))
		title_layout.addWidget(title_label)
		title_layout.addWidget(self.title_edit)
		self.title_container.setLayout(title_layout)

		# Description field
		self.description_container = QWidget()
		description_layout = QVBoxLayout()
		description_layout.setContentsMargins(0, 0, 0, 0)
		description_label = QLabel("Description")
		self.description_edit = QTextEdit()
		self.description_edit.setAcceptRichText(False)
		self.description_edit.setFixedHeight(80)
		self.description_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))
		description_layout.addWidget(description_label)
		description_layout.addWidget(self.description_edit)
		self.description_container.setLayout(description_layout)

		# Markdown body editor
		self.body_container = QWidget()
		body_layout = QVBoxLayout()
		body_layout.setContentsMargins(0, 0, 0, 0)
		body_label = QLabel("Body (Markdown)")
		self.body_edit = QTextEdit()
		self.body_edit.setAcceptRichText(False)
		self.body_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))
		body_layout.addWidget(body_label)
		body_layout.addWidget(self.body_edit)
		self.body_container.setLayout(body_layout)

		# Action buttons and status label
		actions_layout = QHBoxLayout()
		self.status_label = QLabel("")
		self.status_label.setStyleSheet("color: #888888; font-size: 10px;")
		self.status_label.setVisible(False)
		actions_layout.addWidget(self.status_label)
		actions_layout.addStretch(1)
		self.btn_save = QPushButton("Save")
		self.btn_save.setToolTip("Save log (Ctrl+S)")
		self.btn_cancel = QPushButton("Close")
		self.btn_cancel.setToolTip("Close editor (Ctrl+W)")
		actions_layout.addWidget(self.btn_save)
		actions_layout.addWidget(self.btn_cancel)

		# Assemble layout
		root_layout.addWidget(self.title_container)
		root_layout.addWidget(self.description_container)
		root_layout.addWidget(self.body_container, 1)
		root_layout.addLayout(actions_layout)

		central.setLayout(root_layout)
		self.setCentralWidget(central)

		# Wiring signals
		self.btn_save.clicked.connect(self.save_log)
		self.btn_cancel.clicked.connect(self.close)
		self.title_edit.textChanged.connect(self._mark_dirty)
		self.description_edit.textChanged.connect(self._mark_dirty)
		self.body_edit.textChanged.connect(self._mark_dirty)

		# View mode: 0 = all, 1 = title+body, 2 = body only
		self._view_mode = 0

		# Set view mode from global settings
		self._set_view_mode(user_settings.log_editor.default_view_mode)

		self._create_menu_bar()
		self._create_shortcuts()
		self._update_window_modified()

	def _init_auto_save(self) -> None:
		"""Initialize auto-save timer based on global settings interval (seconds)."""
		from DataClasses.settings import user_settings

		interval_seconds = user_settings.preferences.autosave_interval
		if interval_seconds and interval_seconds > 0:
			self._auto_save_timer = QTimer(self)
			# QTimer interval is in milliseconds
			self._auto_save_timer.setInterval(int(interval_seconds * 1000))
			self._auto_save_timer.timeout.connect(self._auto_save_if_dirty)
			self._auto_save_timer.start()

	# --- Data binding -------------------------------------------------
	def _populate_from_log(self) -> None:
		"""Fill widgets from the current Log instance."""
		self.title_edit.setText(self.log.name)
		# Some logs may not yet have a description attribute
		self.description_edit.setPlainText(getattr(self.log, "description", ""))
		self.body_edit.setPlainText(self.log.body)
		self._dirty = False
		self._update_window_modified()

	def _update_log_from_widgets(self) -> None:
		"""Copy data from widgets back into the Log instance."""
		self.log.name = self.title_edit.text()
		# Keep description optional for backward compatibility
		setattr(self.log, "description", self.description_edit.toPlainText())
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
		
		# Update homescreen if applicable
		if self.homescreen is not None:
			try:
				self.homescreen._on_log_saved(self.log)
			except Exception:
				pass
			
		self._show_status("Auto-saved")

	def _mark_dirty(self) -> None:
		"""Mark the editor as having unsaved changes."""
		self._dirty = True
		self._update_window_modified()

	def _update_window_modified(self) -> None:
		self.setWindowModified(self._dirty)
		self._update_window_title()

	def _update_window_title(self) -> None:
		"""Optionally reflect view mode in the window title (non-invasive)."""
		mode_suffix = ""
		if self._view_mode == 1:
			mode_suffix = " [Title+Body]"
		elif self._view_mode == 2:
			mode_suffix = " [Body Only]"
		base_title = "NBJournal - Log Editor" + ("*" if self._dirty else "")
		self.setWindowTitle(base_title + mode_suffix)

	def _show_status(self, text: str, duration_ms: int = 2000) -> None:
		"""Show a small transient text label indicating save status."""
		self.status_label.setText(text)
		self.status_label.setVisible(True)
		QTimer.singleShot(duration_ms, lambda: self.status_label.setVisible(False))

	def _create_shortcuts(self) -> None:
		"""Create keyboard shortcut stubs for common actions.

		Currently wires basic shortcuts to existing slots where possible and
		leaves room for future expansion.
		"""
		from PyQt6.QtGui import QShortcut, QKeySequence

		# Save (Ctrl+S)
		QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save_log)

		# Close editor (Ctrl+W)
		QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)

		# Insert helpers (stubs already mapped to menu actions)
		# Heading shortcuts
		QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._insert_text_at_cursor("# "))
		QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._insert_text_at_cursor("## "))
		QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self._insert_text_at_cursor("### "))

		# Text formatting
		QShortcut(QKeySequence("Ctrl+B"), self, activated=lambda: self._insert_text_at_cursor("****", 2))
		QShortcut(QKeySequence("Ctrl+I"), self, activated=lambda: self._insert_text_at_cursor("**", 1))
		QShortcut(QKeySequence("Ctrl+Shift+B"), self, activated=lambda: self._insert_text_at_cursor("******", 3))
		QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self._insert_text_at_cursor("~~~~", 2))
		QShortcut(QKeySequence("Ctrl+`"), self, activated=lambda: self._insert_text_at_cursor("``", 1))

		# Lists and code blocks
		QShortcut(QKeySequence("Ctrl+L"), self, activated=self._insert_bullet_list)
		QShortcut(QKeySequence("Ctrl+Shift+L"), self, activated=self._insert_numbered_list)
		QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=lambda: self._insert_text_at_cursor("```\n\n```", 4))
		QShortcut(QKeySequence("Ctrl+Shift+T"), self, activated=self._insert_task_list)

		# Horizontal rule
		QShortcut(QKeySequence("Ctrl+R"), self, activated=lambda: self._insert_text_at_cursor("\n---\n"))

		# Insert link to website
		QShortcut(QKeySequence("Ctrl+K"), self, activated=lambda: self._insert_text_at_cursor("[]()", 3))
		# Insert link to file/folder, open file dialog
		QShortcut(QKeySequence("Ctrl+Shift+K"), self, activated=self._insert_file_link)

		# Tag manager/editor
		QShortcut(QKeySequence("Ctrl+Shift+M"), self, activated=self._open_tag_manager)
		QShortcut(QKeySequence("Ctrl+Shift+E"), self, activated=self._open_tag_editor)

		# Cycle view modes (Ctrl+Shift+V)
		QShortcut(QKeySequence("Ctrl+Shift+V"), self, activated=self._cycle_view_mode)

		# Set view modes
		QShortcut(QKeySequence("Ctrl+Shift+A"), self, activated=lambda: self._set_view_mode(0))
		QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=lambda: self._set_view_mode(1))
		QShortcut(QKeySequence("Ctrl+Shift+D"), self, activated=lambda: self._set_view_mode(2))

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

		# Auto save timer cleanup
		if self._auto_save_timer is not None:
			self._auto_save_timer.stop()
			self._auto_save_timer.deleteLater()
			self._auto_save_timer = None

		event.accept()

	def _create_menu_bar(self):
		menuBar = self.menuBar()

		# Insert menu
		insertMenu = menuBar.addMenu("Insert")

		# Various markdown elements
		heading_section = insertMenu.addMenu("Heading")

		self.heading1_action = QAction("Heading 1 (ctrl+1)", self)
		self.heading1_action.triggered.connect(lambda: self._insert_text_at_cursor("# "))
		heading_section.addAction(self.heading1_action)

		self.heading2_action = QAction("Heading 2 (ctrl+2)", self)
		self.heading2_action.triggered.connect(lambda: self._insert_text_at_cursor("## "))
		heading_section.addAction(self.heading2_action)

		self.heading3_action = QAction("Heading 3 (ctrl+3)", self)
		self.heading3_action.triggered.connect(lambda: self._insert_text_at_cursor("### "))
		heading_section.addAction(self.heading3_action)

		text_formatting = insertMenu.addMenu("Text Formatting")

		self.bold_action = QAction("Bold (ctrl+B)", self)
		self.bold_action.triggered.connect(lambda: self._insert_text_at_cursor("****", 2))
		text_formatting.addAction(self.bold_action)

		self.italic_action = QAction("Italic (ctrl+I)", self)
		self.italic_action.triggered.connect(lambda: self._insert_text_at_cursor("**", 1))
		text_formatting.addAction(self.italic_action)

		self.bold_italic_action = QAction("Bold + Italic (ctrl+Shift+B)", self)
		self.bold_italic_action.triggered.connect(lambda: self._insert_text_at_cursor("******", 3))
		text_formatting.addAction(self.bold_italic_action)

		self.strikethrough_action = QAction("Strikethrough (ctrl+T)", self)
		self.strikethrough_action.triggered.connect(lambda: self._insert_text_at_cursor("~~~~", 2))
		text_formatting.addAction(self.strikethrough_action)

		self.inline_code_action = QAction("Inline Code (ctrl+`)", self)
		self.inline_code_action.triggered.connect(lambda: self._insert_text_at_cursor("``", 1))
		text_formatting.addAction(self.inline_code_action)

		self.code_block_action = QAction("Code Block (ctrl+Shift+C)", self)
		self.code_block_action.triggered.connect(lambda: self._insert_text_at_cursor("```\n\n```", 4))
		insertMenu.addAction(self.code_block_action)

		insertMenu.addSeparator()

		self.bullet_list_action = QAction("Bullet List (ctrl+L)", self)
		self.bullet_list_action.triggered.connect(self._insert_bullet_list)
		insertMenu.addAction(self.bullet_list_action)

		self.numbered_list_action = QAction("Numbered List (ctrl+Shift+L)", self)
		self.numbered_list_action.triggered.connect(self._insert_numbered_list)
		insertMenu.addAction(self.numbered_list_action)

		self.task_list_action = QAction("Task List (ctrl+Shift+T)", self)
		self.task_list_action.triggered.connect(self._insert_task_list)
		insertMenu.addAction(self.task_list_action)

		insertMenu.addSeparator()

		self.horizontal_rule_action = QAction("Horizontal Rule (ctrl+R)", self)
		self.horizontal_rule_action.triggered.connect(lambda: self._insert_text_at_cursor("\n---\n"))
		insertMenu.addAction(self.horizontal_rule_action)

		insertMenu.addSeparator()

		self.link_action = QAction("Insert Link (ctrl+K)", self)
		self.link_action.triggered.connect(lambda: self._insert_text_at_cursor("[]()", 3))
		insertMenu.addAction(self.link_action)

		self.file_link_action = QAction("Insert File/Folder Link (ctrl+Shift+K)", self)
		self.file_link_action.triggered.connect(self._insert_file_link)
		insertMenu.addAction(self.file_link_action)

		# Tag submenu containing Tag Manager and Tag Editor
		tagMenu = menuBar.addMenu("Tag")

		self.tag_manager_action = QAction("Tag Manager (ctrl+Shift+M)", self)
		self.tag_manager_action.triggered.connect(self._open_tag_manager)
		tagMenu.addAction(self.tag_manager_action)

		self.tag_editor_action = QAction("Tag Editor (ctrl+Shift+E)", self)
		self.tag_editor_action.triggered.connect(self._open_tag_editor)
		tagMenu.addAction(self.tag_editor_action)

		# View menu
		viewMenu = menuBar.addMenu("View")

		self.settings_action = QAction("Settings", self)
		if self.homescreen is not None:
			self.settings_action.triggered.connect(self.homescreen.open_settings)
		viewMenu.addAction(self.settings_action)

		# Layout submenu for mode switching
		layoutMenu = menuBar.addMenu("Layout")
		self.cycle_view_action = QAction("Cycle View Modes (Ctrl+Shift+V)", self)
		self.cycle_view_action.triggered.connect(self._cycle_view_mode)
		layoutMenu.addAction(self.cycle_view_action)

		self.title_desc_body_action = QAction("Title+Description+Body (ctrl+Shift+A)", self)
		layoutMenu.addAction(self.title_desc_body_action)
		self.title_desc_body_action.triggered.connect(lambda: self._set_view_mode(0))

		self.title_body_action = QAction("Title+Body (ctrl+Shift+S)", self)
		layoutMenu.addAction(self.title_body_action)
		self.title_body_action.triggered.connect(lambda: self._set_view_mode(1))

		self.body_only_action = QAction("Body Only (ctrl+Shift+D)", self)
		layoutMenu.addAction(self.body_only_action)
		self.body_only_action.triggered.connect(lambda: self._set_view_mode(2))

		# Help menu
		helpMenu = menuBar.addMenu("Help")

		HELP_MARKDOWN_GUIDE = """
MARKDOWN QUICK GUIDE (FOR JOURNAL ENTRIES)
=========================================

BASIC FORMATTING
----------------
Bold:        **text**
Italic:      *text*
Bold+Italic: ***text***
Strikethrough: ~~text~~

HEADINGS
--------
# Heading 1
## Heading 2
### Heading 3

LISTS
-----
Bullet list:
- item one
- item two

Numbered list:
1. first item
2. second item

TASK LISTS (CHECKBOXES)
-----------------------
- [ ] thing to do
- [x] finished thing

HORIZONTAL LINE
---------------
Use three dashes:
---

CODE
----
Inline code example:
Use `print("hi")` format for inline code.

Code block example (indent by four spaces):
    print("Hello journal!")

LINKS (WEB, FILES, FOLDERS)
---------------------------
Web link example:
[Example](https://example.com)

Link to a file (opens in your system's default app):
[My PDF](file:///C:/Users/you/Documents/notes.pdf)
[Notes](file:///home/you/Documents/notes.txt)

Link to a folder (opens file explorer):
[Journal Folder](file:///C:/Users/you/Documents/Journal/)
[Projects](file:///home/you/Projects/)

TIPS FOR FILE LINKS
-------------------
- Use: file:/// + full absolute path
- Windows paths: C:/Users/you/Documents/...
- Spaces in paths usually work fine
- Make sure the file or folder actually exists

GOOD HABITS
-----------
- Prefer absolute paths
- Avoid moving files after linking them
- Double-check path spelling if something won't open
"""
		self.markdown_help_action = QAction("Markdown Guide", self)
		self.markdown_help_action.triggered.connect(lambda: QMessageBox.information(
			self,
			"Markdown Quick Guide",
			HELP_MARKDOWN_GUIDE
		))
		helpMenu.addAction(self.markdown_help_action)

		self.tag_guide = QAction("Tagging Guide", self)
		self.tag_guide.triggered.connect(lambda: QMessageBox.information(
			self,
			"Tagging Quick Guide",
			"Tags are labels you can assign to your journal entries to help organize and categorize them.\n\n"
			"To manage your tags, use the Tag Manager from the Tag menu. You can add new tags or remove existing ones there.\n\n"
			"To create, edit, or delete tags in detail, use the Tag Editor also found in the Tag menu.\n\n"
			"Once you have tags created, you can assign them to your journal entries while editing a log.\n\n"
			"Tags help you filter and find related entries easily in the Homescreen view.\n\n"
			"They can also help provide statistics about your journaling habits over time, such as how often you write about certain topics."
		))
		helpMenu.addAction(self.tag_guide)

	def _insert_text_at_cursor(self, text: str, position=None) -> None:
		"""Insert the given text at the current cursor position in the body editor."""
		cursor = self.body_edit.textCursor()
		cursor.insertText(text)
		self.body_edit.setTextCursor(cursor)
		self._mark_dirty()

		if position is not None:
			# Move cursor to specified position relative to insertion point
			cursor.setPosition(cursor.position() - position)
			self.body_edit.setTextCursor(cursor)

	def _current_line_info(self):
		"""Return (cursor, line_text, line_start, line_end) for current line."""
		cursor = self.body_edit.textCursor()
		block = cursor.block()
		line_text = block.text()
		line_start = block.position()
		line_end = line_start + len(line_text)
		return cursor, line_text, line_start, line_end

	def _insert_bullet_list(self) -> None:
		"""Insert or extend a bullet list at the current line.

		- If current line does not start with a bullet, insert two new
		  items: "- " and "- " on the next line.
		- If it does start with a bullet, append a new "- " item on the
		  following line.
		"""
		cursor, line_text, line_start, line_end = self._current_line_info()
		leading = line_text.lstrip()
		indent_len = len(line_text) - len(leading)
		indent = line_text[:indent_len]

		is_bullet = leading.startswith("- ")

		if not is_bullet:
			# Start a new list with two items, respecting existing indentation.
			cursor.beginEditBlock()
			cursor.setPosition(line_start)
			cursor.insertText(f"{indent}- \n{indent}- ")
			# Place cursor after second "- "
			cursor.setPosition(line_start + len(f"{indent}- \n{indent}- "))
			cursor.endEditBlock()
		else:
			# Extend existing list: add a new item on the next line.
			cursor.beginEditBlock()
			cursor.setPosition(line_end)
			cursor.insertText(f"\n{indent}- ")
			cursor.setPosition(line_end + len(f"\n{indent}- "))
			cursor.endEditBlock()

		self.body_edit.setTextCursor(cursor)
		self._mark_dirty()

	def _insert_numbered_list(self) -> None:
		"""Insert or extend a numbered list at the current line.

		Behavior mirrors bullet lists but uses "1.", "2.", etc. When
		extending an existing list, the new item number is the next
		integer after the highest number found in the list up to the
		current line (simple upward scan within the same indentation).
		"""
		cursor, line_text, line_start, line_end = self._current_line_info()
		leading = line_text.lstrip()
		indent_len = len(line_text) - len(leading)
		indent = line_text[:indent_len]

		# Detect if line starts with something like "1. "
		import re
		m = re.match(r"^(\d+)\.\s", leading)
		is_numbered = m is not None

		if not is_numbered:
			# Start a new list: "1." and "2." items.
			cursor.beginEditBlock()
			cursor.setPosition(line_start)
			cursor.insertText(f"{indent}1. \n{indent}2. ")
			cursor.setPosition(line_start + len(f"{indent}1. \n{indent}2. "))
			cursor.endEditBlock()
		else:
			# Determine next number by looking at lines above with same indentation.
			block = cursor.block()
			import re as _re
			max_num = int(m.group(1))
			b = block.previous()
			while b.isValid():
				text = b.text()
				if not text.startswith(indent):
					break
				lead = text[len(indent):]
				m2 = _re.match(r"^(\d+)\.\s", lead)
				if m2:
					max_num = max(max_num, int(m2.group(1)))
				b = b.previous()

			next_num = max_num + 1
			cursor.beginEditBlock()
			cursor.setPosition(line_end)
			cursor.insertText(f"\n{indent}{next_num}. ")
			cursor.setPosition(line_end + len(f"\n{indent}{next_num}. "))
			cursor.endEditBlock()

		self.body_edit.setTextCursor(cursor)
		self._mark_dirty()

	def _insert_task_list(self) -> None:
		"""Insert or extend a markdown task list at the current line.

		- If current line is not a task item, create two items:
		  "- [ ] " on this line and the next.
		- If current line is a task item (checked or unchecked), add a
		  new unchecked item on the following line, preserving
		  indentation.
		"""
		cursor, line_text, line_start, line_end = self._current_line_info()
		leading = line_text.lstrip()
		indent_len = len(line_text) - len(leading)
		indent = line_text[:indent_len]

		# Match "- [ ] ", "- [x] ", "- [X] " etc. at line start (ignoring indent).
		import re
		is_task = re.match(r"^- \[[ xX]\] \s*", leading) is not None

		if not is_task:
			cursor.beginEditBlock()
			cursor.setPosition(line_start)
			cursor.insertText(f"{indent}- [ ] \n{indent}- [ ] ")
			cursor.setPosition(line_start + len(f"{indent}- [ ] \n{indent}- [ ] "))
			cursor.endEditBlock()
		else:
			cursor.beginEditBlock()
			cursor.setPosition(line_end)
			cursor.insertText(f"\n{indent}- [ ] ")
			cursor.setPosition(line_end + len(f"\n{indent}- [ ] "))
			cursor.endEditBlock()

		self.body_edit.setTextCursor(cursor)
		self._mark_dirty()

	def _open_tag_manager(self) -> None:
		"""Open the simple add/remove Tag Manager window.

		Prevents opening if the Tag Editor (from homescreen) is active
		by checking shared global state.
		"""
		from UI.TagManager.tag_manager import TagManagerWindow  # type: ignore[import]
		from UI.TagEditor import state as tag_editor_state
		from UI.TagManager import state as tag_manager_state

		# If the Tag Editor is open, do not allow Tag Manager
		if getattr(tag_editor_state, "active_tag_editor", None) is not None:
			QMessageBox.information(
				self,
				"Tag Editor Already Open",
				"You already have the Tag Editor open. Please close it "
				"before opening the Tag Manager.",
			)
			return

		# Do not allow multiple Tag Manager windows
		if getattr(tag_manager_state, "active_tag_manager", None) is not None:
			QMessageBox.information(
				self,
				"Tag Manager Already Open",
				"You already have a Tag Manager window open.",
			)
			return

		if self.log is None:
			QMessageBox.warning(self, "No Log", "No log is loaded in this editor.")
			return

		mgr = TagManagerWindow(self.log, parent=self)
		mgr.show()

		# Mark as dirty since tags changed
		self._mark_dirty()

	def _open_tag_editor(self) -> None:
		"""Open the Tag Editor window from the log editor.

		Also respects the shared state so it cannot be opened while
		the Tag Manager is active.
		"""
		from UI.TagEditor.tag_editor import TagEditorWindow  # type: ignore[import]
		from UI.TagEditor import state as tag_editor_state
		from UI.TagManager import state as tag_manager_state

		# If Tag Manager is open, do not open Tag Editor.
		if getattr(tag_manager_state, "active_tag_manager", None) is not None:
			QMessageBox.information(
				self,
				"Tag Manager Already Open",
				"You already have the Tag Manager open. Please close it "
				"before opening the Tag Editor.",
			)
			return

		# Do not allow multiple Tag Editor windows via its own state.
		if getattr(tag_editor_state, "active_tag_editor", None) is not None:
			QMessageBox.information(
				self,
				"Tag Editor Already Open",
				"You already have a Tag Editor window open.",
			)
			return

		editor = TagEditorWindow(parent=self)
		editor.show()

	def _insert_file_link(self) -> None:
		"""Insert a markdown link for either a file or a folder.

		Previously this only allowed selecting files. Now it first
		prompts for a file; if the user cancels that, it then prompts
		for a directory. If both are cancelled, nothing is inserted.
		"""
		# First, try selecting a file.
		path, _ = QFileDialog.getOpenFileName(self, "Select File")
		if not path:
			# If the user didn't pick a file, offer a folder instead.
			path = QFileDialog.getExistingDirectory(self, "Select Folder")
			if not path:
				return

		# Build a markdown link using the base name as the label.
		self._insert_text_at_cursor(f"[{os.path.basename(path)}]({path.replace(' ', '%20')})", 3)

	def _set_view_mode(self, mode: int) -> None:
		"""Set the view mode to the specified value and apply it."""
		if mode not in (0, 1, 2):
			return
		self._view_mode = mode
		self._apply_view_mode()

	def _apply_view_mode(self) -> None:
		"""Apply current view mode to title/description/body containers.

		Modes:
		- 0: title, description, and body visible
		- 1: title and body visible (description hidden)
		- 2: body only visible
		"""
		if self._view_mode == 0:
			self.title_container.setVisible(True)
			self.description_container.setVisible(True)
			self.body_container.setVisible(True)
		elif self._view_mode == 1:
			self.title_container.setVisible(True)
			self.description_container.setVisible(False)
			self.body_container.setVisible(True)
		else:  # 2
			self.title_container.setVisible(False)
			self.description_container.setVisible(False)
			self.body_container.setVisible(True)

		self._update_window_title()

	def _cycle_view_mode(self) -> None:
		"""Cycle between 3 view modes for clutter reduction."""
		self._view_mode = (self._view_mode + 1) % 3
		self._apply_view_mode()
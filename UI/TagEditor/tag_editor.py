from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from DataClasses.settings import user_settings
from DataClasses.tag import Tag, tags as global_tags
from DataClasses.log import logs as global_logs
from UI.TagEditor import state as tag_editor_state


class EditorState(Enum):
    IDLE = auto()
    CREATING = auto()
    EDITING = auto()


class TagEditorWindow(QMainWindow):
    """Standalone Tag editor window.

    - Create, edit, and delete tags
    - Keeps explicit state (idle / creating / editing)
    - Disables text fields when not creating/editing
    - Uses global `tags` list from `DataClasses.tag`
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("NBJournal - Tag Editor")
        self.resize(600, 450)

        self._current_tag: Optional[Tag] = None
        self._state: EditorState = EditorState.IDLE

        # Register this window as the active tag editor.
        tag_editor_state.active_tag_editor = self

        self._init_ui()
        self._populate_list()
        self._apply_state()

        # Shortcuts
        self._create_shortcuts()

    # --- UI setup -------------------------------------------------
    def _init_ui(self) -> None:
        central = QWidget(self)
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Left side: list of tags + basic actions
        left_layout = QVBoxLayout()

        list_label = QLabel("Tags (double-click/enter/space to edit)")
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_new.setToolTip("Create new tag (Ctrl+N)")
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setToolTip("Delete selected tag (Del / Ctrl+D / Backspace)")
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_delete)

        left_layout.addWidget(list_label)
        left_layout.addWidget(self.list_widget, 1)
        left_layout.addLayout(btn_row)

        # Right side: editor pane
        right_layout = QVBoxLayout()

        # Mode / hint label
        self.mode_label = QLabel("")
        self.mode_label.setStyleSheet("font-size: 11px")

        name_label = QLabel("Name")
        self.name_edit = QLineEdit()
        self.name_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))

        desc_label = QLabel("Description")
        self.desc_edit = QTextEdit()
        self.desc_edit.setAcceptRichText(False)
        self.desc_edit.setFont(QFont(user_settings.log_editor.font, user_settings.log_editor.font_size))

        actions_row = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.setToolTip("Save tag (Ctrl+S)")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setToolTip("Cancel edit (Esc)")
        self.btn_close = QPushButton("Close")
        self.btn_close.setToolTip("Close window (Ctrl+W)")
        actions_row.addStretch(1)
        actions_row.addWidget(self.btn_save)
        actions_row.addWidget(self.btn_cancel)
        actions_row.addWidget(self.btn_close)

        right_layout.addWidget(self.mode_label)
        right_layout.addWidget(name_label)
        right_layout.addWidget(self.name_edit)
        right_layout.addWidget(desc_label)
        right_layout.addWidget(self.desc_edit, 1)
        right_layout.addLayout(actions_row)

        root_layout.addLayout(left_layout, 0)
        root_layout.addLayout(right_layout, 1)

        central.setLayout(root_layout)
        self.setCentralWidget(central)

        # Wiring
        self.btn_new.clicked.connect(self._begin_create)
        self.btn_delete.clicked.connect(self._delete_current_tag)
        self.btn_save.clicked.connect(self._save_current)
        self.btn_cancel.clicked.connect(self._cancel_edit)
        self.btn_close.clicked.connect(self.close)

    def _create_shortcuts(self) -> None:
        # New tag (Ctrl+N)  
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._begin_create)

        # Save (Ctrl+S)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_current)

        # Cancel edit (Esc)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._cancel_edit)

        # Delete tag (Del, Ctrl+D, backspace)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, activated=self._delete_current_tag)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self._delete_current_tag)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self, activated=self._delete_current_tag)

        # Close window (Ctrl+W)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)

        # Edit tag (Enter/space)
        QShortcut(QKeySequence("Enter"), self, activated=lambda: self._on_item_double_clicked(self._current_item()) if self._current_item() else None)
        QShortcut(QKeySequence("Return"), self, activated=lambda: self._on_item_double_clicked(self._current_item()) if self._current_item() else None)
        QShortcut(QKeySequence("Space"), self, activated=lambda: self._on_item_double_clicked(self._current_item()) if self._current_item() else None)

    # --- State handling -------------------------------------------
    def _set_state(self, state: EditorState) -> None:
        self._state = state
        self._apply_state()

    def _apply_state(self) -> None:
        # Text fields enabled only when creating or editing
        editable = self._state in (EditorState.CREATING, EditorState.EDITING)
        self.name_edit.setEnabled(editable)
        self.desc_edit.setEnabled(editable)

        # Save/Cancel only make sense while creating or editing
        self.btn_save.setEnabled(editable)
        self.btn_cancel.setEnabled(editable)

        # New always allowed, Delete only when there is selection
        self.btn_new.setEnabled(True)
        self.btn_delete.setEnabled(self._current_item() is not None)

        # When idle and nothing selected, clear editors
        if self._state == EditorState.IDLE and self._current_tag is None:
            self.name_edit.clear()
            self.desc_edit.clear()

        # Update mode label text
        if self._state == EditorState.CREATING:
            self.mode_label.setText("Mode: Creating new tag")
        elif self._state == EditorState.EDITING:
            self.mode_label.setText("Mode: Editing tag")
        else:
            if self._current_tag is not None:
                self.mode_label.setText("Mode: Viewing tag")
            else:
                self.mode_label.setText("Mode: Idle (no tag selected)")

    # --- Data binding ---------------------------------------------
    def _populate_list(self) -> None:
        self.list_widget.clear()
        for tag in global_tags:
            item = QListWidgetItem(tag.name)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.list_widget.addItem(item)

    def _load_tag_into_editors(self, tag: Optional[Tag]) -> None:
        self._current_tag = tag
        if tag is None:
            self.name_edit.clear()
            self.desc_edit.clear()
            return

        self.name_edit.setText(tag.name)
        self.desc_edit.setPlainText(tag.description)

    # --- Helpers --------------------------------------------------
    def _current_item(self) -> Optional[QListWidgetItem]:
        items = self.list_widget.selectedItems()
        return items[0] if items else None

    # --- Slots ----------------------------------------------------
    def _on_selection_changed(self) -> None:
        # Only react to selection when not in the middle of an edit
        if self._state in (EditorState.CREATING, EditorState.EDITING):
            return

        item = self._current_item()
        if item is None:
            self._current_tag = None
            self._set_state(EditorState.IDLE)
            return

        self._current_tag = item.data(Qt.ItemDataRole.UserRole)
        self._load_tag_into_editors(self._current_tag)
        self._set_state(EditorState.IDLE)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        # Start editing on double-click of a list item
        if item is None:
            return
        self._current_tag = item.data(Qt.ItemDataRole.UserRole)
        self._load_tag_into_editors(self._current_tag)
        self._set_state(EditorState.EDITING)
        self.name_edit.setFocus()

    def _begin_create(self) -> None:
        self.list_widget.clearSelection()
        self._current_tag = None
        self.name_edit.clear()
        self.desc_edit.clear()
        self._set_state(EditorState.CREATING)
        self.name_edit.setFocus()

    def _cancel_edit(self) -> None:
        # Revert fields to selected tag, or clear if none
        item = self._current_item()
        if item is not None:
            self._current_tag = item.data(Qt.ItemDataRole.UserRole)
            self._load_tag_into_editors(self._current_tag)
        else:
            self._current_tag = None
            self.name_edit.clear()
            self.desc_edit.clear()
        self._set_state(EditorState.IDLE)

    def _save_current(self) -> None:
        if self._state not in (EditorState.CREATING, EditorState.EDITING):
            return

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Tag must have a name.")
            return

        # Prevent duplicate names
        for existing in global_tags:
            if self._state == EditorState.CREATING:
                if existing.name == name:
                    QMessageBox.warning(self, "Warning", "A tag with this name already exists.")
                    return
            else:  # editing
                if existing is not self._current_tag and existing.name == name:
                    QMessageBox.warning(self, "Warning", "Another tag with this name already exists.")
                    return

        desc = self.desc_edit.toPlainText().strip()

        if self._state == EditorState.CREATING:
            try:
                new_tag = Tag(name=name, description=desc)
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to create tag:\n{exc}")
                return

            global_tags.append(new_tag)
            item = QListWidgetItem(new_tag.name)
            item.setData(Qt.ItemDataRole.UserRole, new_tag)
            self.list_widget.addItem(item)
            self.list_widget.setCurrentItem(item)
            self._current_tag = new_tag

            try:
                new_tag.save()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to save tag:\n{exc}")
                return

        else:  # EDITING
            if self._current_tag is None:
                QMessageBox.warning(self, "Warning", "No tag selected.")
                return

            old_tag = self._current_tag
            try:
                updated = Tag(name=name, description=desc)
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to update tag:\n{exc}")
                return

            # Persist updated tag and propagate changes to logs
            try:
                from DataClasses.tag import TAGS_FOLDER
                import os

                if old_tag.name != updated.name:
                    old_path = os.path.join(TAGS_FOLDER, f"{old_tag.name}.json")
                    if os.path.exists(old_path):
                        os.remove(old_path)
                updated.save()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to save tag:\n{exc}")
                return

            # Replace in global tag list
            idx = global_tags.index(old_tag)
            global_tags[idx] = updated
            self._current_tag = updated

            # Update any logs that reference this tag (by name)
            from DataClasses.tag import Tag as TagClass
            for log in global_logs:
                changed = False
                new_tags: list[TagClass] = []
                for t in log.tags:
                    if isinstance(t, TagClass) and t.name == old_tag.name:
                        new_tags.append(updated)
                        changed = True
                    else:
                        new_tags.append(t)
                if changed:
                    log.tags = new_tags
                    try:
                        log.save()  
                    except Exception:
                        # If a log fails to save, continue with others
                        continue

            # Refresh list item text/binding
            item = self._current_item()
            if item is not None:    
                item.setText(updated.name)
                item.setData(Qt.ItemDataRole.UserRole, updated)

        self._set_state(EditorState.IDLE)

    def _delete_current_tag(self) -> None:
        item = self._current_item()
        if item is None:
            return

        tag: Tag = item.data(Qt.ItemDataRole.UserRole)
        res = QMessageBox.question(
            self,
            "Delete Tag",
            f"Delete tag '{tag.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        # Remove from global list
        try:
            global_tags.remove(tag)
        except ValueError:
            pass

        # Remove this tag from all logs and resave them
        from DataClasses.tag import Tag as TagClass
        for log in global_logs:
            original_count = len(log.tags)
            log.tags = [t for t in log.tags if not (isinstance(t, TagClass) and t.name == tag.name)]
            if len(log.tags) != original_count:
                try:
                    log.save()
                except Exception:
                    continue

        # Remove persisted JSON file, if it exists
        try:
            from DataClasses.tag import TAGS_FOLDER
            import os

            filepath = os.path.join(TAGS_FOLDER, f"{tag.name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            # Silently ignore file deletion issues
            pass

        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)

        # Select next item (same row index) if available, otherwise previous
        count = self.list_widget.count()
        next_row = min(row, count - 1) if count > 0 else -1
        if next_row >= 0:
            self.list_widget.setCurrentRow(next_row)
            item = self._current_item()
            if item is not None:
                self._current_tag = item.data(Qt.ItemDataRole.UserRole)
                self._load_tag_into_editors(self._current_tag)
            else:
                self._current_tag = None
        else:
            self._current_tag = None
            self.name_edit.clear()
            self.desc_edit.clear()

        self._set_state(EditorState.IDLE)

    # --- Close handling -------------------------------------------
    def closeEvent(self, event) -> None:  # type: ignore[override]
        tag_editor_state.active_tag_editor = None
        event.accept()

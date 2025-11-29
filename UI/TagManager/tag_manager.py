from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QDialog,
	QVBoxLayout,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QListWidgetItem,
	QPushButton,
)

from DataClasses.tag import Tag, tags as global_tags
from DataClasses.log import Log


class TagManagerWindow(QDialog):
    """Window to attach/detach existing tags to a specific Log.

    This does NOT create or delete tags globally; it only toggles
    which of the already-defined tags are attached to the given log.
    """

    def __init__(self, log: Log, parent=None) -> None:
        super().__init__(parent)
        self._log = log

        # Register this instance in module-level state so other
        # UI components can prevent multiple windows.
        from UI.TagManager import state as tag_manager_state

        tag_manager_state.active_tag_manager = self

        self.setWindowTitle("NBJournal - Tag Manager")
        self.resize(450, 320)

        root = QVBoxLayout()

        # Info label
        root.addWidget(QLabel("Toggle which tags are attached to this log:"))

        # List of available tags with check state = attached/not attached
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        root.addWidget(self.list_widget, 1)

        # Close/apply button (changes are applied immediately on click)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.btn_close = QPushButton("Close")
        btn_layout.addWidget(self.btn_close)
        root.addLayout(btn_layout)

        self.setLayout(root)

        self._load_tags_into_list(global_tags)

        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.btn_close.clicked.connect(self.close)

    def _load_tags_into_list(self, tags: Iterable[Tag]) -> None:
        self.list_widget.clear()
        attached_names = {t.name for t in self._log.tags}
        for tag in tags:
            item = QListWidgetItem(tag.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if tag.name in attached_names:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.list_widget.addItem(item)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Update the log's tag list when a checkbox is toggled."""
        tag: Tag | None = item.data(Qt.ItemDataRole.UserRole)
        if tag is None:
            return

        if item.checkState() == Qt.CheckState.Checked:
            # Attach if not already present
            if all(existing.name != tag.name for existing in self._log.tags):
                self._log.tags.append(tag)
        else:
            # Detach
            self._log.tags = [t for t in self._log.tags if t.name != tag.name]

    def closeEvent(self, event):  # type: ignore[override]
        from UI.TagManager import state as tag_manager_state

        tag_manager_state.active_tag_manager = None
        super().closeEvent(event)

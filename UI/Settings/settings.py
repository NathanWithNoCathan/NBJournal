from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QScrollArea,
    QWidget,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont
from UI.Homescreen.state import active_homescreen
import DataClasses.settings as settings


def snake_to_title(snake_str: str) -> str:
    """Convert snake_case string to Title Case."""
    components = snake_str.split('_')
    return ' '.join(x.title() for x in components)


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 500)

        self._widgets = {}  # (group_name, field_name) -> widget

        main_layout = QVBoxLayout(self)

        # Scroll area so settings don’t overflow
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Small note about tooltips
        note_label = QLabel("Hover over settings with * for more info.")
        note_label.setStyleSheet("font-size: 8pt")
        note_label.setWordWrap(True)
        scroll_layout.addWidget(note_label)

        # Note about restart-required settings
        restart_note = QLabel("Settings marked with ! require application restart to take effect.")
        restart_note.setStyleSheet("font-size: 8pt")
        restart_note.setWordWrap(True)
        scroll_layout.addWidget(restart_note)

        self._build_groups(scroll_layout)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Buttons row
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        main_layout.addLayout(buttons_layout)

    def _build_groups(self, parent_layout: QVBoxLayout) -> None:
        """Build group boxes and fields from current user_settings."""
        us = settings.user_settings

        # Iterate over top-level groups (appearance, preferences, etc.)
        for group_name in ("log_viewer", "log_editor", "preferences", "ai_settings", "color_palette"):
            group_obj = getattr(us, group_name, None)
            if group_obj is None:
                continue

            group_box = QGroupBox(snake_to_title(group_name))
            form = QFormLayout(group_box)

            # Iterate dataclass fields of the group object
            for field_name, field_def in group_obj.__dataclass_fields__.items():  # type: ignore[attr-defined]
                value = getattr(group_obj, field_name)
                widget = self._make_widget_for_value(field_name, value)
                self._widgets[(group_name, field_name)] = widget

                label_text = snake_to_title(field_name)
                label_widget = QLabel(label_text)

                # Look for optional tooltip in dataclass field metadata
                tooltip = field_def.metadata.get("tooltip") if getattr(field_def, "metadata", None) else None
                if tooltip:
                    # Subtle visual cue that this label has more info.
                    # We avoid changing colors (they're palette-driven) and
                    # just append a small asterisk.
                    label_text += "*"
                    label_widget.setToolTip(tooltip)
                    widget.setToolTip(tooltip)

                # Check if this field requires app restart
                requires_restart = field_def.metadata.get("requires_restart") if getattr(field_def, "metadata", None) else False
                if requires_restart:
                    # Subtle visual cue that this label requires restart.
                    label_text += "!"

                label_widget.setText(f"{label_text}")
                
                # If there's a click action, connect it
                click_action = field_def.metadata.get("click") if getattr(field_def, "metadata", None) else None
                if click_action:
                    def make_handler(action):
                        def handler():
                            action()
                        return handler
                    label_widget.mousePressEvent = lambda event, act=click_action: make_handler(act)()

                form.addRow(label_widget, widget)

            parent_layout.addWidget(group_box)

        parent_layout.addStretch(1)

    def _make_widget_for_value(self, field_name: str, value):
        """Create an appropriate editor widget for a given value."""
        if isinstance(value, bool):
            cb = QCheckBox()
            cb.setChecked(value)
            return cb
        elif isinstance(value, int):
            spin = QSpinBox()
            spin.setRange(1, 10_000)  # generic range; tweak if needed
            spin.setValue(value)
            return spin
        else:
            # Treat everything else as string
            le = QLineEdit()
            le.setText(str(value))
            return le

    def _on_save(self) -> None:
        """Write widget values back into settings and persist."""
        us = settings.user_settings

        for (group_name, field_name), widget in self._widgets.items():
            group_obj = getattr(us, group_name, None)
            if group_obj is None:
                continue

            old_value = getattr(group_obj, field_name)

            if isinstance(widget, QCheckBox):
                new_value = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                new_value = widget.value()
            elif isinstance(widget, QLineEdit):
                # Preserve type: if original was int but editor is line, try cast
                text = widget.text()
                if isinstance(old_value, int):
                    try:
                        new_value = int(text)
                    except ValueError:
                        new_value = old_value
                else:
                    new_value = text
            else:
                new_value = old_value

            setattr(group_obj, field_name, new_value)

        # Persist to disk
        try:
            us.save()
        except ValueError as e:
            QMessageBox.critical(self, "Settings Error", str(e))
            return

        self.accept()
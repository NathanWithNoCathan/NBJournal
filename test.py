import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DemoWindow(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQt6 Demo")
        self.setMinimumSize(600, 400)

        main_layout = QVBoxLayout(self)

        # Top group: basic input controls
        form_group = QGroupBox("Basic Controls")
        form_layout = QGridLayout()

        # Label + line edit
        name_label = QLabel("Name:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter your name")

        # Combo box
        role_label = QLabel("Role:")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Student", "Teacher", "Researcher", "Other"])

        # Checkbox
        self.subscribe_checkbox = QCheckBox("Subscribe to newsletter")

        # Slider
        volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)

        # Layout positions
        form_layout.addWidget(name_label, 0, 0)
        form_layout.addWidget(self.name_edit, 0, 1)
        form_layout.addWidget(role_label, 1, 0)
        form_layout.addWidget(self.role_combo, 1, 1)
        form_layout.addWidget(self.subscribe_checkbox, 2, 0, 1, 2)
        form_layout.addWidget(volume_label, 3, 0)
        form_layout.addWidget(self.volume_slider, 3, 1)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # Middle group: list and text area
        middle_group = QGroupBox("Items & Notes")
        middle_layout = QGridLayout()

        self.item_list = QListWidget()
        self.item_list.addItems(["Apples", "Bananas", "Carrots"])

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Write some notes here...")

        middle_layout.addWidget(QLabel("Items:"), 0, 0)
        middle_layout.addWidget(self.item_list, 1, 0)
        middle_layout.addWidget(QLabel("Notes:"), 0, 1)
        middle_layout.addWidget(self.notes_edit, 1, 1)

        middle_group.setLayout(middle_layout)
        main_layout.addWidget(middle_group)

        # Bottom: button + output label
        self.summary_button = QPushButton("Show Summary")
        self.summary_button.clicked.connect(self.show_summary)

        self.summary_label = QLabel("Ready.")
        self.summary_label.setWordWrap(True)

        main_layout.addWidget(self.summary_button)
        main_layout.addWidget(self.summary_label)

    def show_summary(self) -> None:
        name = self.name_edit.text().strip() or "(no name)"
        role = self.role_combo.currentText()
        subscribed = "yes" if self.subscribe_checkbox.isChecked() else "no"
        volume = self.volume_slider.value()
        current_item = self.item_list.currentItem().text() if self.item_list.currentItem() else "(none)"

        summary = (
            f"Name: {name}; Role: {role}; "
            f"Subscribed: {subscribed}; Volume: {volume}; "
            f"Selected item: {current_item}"
        )

        self.summary_label.setText(summary)


def main() -> None:
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton


class MarkdownDialog(QDialog):
    """Simple dialog to display markdown content to the user."""

    def __init__(self, title: str, markdown_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        # Default size should be large enough to read comfortably.
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        viewer = QTextBrowser(self)
        viewer.setReadOnly(True)
        viewer.setMarkdown(markdown_text)
        layout.addWidget(viewer)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

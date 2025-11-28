from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel


class SettingsWindow(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Settings")
		self.setModal(False)
		self.resize(400, 300)

		layout = QVBoxLayout()
		layout.addWidget(QLabel("Settings placeholder"))
		# TODO: Add settings controls and persist them
		self.setLayout(layout)


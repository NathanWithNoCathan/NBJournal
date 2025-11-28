from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel


class LogsWindow(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Logs")
		self.setModal(False)
		self.resize(600, 400)

		layout = QVBoxLayout()
		layout.addWidget(QLabel("Logs view placeholder"))
		# TODO: Replace with actual logs list/table connected to data classes
		self.setLayout(layout)


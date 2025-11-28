"""Runs the application by starting UI/Homescreen/homescreen.py."""

from UI.Homescreen.homescreen import HomeScreen  # type: ignore[import]

def main():
    """Main entry point for the application."""
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = HomeScreen()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
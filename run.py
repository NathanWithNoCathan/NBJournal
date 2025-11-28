"""Runs the application by starting UI/Homescreen/homescreen.py."""

from UI.Homescreen.homescreen import HomeScreen  # type: ignore[import]
import DataClasses.settings as settings # type: ignore[import]
import DataClasses.log as log  # type: ignore[import]
import DataClasses.tag as tag

def main():
    """Main entry point for the application."""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    print(settings.user_settings)  # Example usage of settings

    app = QApplication(sys.argv)
    window = HomeScreen()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
"""Runs the application by starting UI/Homescreen/homescreen.py."""

from UI.Homescreen.homescreen import HomeScreen  # type: ignore[import]
import DataClasses.settings as settings # type: ignore[import]
import DataClasses.log as log  # type: ignore[import]
import DataClasses.tag as tag
from UI.LogEditor.log_editor import LogEditorWindow  # type: ignore[import]

def main():
    """Main entry point for the application."""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    print(settings.user_settings)  # Example usage of settings

    app = QApplication(sys.argv)
    window = HomeScreen()
    window.show()
    sys.exit(app.exec())

def test_log_editor():
    """Test harness for the Log editor."""
    from PyQt6.QtWidgets import QApplication
    import sys

    # Simple default log – in real usage, pass a real Log instance
    demo_log = log.Log(
        name="New Log",
        description="",
        body="",
        path="demo_log.json",
    )

    app = QApplication(sys.argv)
    window = LogEditorWindow(demo_log)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    test_log_editor()
    # main()
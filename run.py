"""Runs the application by starting UI/Homescreen/homescreen.py."""

from UI.Homescreen.homescreen import HomeScreen  # type: ignore[import]
import DataClasses.settings as settings  # type: ignore[import]
import DataClasses.log as log  # type: ignore[import]
import DataClasses.tag as tag
from UI.LogEditor.log_editor import LogEditorWindow  # type: ignore[import]

def main():
    """Main entry point for the application."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPalette, QColor
    import sys

    app = QApplication(sys.argv)

    # Use Fusion style (works well with custom palettes)
    app.setStyle("Fusion")

    def apply_palette_from_settings(current_settings: settings.Settings) -> None:
        """Apply the color palette from settings to the QApplication."""

        palette_data = current_settings.color_palette

        def c(hex_color: str) -> QColor:
            return QColor(hex_color)

        qt_palette = QPalette()
        qt_palette.setColor(QPalette.ColorRole.Window, c(palette_data.window))
        qt_palette.setColor(QPalette.ColorRole.WindowText, c(palette_data.window_text))
        qt_palette.setColor(QPalette.ColorRole.Base, c(palette_data.base))
        qt_palette.setColor(QPalette.ColorRole.AlternateBase, c(palette_data.alternate_base))
        qt_palette.setColor(QPalette.ColorRole.ToolTipBase, c(palette_data.tooltip_base))
        qt_palette.setColor(QPalette.ColorRole.ToolTipText, c(palette_data.tooltip_text))
        qt_palette.setColor(QPalette.ColorRole.Text, c(palette_data.text))
        qt_palette.setColor(QPalette.ColorRole.Button, c(palette_data.button))
        qt_palette.setColor(QPalette.ColorRole.ButtonText, c(palette_data.button_text))
        qt_palette.setColor(QPalette.ColorRole.BrightText, c(palette_data.bright_text))
        qt_palette.setColor(QPalette.ColorRole.Highlight, c(palette_data.highlight))
        qt_palette.setColor(QPalette.ColorRole.HighlightedText, c(palette_data.highlighted_text))
        qt_palette.setColor(QPalette.ColorRole.Link, c(palette_data.link))

        app.setPalette(qt_palette)

    # Apply initial palette from loaded settings
    apply_palette_from_settings(settings.user_settings)

    # Register hook so future saves update the palette automatically
    settings.user_settings._on_saved = apply_palette_from_settings

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
    # test_log_editor()
    main()
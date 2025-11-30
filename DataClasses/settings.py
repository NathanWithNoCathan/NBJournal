from dataclasses import dataclass, asdict, field
import json
import os
from typing import Callable, Optional, List
from PyQt6.QtGui import QFontDatabase
from UI.Homescreen import state as hs_state
from UI.LogEditor import state as le_state

from PyQt6.QtWidgets import QMessageBox

SETTINGS_FILE = "user_settings.json"

@dataclass
class ArtificialIntelligenceSettings:
    enabled: bool = field(
        default=False,
        metadata={
            "tooltip": "Enable or disable AI features in the application.",
            "requires_restart": True,
        }
    )
    api_key: str = field(
        default="",
        metadata={
            "tooltip": "API key for accessing OpenAI services.",
            "requires_restart": True,
        }
    )
    tag_recommendations: bool = field(default=False, metadata={
        "tooltip": "Enable or disable AI tag recommendations.",
        "requires_restart": False,
    })
    sentiment_analysis: bool = field(default=False, metadata={
        "tooltip": "Enable or disable AI sentiment analysis.",
        "requires_restart": False,
    })
    content_summarization: bool = field(default=False, metadata={
        "tooltip": "Enable or disable AI content summarization.",
        "requires_restart": False,
    })


@dataclass
class ColorPalette:
    """Represents the application's color palette for the UI."""

    window: str = "#353535"
    window_text: str = "#FFFFFF"
    base: str = "#232323"
    alternate_base: str = "#353535"
    tooltip_base: str = "#FFFFFF"
    tooltip_text: str = "#FFFFFF"
    text: str = "#FFFFFF"
    button: str = "#353535"
    button_text: str = "#FFFFFF"
    bright_text: str = "#FF0000"
    highlight: str = "#2A82DA"
    highlighted_text: str = "#000000"
    link: str = "#AAAAAA"

    def validate(self, errors: List[str]) -> None:
        """Validate that all color strings look like hex colors."""

        def _valid_hex(name: str, value: str) -> None:
            if not isinstance(value, str) or not value.startswith("#") or len(value) not in (4, 7):
                errors.append(f"ColorPalette.{name} must be a hex color like '#RRGGBB'. Got: {value!r}")

        _valid_hex("window", self.window)
        _valid_hex("window_text", self.window_text)
        _valid_hex("base", self.base)
        _valid_hex("alternate_base", self.alternate_base)
        _valid_hex("tooltip_base", self.tooltip_base)
        _valid_hex("tooltip_text", self.tooltip_text)
        _valid_hex("text", self.text)
        _valid_hex("button", self.button)
        _valid_hex("button_text", self.button_text)
        _valid_hex("bright_text", self.bright_text)
        _valid_hex("highlight", self.highlight)
        _valid_hex("highlighted_text", self.highlighted_text)
        _valid_hex("link", self.link)

@dataclass
class LogViewerSettings:
    font_size: int = field(
        default=12
    )
    font: str = field(
        default="Arial",
        metadata={"tooltip": "The font family used throughout the application. Click to see available fonts.",
                  "click": lambda: QMessageBox.information(None, "Available Fonts", "List of available fonts: " + ", ".join(QFontDatabase.families()))}
    )

    def validate(self, errors: List[str]) -> None:
        if not isinstance(self.font_size, int) or self.font_size <= 0:
            errors.append(f"AppearanceSettings.font_size must be a positive integer. Got: {self.font_size!r}")
        if not isinstance(self.font, str) or not self.font:
            errors.append("AppearanceSettings.font must be a non-empty string.")

        # Ensure font size is within reasonable bounds
        if self.font_size < 6 or self.font_size > 72:
            errors.append("AppearanceSettings.font_size must be between 6 and 72.")
        
        # Ensure font is a real font name (basic check)
        # This line will cause issues if no GUI environment is available, check app is running first
        if self.font not in QFontDatabase.families():
            errors.append(f"AppearanceSettings.font '{self.font}' is not a recognized font family.")

        # Validation can also be used as an on-save step
        if hs_state.active_homescreen is not None and not errors:
            hs_state.active_homescreen.logs_viewer.preview_body.setFont(QFontDatabase.font(self.font, "", self.font_size))
        if not hs_state.active_homescreen:
            print("Warning: active_homescreen is None during settings validation.")

@dataclass
class LogEditorSettings:
    font_size: int = field(
        default=12
    )
    font: str = field(
        default="Arial",
        metadata={"tooltip": "The font family used throughout the application. Click to see available fonts.",
                  "click": lambda: QMessageBox.information(None, "Available Fonts", "List of available fonts: " + ", ".join(QFontDatabase.families()))}
    )
    default_view_mode: int = field(
        default=0,
        metadata={"tooltip": "The default view mode for the log editor. 0=Title+Description+Body, 1=Title+Body, 2=Body Only."}
    )

    def validate(self, errors: List[str]) -> None:
        if not isinstance(self.font_size, int) or self.font_size <= 0:
            errors.append(f"AppearanceSettings.font_size must be a positive integer. Got: {self.font_size!r}")
        if not isinstance(self.font, str) or not self.font:
            errors.append("AppearanceSettings.font must be a non-empty string.")

        # Ensure font size is within reasonable bounds
        if self.font_size < 6 or self.font_size > 72:
            errors.append("AppearanceSettings.font_size must be between 6 and 72.")
        
        # Ensure font is a real font name (basic check)
        # This line will cause issues if no GUI environment is available, check app is running first
        if self.font not in QFontDatabase.families():
            errors.append(f"AppearanceSettings.font '{self.font}' is not a recognized font family.")

        if not isinstance(self.default_view_mode, int) or self.default_view_mode not in (0, 1, 2):
            errors.append("LogEditorSettings.default_view_mode must be 0, 1, or 2.")

        # Validation can also be used as an on-save step
        if le_state.active_log_editor is not None and not errors:
            le_state.active_log_editor.title_edit.setFont(QFontDatabase.font(self.font, "", self.font_size))
            le_state.active_log_editor.body_edit.setFont(QFontDatabase.font(self.font, "", self.font_size))
        if not le_state.active_log_editor:
            print("Warning: active_log_editor is None during settings validation.")
@dataclass
class UserPreferences:
    username: str = "default_user"
    notifications_enabled: bool = True
    autosave_interval: int = field(
        default=30,  # in seconds
        metadata={
            "tooltip": "Interval in seconds for autosaving logs.",
            "requires_restart": True,
        },
    )

    def toggle_notifications(self) -> None:
        self.notifications_enabled = not self.notifications_enabled

    def validate(self, errors: List[str]) -> None:
        if not isinstance(self.username, str) or not self.username:
            errors.append("UserPreferences.username must be a non-empty string.")
        if not isinstance(self.autosave_interval, int) or self.autosave_interval <= 0:
            errors.append(
                f"UserPreferences.autosave_interval must be a positive integer (seconds). Got: {self.autosave_interval!r}"
            )


@dataclass
class Settings:
    log_viewer: LogViewerSettings = field(default_factory=LogViewerSettings)
    log_editor: LogEditorSettings = field(default_factory=LogEditorSettings)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    ai_settings: ArtificialIntelligenceSettings = field(default_factory=ArtificialIntelligenceSettings)
    color_palette: ColorPalette = field(default_factory=ColorPalette)

    # Optional hook that the UI layer can set to be notified
    # whenever settings are saved, so it can update the app palette.
    _on_saved: Optional[Callable[["Settings"], None]] = field(default=None, repr=False, compare=False)

    def save(self, path: str | None = None) -> None:
        # Validate settings before writing to disk or updating the UI.
        errors: List[str] = []

        # Validate individual groups if they implement a validate() method.
        if hasattr(self.log_viewer, "validate"):
            self.log_viewer.validate(errors)
        if hasattr(self.preferences, "validate"):
            self.preferences.validate(errors)
        if hasattr(self.ai_settings, "validate"):
            # Currently no validate() on AI settings, but call if added later.
            self.ai_settings.validate(errors)  # type: ignore[attr-defined]
        if hasattr(self.color_palette, "validate"):
            self.color_palette.validate(errors)
        if hasattr(self.log_editor, "validate"):
            self.log_editor.validate(errors)

        if errors:
            # Raise an exception to signal that saving failed.
            raise ValueError("Settings validation failed:\n" + "\n".join(errors))

        file_path = path or SETTINGS_FILE
        # Exclude non-serializable fields like callbacks from JSON payload.
        serializable = asdict(self)
        serializable.pop("_on_saved", None)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=4)

        # Notify UI layer (e.g., to update global QApplication palette)
        if self._on_saved is not None:
            try:
                self._on_saved(self)
            except Exception:
                # Avoid crashing on UI hook errors
                pass


def load_settings(path: str | None = None) -> Settings:
    file_path = path or SETTINGS_FILE

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            log_editor_data = data.get("log_editor", {})
            prefs_data = data.get("preferences", {})
            ai_data = data.get("ai_settings", {})
            palette_data = data.get("color_palette", {})
            log_viewer_data = data.get("log_viewer", {})
            log_viewer = LogViewerSettings(**log_viewer_data)
            preferences = UserPreferences(**prefs_data)
            ai_settings = ArtificialIntelligenceSettings(**ai_data)
            color_palette = ColorPalette(**palette_data)
            log_editor = LogEditorSettings(**log_editor_data)
            return Settings(log_viewer=log_viewer, preferences=preferences, ai_settings=ai_settings, color_palette=color_palette, log_editor=log_editor)
        except Exception:
            # If file is corrupt or incompatible, fall back to defaults.
            pass

    return Settings()


# Global settings instance, always loaded from the same file
user_settings: Settings = load_settings()
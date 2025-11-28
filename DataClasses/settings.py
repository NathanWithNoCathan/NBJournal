from dataclasses import dataclass, asdict, field
import json
import os
from typing import Callable, Optional, List

SETTINGS_FILE = "user_settings.json"


@dataclass
class ArtificialIntelligenceSettings:
    enabled: bool = False
    api_key: str = ""
    tag_recommendations: bool = True
    sentiment_analysis: bool = False
    content_summarization: bool = False


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


@dataclass
class AppearanceSettings:
    font_size: int = 12
    font: str = "Arial"

    def validate(self, errors: List[str]) -> None:
        if not isinstance(self.font_size, int) or self.font_size <= 0:
            errors.append(f"AppearanceSettings.font_size must be a positive integer. Got: {self.font_size!r}")
        if not isinstance(self.font, str) or not self.font:
            errors.append("AppearanceSettings.font must be a non-empty string.")

@dataclass
class UserPreferences:
    username: str = "default_user"
    notifications_enabled: bool = True
    autosave_interval: int = 10  # in minutes

    def toggle_notifications(self) -> None:
        self.notifications_enabled = not self.notifications_enabled

    def validate(self, errors: List[str]) -> None:
        if not isinstance(self.username, str) or not self.username:
            errors.append("UserPreferences.username must be a non-empty string.")
        if not isinstance(self.autosave_interval, int) or self.autosave_interval <= 0:
            errors.append(
                f"UserPreferences.autosave_interval must be a positive integer (minutes). Got: {self.autosave_interval!r}"
            )


@dataclass
class Settings:
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
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
        if hasattr(self.appearance, "validate"):
            self.appearance.validate(errors)
        if hasattr(self.preferences, "validate"):
            self.preferences.validate(errors)
        if hasattr(self.ai_settings, "validate"):
            # Currently no validate() on AI settings, but call if added later.
            self.ai_settings.validate(errors)  # type: ignore[attr-defined]
        if hasattr(self.color_palette, "validate"):
            self.color_palette.validate(errors)

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

            appearance_data = data.get("appearance", {})
            prefs_data = data.get("preferences", {})
            ai_data = data.get("ai_settings", {})
            palette_data = data.get("color_palette", {})
            appearance = AppearanceSettings(**appearance_data)
            preferences = UserPreferences(**prefs_data)
            ai_settings = ArtificialIntelligenceSettings(**ai_data)
            color_palette = ColorPalette(**palette_data)
            return Settings(appearance=appearance, preferences=preferences, ai_settings=ai_settings, color_palette=color_palette)
        except Exception:
            # If file is corrupt or incompatible, fall back to defaults.
            pass

    return Settings()


# Global settings instance, always loaded from the same file
user_settings: Settings = load_settings()
user_settings.save()  # Ensure settings file exists / migrates format
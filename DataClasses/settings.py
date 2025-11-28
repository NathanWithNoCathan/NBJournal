from dataclasses import dataclass, asdict, field
import json
import os

SETTINGS_FILE = "user_settings.json"

@dataclass
class ArtificialIntelligenceSettings:
    enabled: bool = False
    api_key: str = ""
    tag_recommendations: bool = True
    sentiment_analysis: bool = False
    content_summarization: bool = False

@dataclass
class AppearanceSettings:
    theme: str = "light"
    font_size: int = 12
    font: str = "Arial"

@dataclass
class UserPreferences:
    username: str = "default_user"
    notifications_enabled: bool = True
    autosave_interval: int = 10  # in minutes

    def toggle_notifications(self) -> None:
        self.notifications_enabled = not self.notifications_enabled


@dataclass
class Settings:
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    ai_settings: ArtificialIntelligenceSettings = field(default_factory=ArtificialIntelligenceSettings)

    def save(self, path: str | None = None) -> None:
        file_path = path or SETTINGS_FILE
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)


def load_settings(path: str | None = None) -> Settings:
    file_path = path or SETTINGS_FILE

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            appearance_data = data.get("appearance", {})
            prefs_data = data.get("preferences", {})
            ai_data = data.get("ai_settings", {})
            appearance = AppearanceSettings(**appearance_data)
            preferences = UserPreferences(**prefs_data)
            ai_settings = ArtificialIntelligenceSettings(**ai_data)
            return Settings(appearance=appearance, preferences=preferences, ai_settings=ai_settings)

        except Exception:
            # If file is corrupt or incompatible, fall back to defaults.
            pass

    return Settings()


# Global settings instance, always loaded from the same file
user_settings: Settings = load_settings()
user_settings.save()  # Ensure settings file exists / migrates format
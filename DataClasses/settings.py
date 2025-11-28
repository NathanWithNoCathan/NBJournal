from dataclasses import dataclass, asdict
import json
import os

SETTINGS_FILE = "user_settings.json"

@dataclass
class Settings:
    # Example settings fields
    theme: str = "light"
    autosave_interval: int = 10  # in minutes
    username: str = None
    notifications_enabled: bool = True
    font_size: int = 12
    font: str = "Arial"

    def toggle_notifications(self) -> None:
        """Toggle the notifications setting."""
        self.notifications_enabled = not self.notifications_enabled

    def save(self, path: str | None = None) -> None:
        """Persist current settings to disk as JSON."""
        file_path = path or SETTINGS_FILE
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)


def load_settings(path: str | None = None) -> Settings:
    """Load settings from disk, falling back to defaults if missing/invalid."""
    file_path = path or SETTINGS_FILE

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings(**data)
        except Exception:
            # If file is corrupt or incompatible, fall back to defaults.
            pass

    return Settings()


# Global settings instance, always loaded from the same file
user_settings: Settings = load_settings()
user_settings.save()  # Ensure settings file exists
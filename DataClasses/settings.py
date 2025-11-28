from dataclasses import dataclass

@dataclass
class Settings:
    # Example settings fields
    theme: str = "light"
    autosave_interval: int = 10  # in minutes
    username: str = "default_user"
    notifications_enabled: bool = True
    font_size: int = 12
    font: str = "Arial"
    
    
    def toggle_notifications(self) -> None:
        """Toggle the notifications setting."""
        self.notifications_enabled = not self.notifications_enabled

# Global settings instance
user_settings: Settings = Settings()

# Load if existing
def load_settings() -> Settings:
    """Load settings from a local json file or return default settings."""
    import json
    import os

    settings_file = "user_settings.json"
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            data = json.load(f)
            return Settings(**data)
    return Settings()
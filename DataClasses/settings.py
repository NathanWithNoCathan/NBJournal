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
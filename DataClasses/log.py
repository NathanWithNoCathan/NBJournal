from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from DataClasses.tag import Tag as tag
import json
import os


LOGS_FOLDER = "logs"

def _datetime_to_iso(dt: datetime) -> str:
    return dt.isoformat()
def _datetime_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)

@dataclass
class Log:
    # Basic log content
    name: str
    description: str
    body: str

    # Path under which the log is stored (within LOGS_FOLDER)
    path: str

    # Optional thumbnail (e.g., file path or URL)
    thumbnail: Optional[str] = None

    # Tagging system
    tags: list[tag] = field(default_factory=list)

    # Metadata (stored as ISO strings for JSON)
    created_at: datetime = field(default_factory=datetime.utcnow)
    revised_at: datetime = field(default_factory=datetime.utcnow)
    revision_history: list[datetime] = field(default_factory=list)

    # Log format version (not content revision number)
    log_format_version: int = 1

    def add_revision(self) -> None:
        """Record a new revision timestamp and update last revised time."""
        now = datetime.utcnow()
        self.revision_history.append(now)
        self.revised_at = now

    def to_json_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""
        data = asdict(self)
        data["created_at"] = _datetime_to_iso(self.created_at)
        data["revised_at"] = _datetime_to_iso(self.revised_at)
        data["revision_history"] = [_datetime_to_iso(d) for d in self.revision_history]
        # Ensure tags are JSON-serializable (assuming Tag is a dataclass)
        data["tags"] = [asdict(t) for t in self.tags]
        return data

    @classmethod
    def from_json_dict(cls, data: dict) -> "Log":
        """Create a Log instance from a JSON dict."""
        # Convert datetimes back
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = _datetime_from_iso(data["created_at"])
        if "revised_at" in data and isinstance(data["revised_at"], str):
            data["revised_at"] = _datetime_from_iso(data["revised_at"])
        if "revision_history" in data:
            data["revision_history"] = [
                _datetime_from_iso(d) if isinstance(d, str) else d
                for d in data.get("revision_history", [])
            ]

        # Rebuild Tag objects if tags are dicts
        if "tags" in data:
            rebuilt_tags: list[tag] = []
            for t in data["tags"]:
                if isinstance(t, dict):
                    rebuilt_tags.append(tag(**t))
                else:
                    rebuilt_tags.append(t)
            data["tags"] = rebuilt_tags

        return cls(**data)

    def save(self) -> None:
        """Persist the log to disk as JSON."""
        if not os.path.exists(LOGS_FOLDER):
            os.makedirs(LOGS_FOLDER)

        global logs
        if self not in logs:
            logs.append(self)

        file_path = os.path.join(LOGS_FOLDER, self.path)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_json_dict(), f, indent=4)

    def delete(self) -> None:
        """Delete the log file from disk and remove from global logs list."""
        global logs
        if self in logs:
            logs.remove(self)

        file_path = os.path.join(LOGS_FOLDER, self.path)
        if os.path.exists(file_path):
            os.remove(file_path)


def load_logs() -> list[Log]:
    """Load existing logs from the logs folder."""
    if not os.path.exists(LOGS_FOLDER):
        os.makedirs(LOGS_FOLDER)
        return []

    log_files = [
        f for f in os.listdir(LOGS_FOLDER)
        if os.path.isfile(os.path.join(LOGS_FOLDER, f))
    ]

    log_list: list[Log] = []
    for file in log_files:
        try:
            with open(os.path.join(LOGS_FOLDER, file), "r", encoding="utf-8") as f:
                data = json.load(f)
            log_list.append(Log.from_json_dict(data))
        except Exception:
            print(f"Failed to read log file: {file}")

    return log_list


logs: list[Log] = load_logs() # Global list of loaded logs
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from DataClasses.tag import Tag as tag
import json
import os
from Helpers import encryptor


LOGS_FOLDER = "logs"

def _datetime_to_iso(dt: datetime) -> str:
    return dt.isoformat()
def _datetime_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


_MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024 * 1024  # 5 GiB

@dataclass
class Log:
    # Basic log content
    name: str
    description: str
    body: str

    # Path under which the log is stored (within LOGS_FOLDER)
    path: str

    # Tagging system
    tags: list[tag] = field(default_factory=list)

    # Metadata (stored as ISO strings for JSON)
    created_at: datetime = field(default_factory=datetime.utcnow)
    revised_at: datetime = field(default_factory=datetime.utcnow)
    revision_history: list[datetime] = field(default_factory=list)

    # Log format version (not content revision number)
    log_format_version: int = 1

    # Encrypted payload (optional). When set, it contains the encrypted
    # form of the original description/body so that those fields can be
    # replaced with a neutral placeholder while the title remains
    # visible.
    encrypted_payload: Optional[str] = None

    

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

    # --- Encryption helpers ---

    def is_encrypted(self) -> bool:
        """Return True if this log currently has encrypted content."""
        return bool(self.encrypted_payload)

    def encrypt_with_password(self, password: str) -> None:
        """Encrypt the description/body with ``password`` and save.

        The title/name remains visible. After encryption, the
        ``description`` and ``body`` fields are replaced with a neutral
        placeholder message while the encrypted bytes are stored in
        ``encrypted_payload`` (base64-encoded).
        """

        # If already encrypted, do nothing.
        if self.is_encrypted():
            return

        payload = {
            "description": self.description,
            "body": self.body,
            "attachments": {},
        }
        plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        encrypted_b64 = encryptor.encrypt_to_base64(password, plaintext)
        self.encrypted_payload = encrypted_b64

        placeholder = "This log has been encrypted. Decrypt this log to view its contents"
        self.description = placeholder
        self.body = placeholder

        # Persist changes immediately.
        self.save()

    def can_decrypt_with_password(self, password: str) -> bool:
        """Return True if ``password`` matches the encrypted payload.

        If the log is not encrypted, this returns False.
        """

        if not self.encrypted_payload:
            return False

        try:
            blob = self.encrypted_payload.encode("ascii")
        except Exception:
            return False

        try:
            # ``encryptor`` expects base64 string for the helper below,
            # so we just pass through the stored payload.
            return encryptor.is_password_correct(
                password,
                encryptor.base64.b64decode(self.encrypted_payload.encode("ascii")),  # type: ignore[attr-defined]
            )
        except Exception:
            return False

    def decrypt_with_password(self, password: str) -> None:
        """Decrypt the log with ``password`` and restore its contents.

        If the password is incorrect or no encrypted payload is
        present, a :class:`ValueError` is raised. On success, the
        original description and body are restored and the
        ``encrypted_payload`` field is cleared. The log is then saved
        to disk.
        """

        if not self.encrypted_payload:
            raise ValueError("Log is not encrypted.")

        try:
            plaintext = encryptor.decrypt_from_base64(password, self.encrypted_payload)
        except ValueError as exc:
            # Wrong password or tampered data
            raise ValueError("Incorrect password or corrupted encrypted log data.") from exc

        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Failed to decode decrypted log payload.") from exc

        self.description = payload.get("description", "")
        self.body = payload.get("body", "")

        # Attachments are no longer supported; ignore any attachment data
        self.encrypted_payload = None

        # Persist restored content.
        self.save()

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

    # --- Sentiment analysis helpers ---

    def _analysis_file_path(self) -> str:
        """Return the expected path to this log's sentiment analysis JSON.

        This mirrors the convention used by the sentiment analysis
        feature: same directory and filename as the log, but with
        "_analysis" inserted before the extension.
        """

        base_log_path = os.path.join(LOGS_FOLDER, self.path)
        root, ext = os.path.splitext(base_log_path)
        if not ext:
            ext = ".json"
        return f"{root}_analysis{ext}"

    def has_sentiment_analysis(self) -> bool:
        """Return True if a sentiment analysis JSON file exists for this log."""

        return os.path.exists(self._analysis_file_path())

    def load_sentiment_analysis(self) -> Optional[dict]:
        """Load this log's sentiment analysis JSON if available.

        Returns the parsed JSON object, or None if no analysis file is
        present or if it cannot be read/parsed.
        """

        path = self._analysis_file_path()
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print(f"Failed to read sentiment analysis file: {os.path.basename(path)}")
            return None
        
    def delete_sentiment_analysis(self) -> None:
        """Delete this log's sentiment analysis JSON file, if it exists."""
        path = self._analysis_file_path()
        if os.path.exists(path):
            os.remove(path)


def load_logs() -> list[Log]:
    """Load existing logs from the logs folder."""
    if not os.path.exists(LOGS_FOLDER):
        os.makedirs(LOGS_FOLDER)
        return []

    log_files = [
        f for f in os.listdir(LOGS_FOLDER)
        if os.path.isfile(os.path.join(LOGS_FOLDER, f))
    ]

    # Analysis files are stored alongside logs; skip them
    log_files = [f for f in log_files if not f.endswith("_analysis.json")]

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
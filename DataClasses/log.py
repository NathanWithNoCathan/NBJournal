from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from tag import Tag as tag

@dataclass
class Log:
    # Basic log content
    name: str
    description: str
    body: str

    # Optional thumbnail (e.g., file path or URL)
    thumbnail: Optional[str] = None

    # Tagging system (list of tag names or IDs)
    tags: list[tag] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    revised_at: datetime = field(default_factory=datetime.utcnow)
    revision_history: list[datetime] = field(default_factory=list)

    # Log format version (not content revision number)
    log_format_version: int = 1

    def add_revision(self) -> None:
        """Record a new revision timestamp and update last revised time.

        Does not change `log_format_version`; that tracks schema version.
        """
        now = datetime.utcnow()
        self.revision_history.append(now)
        self.revised_at = now
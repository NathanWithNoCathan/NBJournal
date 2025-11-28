from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Set, Iterable

@dataclass(frozen=True)
class Tag:
    name: str
    description: str = ""

    def __hash__(self) -> int:
        return hash(self.name.lower())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return False
        return self.name.lower() == other.name.lower()


@dataclass
class Revision:
    version: float
    timestamp: datetime
    name: str
    description: str
    body: str

    def snapshot(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "description": self.description,
            "body": self.body,
        }


@dataclass
class Log:
    name: str
    description: str
    body: str
    thumbnail: Optional[Path] = None
    tags: Set[Tag] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    revisions: List[Revision] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.revisions:
            self.revisions.append(
                Revision(
                    version=self.version,
                    timestamp=self.created_at,
                    name=self.name,
                    description=self.description,
                    body=self.body,
                )
            )

    def add_tags(self, new_tags: Iterable[Tag]) -> None:
        self.tags.update(new_tags)

    def remove_tag(self, tag: Tag) -> None:
        self.tags.discard(tag)

    def update(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        body: Optional[str] = None,
        thumbnail: Optional[Path] = None,
        bump_version: bool = True,
    ) -> None:
        changed = False
        if name is not None and name != self.name:
            self.name = name
            changed = True
        if description is not None and description != self.description:
            self.description = description
            changed = True
        if body is not None and body != self.body:
            self.body = body
            changed = True
        if thumbnail is not None and thumbnail != self.thumbnail:
            self.thumbnail = thumbnail
        if changed and bump_version:
            self.version += 1
            self.revisions.append(
                Revision(
                    version=self.version,
                    timestamp=datetime.now(timezone.utc),
                    name=self.name,
                    description=self.description,
                    body=self.body,
                )
            )

    def revert_to_version(self, target_version: int) -> bool:
        for rev in reversed(self.revisions):
            if rev.version == target_version:
                self.name = rev.name
                self.description = rev.description
                self.body = rev.body
                self.version = rev.version
                # Add a new revision marking the revert action
                self.revisions.append(
                    Revision(
                        version=self.version,
                        timestamp=datetime.now(timezone.utc),
                        name=self.name,
                        description=self.description,
                        body=self.body,
                    )
                )
                return True
        return False

    def latest_revision(self) -> Revision:
        return self.revisions[-1]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "body": self.body,
            "thumbnail": str(self.thumbnail) if self.thumbnail else None,
            "tags": [t.name for t in self.tags],
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "revisions": [r.snapshot() for r in self.revisions],
        }
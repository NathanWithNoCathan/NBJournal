from dataclasses import dataclass, asdict
from typing import Any
import json
import os


TAGS_FOLDER = "tags"

@dataclass(slots=True)
class Tag:
    """Basic tag dataclass."""

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        # Normalize and validate
        n = self.name.strip()
        d = self.description.strip()
        if not n:
            raise ValueError("Tag.name cannot be empty")
        object.__setattr__(self, "name", n)
        object.__setattr__(self, "description", d)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description}

    def save(self) -> None:
        """Persist this tag to disk as JSON under TAGS_FOLDER."""
        if not os.path.exists(TAGS_FOLDER):
            os.makedirs(TAGS_FOLDER)

        # Use the normalized name as filename
        filename = f"{self.name}.json"
        filepath = os.path.join(TAGS_FOLDER, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)


def load_tags() -> list[Tag]:
    """Load all tags from disk."""
    tags: list[Tag] = []
    if not os.path.exists(TAGS_FOLDER):
        return tags

    for filename in os.listdir(TAGS_FOLDER):
        if filename.endswith(".json"):
            filepath = os.path.join(TAGS_FOLDER, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tag_obj = Tag(**data)
                tags.append(tag_obj)
            except Exception:
                # Skip invalid/corrupt tag files
                continue

    return tags


tags = load_tags()  # Global list of tags
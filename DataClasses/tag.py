from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class Tag:
    """
    Basic tag dataclass.

    Fields:
      - name: Required tag name.
      - description: Optional description (defaults to empty string).
    """
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
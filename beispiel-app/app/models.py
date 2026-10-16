from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Task:
    id: int
    title: str
    done: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ValidationError(ValueError):
    """Raised when client input does not satisfy the Task invariants."""


MAX_TITLE_LENGTH = 200


def validate_title(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ValidationError("title must be a string")
    title = raw.strip()
    if not title:
        raise ValidationError("title must not be empty")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(f"title must be at most {MAX_TITLE_LENGTH} characters")
    return title


def validate_done(raw: Any) -> bool:
    if not isinstance(raw, bool):
        raise ValidationError("done must be a boolean")
    return raw

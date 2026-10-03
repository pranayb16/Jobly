from __future__ import annotations

from typing import Any


def change_between(current: int, previous: int | None) -> dict[str, Any] | None:
    if previous is None:
        return None
    percent = None if previous == 0 else round(((current - previous) / previous) * 100, 2)
    return {"absolute": current - previous, "percent": percent}

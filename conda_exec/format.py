"""Formatting utilities for CLI output."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


def format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    value = float(size_bytes)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
    raise AssertionError("unreachable")


def format_age(dt: datetime | None) -> str:
    """Format a datetime as a human-readable age string."""
    from datetime import datetime, timezone

    if dt is None:
        return "unknown"

    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt

    if delta.days > 1:
        return f"{delta.days} days ago"
    if delta.days == 1:
        return "1 day ago"
    hours = delta.seconds // 3600
    if hours > 1:
        return f"{hours} hours ago"
    if hours == 1:
        return "1 hour ago"
    minutes = delta.seconds // 60
    if minutes > 1:
        return f"{minutes} minutes ago"
    if minutes == 1:
        return "1 minute ago"
    return "just now"

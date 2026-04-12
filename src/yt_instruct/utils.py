"""Utility helpers: slugify, path helpers, metadata formatting."""

import re
import unicodedata
from pathlib import Path


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to a filesystem-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text[:max_length]


def output_path(output_dir: Path, title: str, suffix: str = "_instructions.md") -> Path:
    """Return the output file path for a given video title."""
    slug = slugify(title)
    return output_dir / f"{slug}{suffix}"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if seconds is None:
        return "unknown"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

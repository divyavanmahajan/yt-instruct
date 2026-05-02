"""yt-instruct: Convert YouTube videos into structured markdown instruction documents."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("yt-instruct")
except PackageNotFoundError:
    __version__ = "unknown"

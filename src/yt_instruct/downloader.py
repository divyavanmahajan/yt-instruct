"""Audio downloader using yt-dlp."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL


@dataclass
class VideoInfo:
    title: str
    channel: str
    url: str
    duration: int | None
    audio_path: Path | None
    description: str = ""


def _check_ffmpeg() -> None:
    """Raise a clear error if ffmpeg is not available."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is required but not found. "
            "Install it with: brew install ffmpeg  (macOS) or apt install ffmpeg  (Linux)"
        )


def fetch_info(url: str) -> "VideoInfo":
    """Fetch video metadata without downloading audio (lightweight network call)."""
    opts = {"quiet": True, "no_warnings": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return VideoInfo(
        title=info.get("title", url),
        channel=info.get("uploader") or info.get("channel", "Unknown"),
        url=url,
        duration=info.get("duration"),
        audio_path=None,
        description=info.get("description") or "",
    )


def resolve_urls(url: str) -> list[str]:
    """Expand a URL to a list of video URLs. Handles playlists and single videos."""
    opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        urls = []
        for entry in entries:
            if entry and entry.get("url"):
                urls.append(entry["url"])
            elif entry and entry.get("id"):
                urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
        return urls

    return [url]


def download_audio(url: str, tmp_dir: Path, audio_format: str = "mp3") -> VideoInfo:
    """Download audio from a YouTube URL. Returns VideoInfo with audio_path set."""
    _check_ffmpeg()

    opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
            }
        ],
        "outtmpl": str(tmp_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info["id"]
    audio_path = tmp_dir / f"{video_id}.{audio_format}"

    if not audio_path.exists():
        # yt-dlp may have used a different extension
        candidates = list(tmp_dir.glob(f"{video_id}.*"))
        if not candidates:
            raise FileNotFoundError(f"Downloaded audio not found in {tmp_dir}")
        audio_path = candidates[0]

    return VideoInfo(
        title=info.get("title", video_id),
        channel=info.get("uploader") or info.get("channel", "Unknown"),
        url=url,
        duration=info.get("duration"),
        audio_path=audio_path,
        description=info.get("description") or "",
    )

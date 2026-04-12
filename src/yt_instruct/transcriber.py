"""Audio transcription using Mistral's voxtral API."""

import os
from pathlib import Path

from mistralai.client import Mistral


def transcribe(audio_path: Path, model: str = "voxtral-mini-latest") -> str:
    """Transcribe audio file using Mistral. Returns transcript as plain text."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY environment variable is not set. "
            "Get your key at https://console.mistral.ai/"
        )

    client = Mistral(api_key=api_key)

    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.complete(
            model=model,
            file={"file_name": audio_path.name, "content": f},
        )

    transcript = result.text
    if not transcript or not transcript.strip():
        raise ValueError(f"Empty transcript returned for {audio_path.name}")

    return transcript.strip()

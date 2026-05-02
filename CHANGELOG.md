# Changelog

## [1.1.0] - 2026-05-02

### Changed
- Enable speaker diarization and segment-level timestamps in Mistral transcription (`diarize=True`, `timestamp_granularities=["segment"]`)

## [1.0.0] - Initial release

- YouTube to markdown pipeline: download (yt-dlp) → transcribe (Mistral voxtral) → generate (Anthropic/llm/NVIDIA)

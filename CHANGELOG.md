# Changelog

## [1.2.0] - 2026-05-02

### Added
- `--no-generate` flag: stop after transcription and skip the LLM generation step. The transcript is always saved to `<output-dir>/<slug>_transcript.txt`. Useful when you only need the raw transcript.

## [1.1.0] - 2026-05-02

### Changed
- Enable speaker diarization and segment-level timestamps in Mistral transcription (`diarize=True`, `timestamp_granularities=["segment"]`)

## [1.0.0] - Initial release

- YouTube to markdown pipeline: download (yt-dlp) → transcribe (Mistral voxtral) → generate (Anthropic/llm/NVIDIA)

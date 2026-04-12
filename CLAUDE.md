# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

`yt-instruct` is a Python CLI tool that converts YouTube videos into structured markdown instruction documents. The pipeline is: URL → audio download (yt-dlp) → transcription (Mistral voxtral) → LLM document generation (Anthropic/llm/NVIDIA).

## Development Setup

```bash
pip install -e .
```

**Runtime requirements:**
- `ffmpeg` installed and on PATH
- `MISTRAL_API_KEY` — always required for transcription
- `ANTHROPIC_API_KEY` — required for default backend
- `NVIDIA_API_KEY` — required only for `--backend nvidia`

## Running the Tool

```bash
yt-instruct <URL>                                                   # single video
yt-instruct url1 url2 --output-dir ./docs                          # multiple URLs
yt-instruct <URL> --content-type ib --backend llm                  # specific type/backend
yt-instruct --transcript-file transcript.txt --title "Name"        # skip download/transcription
cat urls.txt | yt-instruct --url-file /dev/stdin                   # from file
```

Key options: `--keep` (keep audio/transcript), `--merge` (combine into one doc), `--content-type [tutorial|lecture|ib|auto]`, `--backend [anthropic|llm|nvidia]`, `--model TEXT`, `--prompt-file PATH`, `--language LANG`.

## Running Tests

```bash
pytest
```

The `tests/` directory is currently empty — no tests exist yet.

## Architecture

Four modules with clean separation:

- **`cli.py`** — Click CLI, orchestration, batch processing, error recovery, temp dir lifecycle
- **`downloader.py`** — yt-dlp wrapper; produces `VideoInfo` dataclass (title, channel, url, duration, audio_path)
- **`transcriber.py`** — Mistral voxtral API call; returns plain text transcript
- **`generator.py`** — Multi-backend LLM generation; three backends (`generate_anthropic`, `generate_llm`, `generate_nvidia`), auto content-type classification, template variable substitution

## Prompt Templates

Located in `src/yt_instruct/prompts/`. Each template accepts `{title}`, `{channel}`, `{content_type}`, `{duration}` variables:

- `default.md` — generic instructions
- `tutorial.md` — hands-on how-to
- `lecture.md` — tech talks / academic
- `ib.md` — IB student revision notes

`--content-type auto` triggers LLM classification to pick the right template. Custom prompts can be supplied via `--prompt-file`.

## Package Entry Point

`pyproject.toml` defines `yt-instruct = "yt_instruct.cli:cli"`. The package is under `src/yt_instruct/` with prompt templates included as package data.

# yt-instruct — Implementation Plan

## Phase 1: Scaffold ✅
- Directory structure: `src/yt_instruct/`, `docs/`, `prompts/`
- `pyproject.toml` with all dependencies and `yt-instruct` entry point
- `__init__.py`, `utils.py`
- `cli.py` skeleton with all Click flags

## Phase 2: Downloader ✅
- `downloader.py` — yt-dlp audio extraction
- `VideoInfo` dataclass
- ffmpeg presence check with clear error message

## Phase 3: Transcriber ✅
- `transcriber.py` — Mistral voxtral-mini-latest API
- API key validation
- Empty transcript guard

## Phase 4: Generator + Prompts ✅
- Four prompt templates: `default.md`, `tutorial.md`, `lecture.md`, `ib.md`
- `generator.py` — Anthropic SDK and llm backends
- Auto content-type detection (LLM classifies on title + channel)
- `--prompt-file` override support

## Phase 5: Integration ✅
- CLI wired end-to-end: download → transcribe → generate → write → cleanup
- `--merge` mode
- `--keep` mode (retains audio + transcript in temp dir)
- Per-URL error handling (skip failing URLs, continue batch)

## Verification

```bash
# Install and run with uvx (from repo root)
uvx --from ./yt-instruct yt-instruct https://www.youtube.com/watch?v=<id>

# Or editable install
pip install -e ./yt-instruct
yt-instruct <url> --keep --output-dir ./output

# Custom prompt
yt-instruct <url> --prompt-file my_prompt.md

# llm backend
yt-instruct <url> --backend llm --model claude-sonnet-4-6

# Batch + merge
yt-instruct url1 url2 url3 --merge --output-dir ./output

# URL file
yt-instruct --url-file urls.txt --content-type ib
```

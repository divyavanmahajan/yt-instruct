# yt-instruct

Convert YouTube videos into structured markdown instruction documents.

Downloads audio via yt-dlp, transcribes with Mistral's voxtral API, then generates a clean how-to document using Claude.

## Quick Start

```bash
# Run with uvx (no install needed)
uvx --from . yt-instruct https://www.youtube.com/watch?v=<id>

# Or install
pip install -e .
yt-instruct https://www.youtube.com/watch?v=<id>
```

## Requirements

- `ffmpeg` — `brew install ffmpeg` or `apt install ffmpeg`
- `MISTRAL_API_KEY` — [console.mistral.ai](https://console.mistral.ai/)
- `ANTHROPIC_API_KEY` — for default backend
- `NVIDIA_API_KEY` — only for `--backend nvidia`

## Usage

```
yt-instruct [OPTIONS] URL [URL...]
yt-instruct [OPTIONS] --url-file urls.txt
yt-instruct [OPTIONS] --transcript-file transcript.txt --title "Name"
yt-instruct [OPTIONS] --audio-file recording.mp3 --title "Name"

Options:
  --output-dir PATH              Output directory [default: .]
  --keep                         Keep intermediate audio + transcript files
  --merge                        Merge all videos into one document
  --resume                       Skip already-generated outputs; reuse cached transcripts
  --no-generate                  Stop after transcription; skip LLM generation
  --content-type [tutorial|lecture|ib|auto]
                                 Prompt style [default: auto]
  --backend [anthropic|llm|nvidia]
                                 LLM backend [default: anthropic]
  --model TEXT                   Model name [default: claude-sonnet-4-6]
  --prompt-file PATH             Custom system prompt (overrides built-in)
  --language LANG                Output language (e.g. 'French'). Defaults to English.
  --transcript-file PATH         Use existing transcript; skips download and transcription
  --audio-file PATH              Use existing audio file; skips download, transcribes directly
  --title TEXT                   Video title for --transcript-file or --audio-file
  --draft                        Set draft: true in the output frontmatter [default: false]
  --mistral-model TEXT           [default: voxtral-mini-latest]
  --audio-format [mp3|m4a]       [default: mp3]
  --version                      Show version and exit
```

## Output Frontmatter

Every generated file includes YAML frontmatter:

```yaml
---
title: "Video Title"
url: https://youtu.be/...
description: "YouTube video description"
date: 2026-04-12
draft: false
---
```

Use `--draft` to set `draft: true` (useful for Hugo, Jekyll, or similar static site generators).
Merged documents (`--merge`) do not include frontmatter.

## Content Types

| Type | Use for |
|------|---------|
| `auto` | Let the LLM detect (default) |
| `tutorial` | How-to / step-by-step videos |
| `lecture` | Tech talks, academic presentations |
| `ib` | IB student subject videos |

## Custom Prompts

Override the built-in prompt with your own file. Template variables:
`{title}`, `{channel}`, `{content_type}`, `{duration}`

```bash
yt-instruct <url> --prompt-file my_prompt.md
```

## Using the `llm` backend

```bash
pip install llm llm-anthropic
llm keys set anthropic
yt-instruct <url> --backend llm --model claude-sonnet-4-6
```

## Using the `nvidia` backend

```bash
NVIDIA_API_KEY=... yt-instruct <url> --backend nvidia --model moonshotai/kimi-k2-instruct
```

## Batch Processing

```bash
# Multiple URLs
yt-instruct url1 url2 url3 --output-dir ./docs

# Playlist (automatically expanded)
yt-instruct https://www.youtube.com/playlist?list=<id> --output-dir ./docs

# From file
cat urls.txt | yt-instruct --url-file /dev/stdin

# Merge all into one doc
yt-instruct url1 url2 --merge --output-dir ./docs
```

## Skip Steps — Use Existing Files

`--audio-file` and `--transcript-file` resolve relative to `--output-dir` if the file isn't found at the given path. This lets you reference files already in the output directory without typing the full path:

```bash
# Start from an existing transcript (skips download + transcription)
yt-instruct --transcript-file transcript.txt --title "My Video" --output-dir ./docs

# File not found locally? Looked up in ./docs automatically
yt-instruct --transcript-file my_transcript.txt --output-dir ./docs

# Start from an existing audio file (skips download, still transcribes)
yt-instruct --audio-file recording.mp3 --output-dir ./docs
```

## Resume an Interrupted Run

Use `--keep` to save transcripts alongside output files, then `--resume` to continue from where a previous run stopped:

```bash
# First run (interrupted partway through)
yt-instruct --url-file urls.txt --keep --output-dir ./docs

# Resume — skips videos with existing output; reuses cached transcripts
yt-instruct --url-file urls.txt --resume --output-dir ./docs
```

`--resume` checks at two levels per video:
1. Output `.md` already exists → skip entirely
2. Cached `*_transcript.txt` exists (saved by `--keep`) → skip download and transcription, regenerate only

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

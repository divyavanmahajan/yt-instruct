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

## Usage

```
yt-instruct [OPTIONS] URL [URL...]
yt-instruct [OPTIONS] --url-file urls.txt

Options:
  --output-dir PATH         Output directory [default: .]
  --keep                    Keep intermediate audio + transcript files
  --merge                   Merge all videos into one document
  --content-type [tutorial|lecture|ib|auto]
                            Prompt style [default: auto]
  --backend [anthropic|llm] LLM backend [default: anthropic]
  --model TEXT              Model name [default: claude-sonnet-4-6]
  --prompt-file PATH        Custom system prompt (overrides built-in)
  --mistral-model TEXT      [default: voxtral-mini-latest]
  --audio-format [mp3|m4a]  [default: mp3]
  --version                 Show version and exit
```

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

## Batch Processing

```bash
# Multiple URLs
yt-instruct url1 url2 url3 --output-dir ./docs

# From file
cat urls.txt | yt-instruct --url-file /dev/stdin

# Merge all into one doc
yt-instruct url1 url2 --merge --output-dir ./docs
```

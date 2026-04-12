# yt-instruct — Product Specification

## Problem

YouTube tutorials, tech talks, and IB subject videos are rich with structured knowledge, but consuming that knowledge requires watching the full video. There is no lightweight way to extract the instructional content into a reusable, searchable document.

## Target Users

- **Students** (especially IB) who want revision notes from YouTube explainers
- **Developers** who watch tutorials and want a reference document to follow later
- **Learners** who prefer reading over watching, or want to bookmark key steps

## Core Feature Set

### Input
- One or more YouTube URLs as CLI arguments
- A text file of URLs via `--url-file`

### Pipeline
```
URL → download audio (yt-dlp) → transcribe (Mistral voxtral) → generate markdown (Claude/llm) → write file
```

### Output
- One `{slug}_instructions.md` per video in `--output-dir` (default: current directory)
- Optional `--merge` to combine all videos into `merged_instructions.md`

### Content Types
| Type | Target |
|------|--------|
| `tutorial` | How-to / step-by-step practical videos |
| `lecture` | Tech talks, academic presentations |
| `ib` | IB student subject videos (maths, sciences, humanities) |
| `auto` | LLM classifies based on title + channel (default) |

### LLM Backends
| Backend | How |
|---------|-----|
| `anthropic` | Anthropic Python SDK, requires `ANTHROPIC_API_KEY` (default) |
| `llm` | simonw/llm library, model configured via `llm keys set` |

## API Contracts

### downloader.download_audio(url, tmp_dir, audio_format) → VideoInfo
```python
@dataclass
class VideoInfo:
    title: str
    channel: str
    url: str
    duration: int | None  # seconds
    audio_path: Path
```

### transcriber.transcribe(audio_path, model) → str
Returns plain text transcript.

### generator.generate(video, transcript, content_type, backend, model, prompt_file) → str
Returns markdown document.

## Environment Variables
| Variable | Required when |
|----------|--------------|
| `MISTRAL_API_KEY` | Always |
| `ANTHROPIC_API_KEY` | `--backend anthropic` (default) |

## Prompt Customisation
- Built-in prompts: `src/yt_instruct/prompts/{tutorial,lecture,ib,default}.md`
- Override with `--prompt-file path/to/prompt.md`
- Template variables available in prompts: `{title}`, `{channel}`, `{content_type}`, `{duration}`

## Constraints
- Requires `ffmpeg` for audio extraction (yt-dlp post-processor)
- Audio is transcribed via Mistral's cloud API (data leaves device)
- LLM generation via Anthropic's cloud API or locally-configured llm models
- Python ≥ 3.10 required

"""yt-instruct CLI — Download, transcribe, and generate instruction docs from YouTube videos."""

import sys
import tempfile
from datetime import date
from pathlib import Path

import click

from . import __version__
from .downloader import VideoInfo, download_audio, fetch_info, resolve_urls
from .generator import generate
from .transcriber import transcribe
from .utils import output_path, slugify


def _frontmatter(title: str, url: str, description: str, draft: bool) -> str:
    safe_title = title.replace('"', '\\"')
    safe_desc = description.replace('"', '\\"')
    draft_str = "true" if draft else "false"
    return (
        "---\n"
        f'title: "{safe_title}"\n'
        f"url: {url}\n"
        f'description: "{safe_desc}"\n'
        f"date: {date.today().isoformat()}\n"
        f"draft: {draft_str}\n"
        "---\n\n"
    )


def _transcript_cache_path(output_dir: Path, title: str) -> Path:
    """Predictable path for a cached transcript file (used by --keep and --resume)."""
    return output_dir / f"{slugify(title)}_transcript.txt"


def _resolve_input_file(path: Path, output_dir: Path) -> Path:
    """Resolve an input file path, falling back to output_dir if the file isn't found as-is."""
    if path.exists():
        return path
    candidate = output_dir / path
    if candidate.exists():
        return candidate
    raise click.BadParameter(f"File not found: {path} (also tried {candidate})")


@click.command()
@click.version_option(__version__, prog_name="yt-instruct")
@click.argument("urls", nargs=-1, metavar="URL...")
@click.option(
    "--url-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Text file with one YouTube URL per line.",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory to write output markdown files.",
)
@click.option(
    "--keep",
    is_flag=True,
    default=False,
    help="Keep intermediate audio and transcript files.",
)
@click.option(
    "--merge",
    is_flag=True,
    default=False,
    help="Merge all videos into a single output document.",
)
@click.option(
    "--content-type",
    type=click.Choice(["tutorial", "lecture", "ib", "auto"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Prompt style to use for generation.",
)
@click.option(
    "--backend",
    type=click.Choice(["anthropic", "llm", "nvidia"], case_sensitive=False),
    default="anthropic",
    show_default=True,
    help="LLM backend to use.",
)
@click.option(
    "--model",
    default="claude-sonnet-4-6",
    show_default=True,
    help="Model name (e.g. 'claude-sonnet-4-6' for anthropic/llm, 'moonshotai/kimi-k2-instruct' for nvidia).",
)
@click.option(
    "--prompt-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Custom system prompt file (overrides built-in prompts).",
)
@click.option(
    "--mistral-model",
    default="voxtral-mini-latest",
    show_default=True,
    help="Mistral transcription model.",
)
@click.option(
    "--audio-format",
    type=click.Choice(["mp3", "m4a"], case_sensitive=False),
    default="mp3",
    show_default=True,
    help="Audio format for intermediate file.",
)
@click.option(
    "--language",
    default=None,
    metavar="LANG",
    help="Output language for the generated document (e.g. 'French', 'Spanish'). Defaults to English.",
)
@click.option(
    "--transcript-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Use an existing transcript .txt file; skips download and transcription.",
)
@click.option(
    "--audio-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Use an existing audio file (e.g. MP3); skips download, transcribes directly.",
)
@click.option(
    "--title",
    default=None,
    help="Video title to use with --transcript-file or --audio-file (defaults to filename stem).",
)
@click.option(
    "--draft",
    is_flag=True,
    default=False,
    help="Set draft: true in the output frontmatter.",
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help=(
        "Skip videos that already have a generated output file. "
        "If a cached transcript (from --keep) exists, skips download and transcription too."
    ),
)
def cli(
    urls,
    url_file,
    output_dir,
    keep,
    merge,
    content_type,
    backend,
    model,
    prompt_file,
    mistral_model,
    audio_format,
    language,
    transcript_file,
    audio_file,
    title,
    draft,
    resume,
):
    """Convert YouTube videos into structured markdown instruction documents.

    Pipeline: URL → audio download (yt-dlp) → transcription (Mistral voxtral) →
    LLM document generation (Anthropic / llm / NVIDIA). Each output file is
    prefixed with YAML frontmatter (title, url, description, date, draft).

    \b
    REQUIRED ENVIRONMENT VARIABLES
      MISTRAL_API_KEY      Always required (transcription).
      ANTHROPIC_API_KEY    Required for --backend anthropic (default).
      NVIDIA_API_KEY       Required for --backend nvidia.

    \b
    CONTENT TYPES
      auto      LLM classifies the video and picks the best template (default).
      tutorial  Hands-on how-to guides with steps and code.
      lecture   Tech talks and academic presentations.
      ib        IB student revision notes.

    \b
    BACKENDS
      anthropic  Anthropic Python SDK (default model: claude-sonnet-4-6).
      llm        Simon Willison's llm CLI library.
      nvidia     NVIDIA NIM API via OpenAI-compatible endpoint.

    \b
    FILE RESOLUTION FOR --audio-file AND --transcript-file
      If the given path does not exist, it is looked up inside --output-dir.
      Example: --audio-file recording.mp3 --output-dir ./docs
               resolves to ./docs/recording.mp3 if not found locally.

    \b
    EXAMPLES
      yt-instruct https://youtu.be/dQw4w9WgXcQ
      yt-instruct url1 url2 --output-dir ./docs
      yt-instruct <URL> --content-type tutorial --backend llm
      yt-instruct --url-file urls.txt --merge --output-dir ./docs
      yt-instruct --transcript-file transcript.txt --title "My Video"
      yt-instruct --audio-file recording.mp3 --output-dir ./docs
      yt-instruct <URL> --backend nvidia --model moonshotai/kimi-k2-instruct
      yt-instruct <URL> --language French
      yt-instruct <URL> --draft
      yt-instruct --url-file urls.txt --keep --output-dir ./docs
      yt-instruct --url-file urls.txt --resume --output-dir ./docs
    """
    # Fast path: transcript file provided — skip download and transcription
    if transcript_file:
        if urls or url_file or audio_file:
            raise click.UsageError("--transcript-file cannot be combined with URLs, --url-file, or --audio-file.")
        output_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = _resolve_input_file(transcript_file, output_dir)
        transcript = transcript_file.read_text(encoding="utf-8").strip()
        resolved_title = title or transcript_file.stem
        video = VideoInfo(title=resolved_title, channel="", url="", duration=None, audio_path=None)
        lang_note = f", language={language}" if language else ""
        click.echo(f"\n[yt-instruct] Generating from transcript: {transcript_file.name} ({content_type}, backend={backend}{lang_note})")
        try:
            markdown = generate(
                video=video,
                transcript=transcript,
                content_type=content_type,
                backend=backend,
                model=model,
                prompt_file=prompt_file,
                language=language,
            )
        except Exception as e:
            click.echo(f"  ERROR: {e}", err=True)
            sys.exit(1)
        out = output_path(output_dir, resolved_title)
        out.write_text(_frontmatter(resolved_title, video.url, video.description, draft) + markdown, encoding="utf-8")
        click.echo(f"  Written: {out}")
        return

    # Fast path: audio file provided — skip download, transcribe directly
    if audio_file:
        if urls or url_file:
            raise click.UsageError("--audio-file cannot be combined with URLs or --url-file.")
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_file = _resolve_input_file(audio_file, output_dir)
        resolved_title = title or audio_file.stem
        video = VideoInfo(title=resolved_title, channel="", url="", duration=None, audio_path=audio_file)
        lang_note = f", language={language}" if language else ""
        click.echo(f"\n[yt-instruct] Transcribing audio file: {audio_file} ({content_type}, backend={backend}{lang_note})")
        click.echo("  Transcribing...")
        try:
            transcript = transcribe(video.audio_path, mistral_model)
        except Exception as e:
            click.echo(f"  ERROR transcribing: {e}", err=True)
            sys.exit(1)
        click.echo(f"  Transcript: {len(transcript)} chars")
        if keep:
            _transcript_cache_path(output_dir, resolved_title).write_text(transcript, encoding="utf-8")
        click.echo(f"  Generating ({content_type}, backend={backend}{lang_note})...")
        try:
            markdown = generate(
                video=video,
                transcript=transcript,
                content_type=content_type,
                backend=backend,
                model=model,
                prompt_file=prompt_file,
                language=language,
            )
        except Exception as e:
            click.echo(f"  ERROR generating: {e}", err=True)
            sys.exit(1)
        out = output_path(output_dir, resolved_title)
        out.write_text(_frontmatter(resolved_title, video.url, video.description, draft) + markdown, encoding="utf-8")
        click.echo(f"  Written: {out}")
        return

    all_urls = list(urls)
    if url_file:
        lines = url_file.read_text(encoding="utf-8").splitlines()
        all_urls.extend(line.strip() for line in lines if line.strip() and not line.startswith("#"))

    if not all_urls:
        raise click.UsageError("No URLs provided. Pass URLs as arguments or use --url-file.")

    # Expand playlists to individual video URLs
    expanded: list[str] = []
    for raw_url in all_urls:
        try:
            resolved = resolve_urls(raw_url)
            if len(resolved) > 1:
                click.echo(f"[yt-instruct] Playlist detected: {len(resolved)} videos in {raw_url}")
            expanded.extend(resolved)
        except Exception as e:
            click.echo(f"[yt-instruct] WARNING: could not resolve {raw_url}: {e}", err=True)
            expanded.append(raw_url)  # try anyway

    output_dir.mkdir(parents=True, exist_ok=True)

    # Use a persistent temp dir so we can --keep audio if needed
    tmp_dir = Path(tempfile.mkdtemp(prefix="yt-instruct-"))
    results: list[tuple[str, str]] = []  # (title, markdown)

    try:
        for i, url in enumerate(expanded, 1):
            prefix = f"[{i}/{len(expanded)}]" if len(expanded) > 1 else ""
            click.echo(f"\n[yt-instruct]{prefix} Processing: {url}")

            video = None
            transcript = None
            skip_download = False
            skip_transcription = False

            # Resume: fetch lightweight metadata, then check for existing output / cached transcript
            if resume:
                try:
                    meta = fetch_info(url)
                except Exception as e:
                    click.echo(f"  WARNING: could not fetch metadata for resume check: {e}", err=True)
                    meta = None

                if meta:
                    out = output_path(output_dir, meta.title)
                    if out.exists():
                        click.echo(f"  [resume] Already done, skipping: {out.name}")
                        continue

                    cached_transcript = _transcript_cache_path(output_dir, meta.title)
                    if cached_transcript.exists():
                        click.echo(f"  [resume] Found cached transcript, skipping download and transcription.")
                        transcript = cached_transcript.read_text(encoding="utf-8").strip()
                        video = meta
                        skip_download = True
                        skip_transcription = True

            # Step 1: Download
            if not skip_download:
                click.echo("  Downloading audio...")
                try:
                    video = download_audio(url, tmp_dir, audio_format)
                except Exception as e:
                    click.echo(f"  ERROR downloading {url}: {e}", err=True)
                    if len(expanded) > 1 and i < len(expanded):
                        if not click.confirm("  Continue with remaining videos?", default=True):
                            break
                    continue
                click.echo(f"  Downloaded: {video.title!r} ({video.channel})")

            # Step 2: Transcribe
            if not skip_transcription:
                click.echo("  Transcribing...")
                try:
                    transcript = transcribe(video.audio_path, mistral_model)
                except Exception as e:
                    click.echo(f"  ERROR transcribing {url}: {e}", err=True)
                    continue
                click.echo(f"  Transcript: {len(transcript)} chars")
                if keep:
                    _transcript_cache_path(output_dir, video.title).write_text(transcript, encoding="utf-8")

            # Step 3: Generate
            lang_note = f", language={language}" if language else ""
            click.echo(f"  Generating ({content_type}, backend={backend}{lang_note})...")
            try:
                markdown = generate(
                    video=video,
                    transcript=transcript,
                    content_type=content_type,
                    backend=backend,
                    model=model,
                    prompt_file=prompt_file,
                    language=language,
                )
            except Exception as e:
                click.echo(f"  ERROR generating for {url}: {e}", err=True)
                continue

            results.append((video.title, markdown))

            if not merge:
                out = output_path(output_dir, video.title)
                out.write_text(_frontmatter(video.title, video.url, video.description, draft) + markdown, encoding="utf-8")
                click.echo(f"  Written: {out}")

    finally:
        import shutil
        if keep:
            # Move remaining intermediate audio files into output_dir
            moved = []
            for f in tmp_dir.iterdir():
                dest = output_dir / f.name
                shutil.move(str(f), dest)
                moved.append(dest.name)
            if moved:
                click.echo(f"\nIntermediate audio files moved to {output_dir}/: {', '.join(moved)}")
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if not results:
        click.echo("\nNo documents generated.", err=True)
        sys.exit(1)

    # Merge mode: combine all into one file
    if merge:
        combined = "\n\n---\n\n".join(md for _, md in results)
        merged_path = output_dir / "merged_instructions.md"
        merged_path.write_text(combined, encoding="utf-8")  # no frontmatter for merged docs
        click.echo(f"\nMerged document written: {merged_path}")
    else:
        click.echo(f"\nDone. {len(results)} document(s) written to {output_dir}/")

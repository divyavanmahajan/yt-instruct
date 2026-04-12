"""yt-instruct CLI — Download, transcribe, and generate instruction docs from YouTube videos."""

import sys
import tempfile
from pathlib import Path

import click

from . import __version__
from .downloader import VideoInfo, download_audio, resolve_urls
from .generator import generate
from .transcriber import transcribe
from .utils import output_path


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
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Use an existing transcript .txt file; skips download and transcription.",
)
@click.option(
    "--title",
    default=None,
    help="Video title to use when --transcript-file is given (defaults to filename stem).",
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
    title,
):
    """Convert YouTube videos into structured markdown instruction documents.

    Provide one or more URLs as arguments, or use --url-file for batch processing.
    Use --transcript-file to skip download and transcription and generate directly
    from an existing transcript.

    Examples:

        yt-instruct https://www.youtube.com/watch?v=dQw4w9WgXcQ --output-dir ./docs

        yt-instruct --transcript-file transcript.txt --title "My Video" --output-dir ./docs
    """
    # Fast path: transcript file provided — skip download and transcription
    if transcript_file:
        if urls or url_file:
            raise click.UsageError("--transcript-file cannot be combined with URLs or --url-file.")
        output_dir.mkdir(parents=True, exist_ok=True)
        transcript = transcript_file.read_text(encoding="utf-8").strip()
        resolved_title = title or transcript_file.stem
        video = VideoInfo(
            title=resolved_title,
            channel="",
            url="",
            duration=None,
            audio_path=None,
        )
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
        out.write_text(markdown, encoding="utf-8")
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

    # Use a persistent temp dir so we can --keep if needed
    tmp_dir = Path(tempfile.mkdtemp(prefix="yt-instruct-"))
    results: list[tuple[str, str]] = []  # (title, markdown)

    try:
        for i, url in enumerate(expanded, 1):
            prefix = f"[{i}/{len(expanded)}]" if len(expanded) > 1 else ""
            click.echo(f"\n[yt-instruct]{prefix} Processing: {url}")

            # Step 1: Download
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
            click.echo("  Transcribing...")
            try:
                transcript = transcribe(video.audio_path, mistral_model)
            except Exception as e:
                click.echo(f"  ERROR transcribing {url}: {e}", err=True)
                continue
            click.echo(f"  Transcript: {len(transcript)} chars")

            if keep:
                transcript_path = tmp_dir / f"{video.audio_path.stem}.txt"
                transcript_path.write_text(transcript, encoding="utf-8")

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
                out.write_text(markdown, encoding="utf-8")
                click.echo(f"  Written: {out}")

    finally:
        if keep:
            import shutil
            # Move intermediate files (audio + any transcripts) into output_dir
            moved = []
            for f in tmp_dir.iterdir():
                dest = output_dir / f.name
                shutil.move(str(f), dest)
                moved.append(dest.name)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            if moved:
                click.echo(f"\nIntermediate files moved to {output_dir}/: {', '.join(moved)}")
        else:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if not results:
        click.echo("\nNo documents generated.", err=True)
        sys.exit(1)

    # Merge mode: combine all into one file
    if merge:
        combined = "\n\n---\n\n".join(md for _, md in results)
        merged_path = output_dir / "merged_instructions.md"
        merged_path.write_text(combined, encoding="utf-8")
        click.echo(f"\nMerged document written: {merged_path}")
    else:
        click.echo(f"\nDone. {len(results)} document(s) written to {output_dir}/")

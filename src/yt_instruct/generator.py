"""Instruction document generator using Claude (Anthropic SDK, Claude CLI, or llm library) or NVIDIA NIM."""

import importlib.resources
import os
import shutil
import subprocess
from pathlib import Path

from .downloader import VideoInfo
from .utils import format_duration

BUILTIN_PROMPTS_PACKAGE = "yt_instruct.prompts"

AUTO_CLASSIFY_PROMPT = """You are classifying a YouTube video. Based on the title and channel below,
respond with exactly one word — the content type that best fits:
- tutorial  (how-to, step-by-step, practical skill)
- lecture   (tech talk, academic, educational presentation)
- ib        (IB student subject: maths, sciences, humanities, etc.)

Title: {title}
Channel: {channel}

Respond with one word only."""


def _load_builtin_prompt(content_type: str) -> str:
    """Load a built-in prompt template from the prompts package."""
    try:
        ref = importlib.resources.files(BUILTIN_PROMPTS_PACKAGE).joinpath(
            f"{content_type}.md"
        )
        return ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        # Fall back to default
        ref = importlib.resources.files(BUILTIN_PROMPTS_PACKAGE).joinpath("default.md")
        return ref.read_text(encoding="utf-8")


def _load_prompt(content_type: str, prompt_file: Path | None) -> str:
    """Load prompt template from user file or built-in resource."""
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8")
    return _load_builtin_prompt(content_type)


def _build_messages(
    video: VideoInfo, transcript: str, content_type: str, system_prompt: str,
    language: str | None = None,
) -> tuple[str, str]:
    """Return (system, user) message strings."""
    system = system_prompt.format(
        title=video.title,
        channel=video.channel,
        content_type=content_type,
        duration=format_duration(video.duration),
    )
    if language:
        system += f"\n\nWrite the output document in {language}."
    user = (
        f"Video: {video.title}\n"
        f"Channel: {video.channel}\n"
        f"URL: {video.url}\n"
        f"Duration: {format_duration(video.duration)}\n\n"
        f"Transcript:\n{transcript}"
    )
    return system, user


def _detect_content_type_anthropic(
    video: VideoInfo, model: str, client
) -> str:
    prompt = AUTO_CLASSIFY_PROMPT.format(title=video.title, channel=video.channel)
    msg = client.messages.create(
        model=model,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    result = msg.content[0].text.strip().lower()
    return result if result in ("adhd", "tutorial", "lecture", "ib") else "tutorial"


def _detect_content_type_llm(video: VideoInfo, model_name: str) -> str:
    import llm

    prompt = AUTO_CLASSIFY_PROMPT.format(title=video.title, channel=video.channel)
    model_obj = llm.get_model(model_name)
    result = model_obj.prompt(prompt).text().strip().lower()
    return result if result in ("adhd", "tutorial", "lecture", "ib") else "tutorial"


def generate_anthropic(
    video: VideoInfo,
    transcript: str,
    content_type: str,
    model: str,
    prompt_file: Path | None,
    language: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Generate instruction document using Anthropic SDK."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set."
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Auto-detect content type if requested
    resolved_type = content_type
    if content_type == "auto":
        resolved_type = _detect_content_type_anthropic(video, model, client)

    system_prompt = _load_prompt(resolved_type, prompt_file)
    system, user = _build_messages(video, transcript, resolved_type, system_prompt, language)

    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def generate_llm(
    video: VideoInfo,
    transcript: str,
    content_type: str,
    model: str,
    prompt_file: Path | None,
    language: str | None = None,
) -> str:
    """Generate instruction document using simonw/llm library."""
    import llm

    resolved_type = content_type
    if content_type == "auto":
        resolved_type = _detect_content_type_llm(video, model)

    system_prompt = _load_prompt(resolved_type, prompt_file)
    system, user = _build_messages(video, transcript, resolved_type, system_prompt, language)

    model_obj = llm.get_model(model)
    return model_obj.prompt(user, system=system).text()


def _detect_content_type_nvidia(video: VideoInfo, model: str, client) -> str:
    prompt = AUTO_CLASSIFY_PROMPT.format(title=video.title, channel=video.channel)
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0.0,
    )
    result = completion.choices[0].message.content.strip().lower()
    return result if result in ("adhd", "tutorial", "lecture", "ib") else "tutorial"


def generate_nvidia(
    video: VideoInfo,
    transcript: str,
    content_type: str,
    model: str,
    prompt_file: Path | None,
    language: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Generate instruction document using NVIDIA NIM (OpenAI-compatible API)."""
    from openai import OpenAI

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY environment variable is not set.")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )

    resolved_type = content_type
    if content_type == "auto":
        resolved_type = _detect_content_type_nvidia(video, model, client)

    system_prompt = _load_prompt(resolved_type, prompt_file)
    system, user = _build_messages(video, transcript, resolved_type, system_prompt, language)

    chunks = []
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.6,
        top_p=0.9,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in completion:
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta.content
        if delta is not None:
            chunks.append(delta)
    return "".join(chunks)


def _claude_cli_env() -> dict[str, str]:
    """Environment for the `claude` CLI subprocess.

    Strip ANTHROPIC_API_KEY so the CLI authenticates against the user's Claude
    subscription (Pro/Max OAuth login) rather than the metered pay-as-you-go API.
    The CLI resolves ANTHROPIC_API_KEY ahead of the subscription login, so leaving
    it set would silently bill the API instead.
    """
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def _run_claude_cli(system: str, user: str, timeout: int = 600) -> str:
    """Invoke `claude -p` in print mode and return its stdout."""
    if not shutil.which("claude"):
        raise RuntimeError(
            "The `claude` CLI was not found on PATH. Install Claude Code and run "
            "`claude` once to log in with your subscription before using "
            "--backend claude-cli."
        )
    try:
        result = subprocess.run(
            ["claude", "-p", system],
            input=user,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_claude_cli_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"claude CLI timed out after {timeout}s.") from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited with code {result.returncode}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("claude CLI produced no output.")
    return output


def _detect_content_type_claude_cli(video: VideoInfo) -> str:
    prompt = AUTO_CLASSIFY_PROMPT.format(title=video.title, channel=video.channel)
    result = _run_claude_cli(prompt, "", timeout=120).strip().lower()
    return result if result in ("adhd", "tutorial", "lecture", "ib") else "tutorial"


def generate_claude_cli(
    video: VideoInfo,
    transcript: str,
    content_type: str,
    prompt_file: Path | None,
    language: str | None = None,
) -> str:
    """Generate instruction document via the Claude CLI (uses the Claude subscription).

    Mirrors the anthropic backend but shells out to `claude -p` so generation is
    billed against a Pro/Max subscription instead of the metered API. `model` is
    intentionally ignored — the CLI uses its own configured default model.
    """
    resolved_type = content_type
    if content_type == "auto":
        resolved_type = _detect_content_type_claude_cli(video)

    system_prompt = _load_prompt(resolved_type, prompt_file)
    system, user = _build_messages(video, transcript, resolved_type, system_prompt, language)
    return _run_claude_cli(system, user)


def generate(
    video: VideoInfo,
    transcript: str,
    content_type: str,
    backend: str,
    model: str,
    prompt_file: Path | None,
    language: str | None = None,
) -> str:
    """Dispatch to the appropriate backend."""
    if backend == "anthropic":
        return generate_anthropic(video, transcript, content_type, model, prompt_file, language)
    elif backend == "claude-cli":
        return generate_claude_cli(video, transcript, content_type, prompt_file, language)
    elif backend == "llm":
        return generate_llm(video, transcript, content_type, model, prompt_file, language)
    elif backend == "nvidia":
        return generate_nvidia(video, transcript, content_type, model, prompt_file, language)
    else:
        raise ValueError(
            f"Unknown backend: {backend!r}. Choose 'anthropic', 'claude-cli', 'llm', or 'nvidia'."
        )

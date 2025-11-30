"""Log summarization utilities using OpenAI chat completions.

This module exposes helpers that:
- Build a system prompt that constrains the model to basic Markdown.
- Build a user prompt from one or many `Log` objects, plus an optional
  custom instruction.
- Call `send_prompt_to_openai` from `openai_prompter`.
- Return the summary as a plain string.

Public API:
- summarize_log(log: Log, prompt: str | None = None) -> str
- summarize_logs(logs: list[Log], prompt: str | None = None) -> str

The caller is responsible for deciding where (or whether) to persist
any returned summaries.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from DataClasses.log import Log
from .openai_prompter import content_summarization_enabled, send_prompt_to_openai


DEFAULT_SUMMARY_PROMPT = "Summarize the content of the log(s)."


def _build_system_prompt() -> str:
    """Build the system prompt constraining output to basic Markdown.

    The model is instructed to:
    - Use only paragraphs, bullet lists, numbered lists, and simple
      headings ("#", "##").
    - Avoid tables, images, HTML, or advanced formatting.
    - Avoid code blocks unless they are directly quoted from the log.
    - Focus strictly on the provided log text and instructions.
    """

    lines: List[str] = []
    lines.append("You are a helpful assistant that summarizes personal journal logs.")
    lines.append("")
    lines.append("Output format constraints:")
    lines.append("- Only use basic Markdown features:")
    lines.append("  - Plain paragraphs.")
    lines.append("  - Bullet lists using '-' or '*'.")
    lines.append("  - Numbered lists like '1.', '2.', etc.")
    lines.append("  - Simple headings using '# ' or '## '.")
    lines.append("- Do NOT use tables, images, HTML tags, footnotes, or links.")
    lines.append("- Avoid fenced code blocks (```); if quoting text, just use inline quotes or indented lines.")
    lines.append("- Do not include any YAML front matter.")
    lines.append("")
    lines.append("Content requirements:")
    lines.append("- Base your response only on the provided log text.")
    lines.append("- Do not invent details that are not supported by the logs.")
    lines.append("- Follow any user instruction in the prompt. If no clear instruction is given, summarize the content.")
    lines.append("- Focus on the main events, feelings, and themes in the logs.")

    return "\n".join(lines)


def _format_single_log(log: Log) -> str:
    parts: List[str] = []
    parts.append(f"Log name: {log.name}")
    if log.description:
        parts.append("")
        parts.append("Description:")
        parts.append(log.description)
    if log.body:
        parts.append("")
        parts.append("Body:")
        parts.append(log.body)
    return "\n".join(parts)


def _build_user_prompt_for_logs(logs: Iterable[Log], prompt: Optional[str]) -> str:
    logs_list = list(logs)
    if not logs_list:
        raise ValueError("summarize_logs was called with an empty list of logs")

    instruction = prompt.strip() if prompt and prompt.strip() else DEFAULT_SUMMARY_PROMPT

    parts: List[str] = []
    parts.append(f"Instruction: {instruction}")
    parts.append("")
    if len(logs_list) == 1:
        parts.append("The following is a single log entry:")
        parts.append("")
        parts.append(_format_single_log(logs_list[0]))
    else:
        parts.append(f"The following are {len(logs_list)} log entries. Use them all when responding to the instruction above.")
        for idx, log in enumerate(logs_list, start=1):
            parts.append("")
            parts.append(f"=== Log {idx} ===")
            parts.append(_format_single_log(log))

    return "\n".join(parts)


def _extract_text_response(response) -> str:
    """Extract the assistant's text content from a ChatCompletion response."""

    # We expect a standard Chat Completions response as returned by
    # `send_prompt_to_openai`. Mirror the extraction pattern from
    # `sentiment_analysis._response_to_json`, but keep it string-based.
    choice = response.choices[0]
    msg = choice.message
    content = getattr(msg, "content", None)
    if not isinstance(content, str):
        content = str(content)
    return content

def summarize_logs(logs: Iterable[Log], prompt: Optional[str] = None) -> str:
    """Summarize a list of `Log` objects and return the Markdown string.

    - `logs` must contain at least one log.
    - `prompt` is an optional custom instruction about the list of logs
      (e.g., "compare how my stress levels changed over time").
      If missing or blank, a generic summary instruction is used.
    """

    if not content_summarization_enabled():
        raise RuntimeError("Content summarization is disabled in user settings.")

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt_for_logs(logs, prompt)

    response = send_prompt_to_openai(
        system=system_prompt,
        prompt=user_prompt,
        json_mode=False,
    )
    return _extract_text_response(response)


__all__ = [
    "summarize_logs",
    "DEFAULT_SUMMARY_PROMPT",
]
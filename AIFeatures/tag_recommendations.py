"""Tag recommendation utilities using OpenAI chat completions.

This module exposes a main function
`recommend_tags_for_log(log: DataClasses.log.Log)` which:

- Builds a system prompt using the tag-selection instructions.
- Uses the current set of user-defined tags from `DataClasses.tag.tags`.
- Sends the combined instructions, allowed tags, and log body to OpenAI via
  `send_prompt_to_openai`.
- Expects the model to return JSON of the form:

    { "selected": [ { "name": str, "confidence": float }, ... ] }

- Returns the parsed JSON object and does not persist anything to disk.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from DataClasses.log import Log
from DataClasses.tag import tags as USER_TAGS, Tag
from .openai_prompter import (
    sentiment_analysis_enabled,
    send_prompt_to_openai,
)


def _format_allowed_tags(user_tags: List[Tag]) -> str:
    """Format the allowed tags list for inclusion in the prompt."""

    # We include both name and description so the model can match by meaning,
    # but we stress in the instructions that it must respect descriptions.
    lines: list[str] = []
    for t in user_tags:
        desc = t.description or "(no description provided)"
        lines.append(f"- name: {t.name}\n  description: {desc}")
    return "\n".join(lines)


def _build_system_prompt() -> str:
    """Build the system prompt with detailed tag-selection instructions."""

    lines: list[str] = []
    lines.append("Task: From the provided journal log content, select zero or more relevant tags from the allowed set.")
    lines.append("")
    lines.append("Rules:")
    lines.append("- Only select from the allowedTags list provided. Do not invent new tags.")
    lines.append("- If no tags clearly apply, return an empty list.")
    lines.append("- There is no limit on how many tags you may select, as long as they are clearly relevant.")
    lines.append("- Base your choices strictly on the provided content (title/description/body).")
    lines.append("- Do not recommend tags solely based on their names. Ensure the tag's description matches the content.")
    lines.append("")
    lines.append("Output requirements:")
    lines.append("- Return only valid JSON.")
    lines.append("- JSON fields: selected = array of tag names (strings).")
    lines.append("- Each name must match exactly one of the allowedTags names.")
    lines.append("")
    lines.append("allowedTags:")
    # The actual allowed tags list is appended in the user prompt for clarity.

    return "\n".join(lines)


def _build_user_prompt(log: Log, user_tags: List[Tag]) -> str:
    """Build the user prompt content using the log fields and allowed tags."""

    parts: list[str] = []
    parts.append("allowedTags:")
    parts.append(_format_allowed_tags(user_tags))
    parts.append("")
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


def _response_to_json(response: Any) -> Dict[str, Any]:
    """Extract the JSON payload from an OpenAI JSON-mode response.

    We call the Chat Completions API with
    ``response_format={"type": "json_object"}``, so ``message.content``
    is expected to be a single JSON string. Here we simply load that
    string as JSON and surface a clear error if anything unexpected
    happens.
    """

    try:
        choice = response.choices[0]
        msg = choice.message
        content = getattr(msg, "content", None)
        if not isinstance(content, str):
            content = str(content)
        data = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Failed to parse tag recommendations JSON from OpenAI response") from exc

    # Very lightweight shape validation
    selected = data.get("selected", [])
    if not isinstance(selected, list):
        raise ValueError("Tag recommendations JSON must contain 'selected' as a list")

    for item in selected:
        if not isinstance(item, str):
            raise ValueError("Each selected tag must be a string tag name")

    return data


def recommend_tags_for_log(log: Log) -> Dict[str, Any]:
    """Recommend tags for a `Log` using the current user tag set.

        - Uses the global tag list from `DataClasses.tag.tags` as allowedTags.
        - If the AI feature flag (re-using `sentiment_analysis_enabled`) is disabled,
            this function raises a `RuntimeError`.
        - On success, returns the parsed JSON result.
    """

    if not sentiment_analysis_enabled():
        raise RuntimeError("AI features are disabled in user settings.")

    user_tags = list(USER_TAGS)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(log, user_tags)

    response = send_prompt_to_openai(system=system_prompt, prompt=user_prompt)
    result_json = _response_to_json(response)
    return result_json


__all__ = ["recommend_tags_for_log"]

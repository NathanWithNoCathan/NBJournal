"""Sentiment analysis utilities using OpenAI chat completions.

This module exposes a single main function
`analyze_log_sentiment(log: DataClasses.log.Log)` which:

- Builds a rich system prompt using the scoring instructions.
- Sends the combined instructions and log body to OpenAI via
  `send_prompt_to_openai`.
- Expects the model to return a JSON object mapping emotion labels
  (e.g. "joy", "sadness") to numeric scores.
- Persists the raw JSON analysis next to the log file, using the
  same filename but with `_analysis` inserted before the extension.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from DataClasses.log import Log, LOGS_FOLDER
from .openai_prompter import (
	sentiment_analysis_enabled,
	send_prompt_to_openai,
)


EMOTION_LABELS = [
	"joy",
	"sadness",
	"anger",
	"fear",
	"surprise",
	"disgust",
	"anxiety",
	"calm",
	"hope",
	"frustration",
	"loneliness",
	"grief",
	"love",
	"gratitude",
	"shame",
	"guilt",
	"pride",
	"confusion",
	"stress",
	"excitement",
	"boredom",
	"relief",
]


def _build_system_prompt() -> str:
	"""Build the system prompt with detailed scoring instructions.

	Mirrors the semantics of the instructions provided in the
	previous project, adapted for a JSON object output where keys are
	emotion labels and values are scores.
	"""

	labels_csv = ",".join(f'"{label}"' for label in EMOTION_LABELS)

	lines: list[str] = []
	lines.append("Task: Perform sentiment analysis on the provided personal journal log content.")
	lines.append("")
	lines.append("Output requirements:")
	lines.append("- Return only valid JSON.")
	lines.append("- The JSON must be an object mapping each emotion label to a numeric score.")
	lines.append("- For each emotion in emotionLabels:")
	lines.append("  - The key MUST be the emotion label.")
	lines.append("  - The value MUST be a number. If the strength/intensity of an emotion can be determined, score it from 1.0 to 10.0 (decimals allowed).")
	lines.append("  - If it is unclear or impossible to decide on a score due to limited information, or if the emotion is completely irrelevant, give a score of -1.")
	lines.append("  - Do NOT give an emotion a score of -1 solely for being absent; the score of -1 should be used only when a scoring cannot be properly determined.")
	lines.append("  Examples of when to use -1:")
	lines.append("    - The text is very short and does not provide enough context to assess the emotion.")
	lines.append("    - The text is neutral and does not convey any particular emotion, making it impossible to assign a meaningful score.")
	lines.append("    - The emotion is not relevant to the content of the text (e.g., scoring 'joy' in a technical log, or 'love' in a log talking about upcoming exams).")
	lines.append("  General scoring guideline:")
	lines.append("    1  - Extremely minimal or absent; emotion barely noticeable, or not present at all.")
	lines.append("    2  - Very mild; faint emotional tone, easily dismissed or controlled.")
	lines.append("    3  - Mild; emotion present but not disruptive, only slightly affecting mood or thoughts.")
	lines.append("    4  - Noticeable; emotion clearly felt and influencing behavior, but manageable.")
	lines.append("    5  - Moderate; balanced expression of emotion with some internal tension or motivation.")
	lines.append("    6  - Strong; emotion significantly influences mood, decisions, or tone of writing.")
	lines.append("    7  - Very strong; emotion dominates current thoughts or focus, visible in tone or language.")
	lines.append("    8  - Intense; emotion is overwhelming or hard to regulate, possibly affecting clarity or logic.")
	lines.append("    9  - Extreme; emotion overtakes reasoning or control, leading to impulsive or powerful expression.")
	lines.append("    10 - Maximum intensity; emotion fully consumes attention and thought, leaving little balance or restraint.")
	lines.append("- Evaluate strictly from the text provided. Do not hallucinate or infer beyond the text.")
	lines.append("- Use decimal scores when appropriate.")
	lines.append("- For each emotion, think carefully about the context and nuances in the text.")
	lines.append("- For each emotion, internally justify how the text supports the assigned score, but DO NOT include explanations in the JSON output.")
	lines.append("")
	lines.append("Safety requirement:")
	lines.append("- Additionally, include the following keys in the JSON object:")
	lines.append("  - riskToSelf: boolean.")
	lines.append("  - riskSeveritySelf: number from 0 to 10.")
	lines.append("  - riskToOthers: boolean.")
	lines.append("  - riskSeverityOthers: number from 0 to 10.")
	lines.append("- If the content indicates potential risk of self-harm (e.g., suicidal ideation, intent, plan) set riskToSelf=true and set riskSeveritySelf from 0 to 10 with this guideline:")
	lines.append("  0  - No mention or implication of distress, self-harm, or hopelessness.")
	lines.append("  1  - Normal emotional reflection; sadness or fatigue with no indication of risk or loss of control.")
	lines.append("  2  - Mild emotional distress (e.g., 'I've been feeling down lately') but explicitly stable and coping.")
	lines.append("  3  - Noticeable emotional pain, low mood, or self-criticism without suicidal thinking.")
	lines.append("  4  - Hopelessness, worthlessness, or vague references to 'not wanting to be here,' but no intent or plan.")
	lines.append("  5  - Passive suicidal ideation ('sometimes I wish I could disappear') but no plan or preparation.")
	lines.append("  6  - Recurrent suicidal thoughts or strong hopelessness, yet no intent or immediate risk.")
	lines.append("  7  - Mentions considering suicide or specific methods abstractly; possible early planning behavior.")
	lines.append("  8  - Clear suicidal ideation with a method or intent mentioned, but ambivalent about acting.")
	lines.append("  9  - Active suicidal intent with a plan or means accessible and urgency implied.")
	lines.append("  10 - Immediate danger: explicit plan, intent, and stated desire to die.")
	lines.append("- If the content indicates potential risk of harming others (e.g., violent intent, threats) set riskToOthers=true and set riskSeverityOthers from 0 to 10 with this guideline:")
	lines.append("  0  - No aggression or conflict described.")
	lines.append("  1  - Mild irritation or frustration expressed abstractly (e.g., 'people annoy me').")
	lines.append("  2  - Occasional anger or resentment toward others but no threatening or harmful language.")
	lines.append("  3  - Noticeable hostility or aggressive tone, yet purely verbal or rhetorical.")
	lines.append("  4  - Mentions wanting to 'lash out' or 'hurt someone' in a metaphorical or emotional way.")
	lines.append("  5  - Mentions violence in abstract or hypothetical terms but no real target or plan.")
	lines.append("  6  - Sustained anger toward specific people or groups; possible fixation but no stated intent.")
	lines.append("  7  - Mentions specific individuals or situations where violence is contemplated but not planned.")
	lines.append("  8  - Expresses clear violent fantasies or early preparation (e.g., thinking about methods).")
	lines.append("  9  - Stated desire or plan to harm others; intent appears serious and personal.")
	lines.append("  10 - Imminent danger: explicit threat, target, method, or timeframe expressed.")
	lines.append("- If no indication is present, set riskToSelf=false, riskSeveritySelf=0, riskToOthers=false, riskSeverityOthers=0.")
	lines.append("- Do not provide advice or instructions; return classification only.")
	lines.append("")
	lines.append("emotionLabels:")
	lines.append("[" + labels_csv + "]")

	return "\n".join(lines)


def _build_user_prompt(log: Log) -> str:
	"""Build the user prompt content using the log fields.

	We include the log's name, description, and body so the model has
	full context, but the model is instructed to evaluate strictly
	from the text content itself.
	"""

	parts: list[str] = []
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


def _get_analysis_file_path(log: Log) -> str:
	"""Return the full path for the sentiment analysis JSON file.

	If the log file is stored as `logs/<path>.json`, the analysis
	file will be `logs/<path_without_ext>_analysis.json`.
	"""

	base_log_path = os.path.join(LOGS_FOLDER, log.path)
	root, ext = os.path.splitext(base_log_path)
	if not ext:
		ext = ".json"
	return f"{root}_analysis{ext}"


def _response_to_json(response: Any) -> Dict[str, Any]:
	"""Extract the JSON payload from an OpenAI JSON-mode response.

	We call the Chat Completions API with
	``response_format={"type": "json_object"}``, so ``message.content``
	is guaranteed to be a single JSON string. Here we simply load that
	string as JSON and surface a clear error if anything unexpected
	happens.
	"""

	try:
		choice = response.choices[0]
		msg = choice.message
		content = getattr(msg, "content", None)
		if not isinstance(content, str):
			# Fallback: rely on string conversion if SDK ever changes type.
			content = str(content)
		return json.loads(content)
	except Exception as exc:  # noqa: BLE001
		raise ValueError("Failed to parse sentiment analysis JSON from OpenAI response") from exc


def analyze_log_sentiment(log: Log) -> Dict[str, Any]:
	"""Run sentiment analysis on a `Log` and save the results.

	- If the AI sentiment analysis feature is disabled, this function
	  raises a `RuntimeError`.
	- On success, the parsed JSON result is written to disk and also
	  returned to the caller.
	"""

	if not sentiment_analysis_enabled():
		raise RuntimeError("Sentiment analysis is disabled in user settings.")

	system_prompt = _build_system_prompt()
	user_prompt = _build_user_prompt(log)

	response = send_prompt_to_openai(system=system_prompt, prompt=user_prompt)
	result_json = _response_to_json(response)

	analysis_path = _get_analysis_file_path(log)
	os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
	with open(analysis_path, "w", encoding="utf-8") as f:
		json.dump(result_json, f, indent=4)

	return result_json


__all__ = ["analyze_log_sentiment", "EMOTION_LABELS"]


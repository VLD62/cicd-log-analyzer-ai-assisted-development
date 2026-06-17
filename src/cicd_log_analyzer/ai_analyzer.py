from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .analyzer import AnalysisResult, Finding
from .rules import SEVERITY_SCORE


class AIAnalysisError(RuntimeError):
    """Raised when AI analysis fails or returns invalid output."""


@dataclass(frozen=True)
class AIConfig:
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    timeout_seconds: int = 30
    max_input_chars: int = 40000


def analyze_file_with_ai(path: str | Path, config: AIConfig) -> AnalysisResult:
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file does not exist: {log_path}")

    text = log_path.read_text(encoding="utf-8", errors="replace")
    return analyze_text_with_ai(text, source_file=str(log_path), config=config)


def analyze_text_with_ai(text: str, source_file: str, config: AIConfig) -> AnalysisResult:
    normalized_text = text if len(text) <= config.max_input_chars else text[: config.max_input_chars]
    findings_payload = _request_findings(normalized_text, config)

    findings: list[Finding] = []
    for item in findings_payload:
        findings.append(_finding_from_payload(item))

    findings.sort(key=lambda f: (-SEVERITY_SCORE.get(f.severity, 0), f.line_number, f.rule_id))
    total_lines = text.count("\n") + (1 if text else 0)
    return AnalysisResult(source_file=source_file, total_lines=total_lines, findings=findings)


def _request_findings(log_text: str, config: AIConfig) -> list[dict[str, Any]]:
    provider = config.provider.lower().strip()
    api_key = config.api_key or _api_key_from_env(provider)
    if not api_key:
        raise AIAnalysisError(f"Missing API key for provider '{provider}'")

    if provider == "openai":
        response_text = _call_openai(log_text, config, api_key)
    elif provider == "anthropic":
        response_text = _call_anthropic(log_text, config, api_key)
    else:
        raise AIAnalysisError(f"Unsupported AI provider: {config.provider}")

    try:
        payload = json.loads(_strip_json_fence(response_text))
    except json.JSONDecodeError as exc:
        raise AIAnalysisError("AI response is not valid JSON") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise AIAnalysisError("AI response must be a JSON object with a 'findings' array")
    return payload["findings"]


def _finding_from_payload(item: dict[str, Any]) -> Finding:
    if not isinstance(item, dict):
        raise AIAnalysisError("Each finding returned by AI must be an object")

    severity = str(item.get("severity", "")).lower().strip()
    if severity not in SEVERITY_SCORE:
        raise AIAnalysisError(f"Invalid severity from AI: {severity!r}")

    return Finding(
        rule_id=str(item.get("rule_id") or "AI_DETECTED"),
        category=str(item.get("category") or "AI / Unknown"),
        severity=severity,
        line_number=_safe_line_number(item.get("line_number")),
        line=str(item.get("line") or "").strip(),
        recommendation=str(item.get("recommendation") or "No recommendation provided."),
    )


def _safe_line_number(value: Any) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else 1
    except (TypeError, ValueError):
        return 1


def _api_key_from_env(provider: str) -> str | None:
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")
    return None


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _call_openai(log_text: str, config: AIConfig, api_key: str) -> str:
    prompt = _build_prompt(log_text)
    payload = {
        "model": config.model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": prompt},
        ],
    }
    data = _http_post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        {
            "Authorization": f"Bearer {api_key}",
        },
        timeout_seconds=config.timeout_seconds,
    )

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIAnalysisError("Unexpected response format from OpenAI") from exc


def _call_anthropic(log_text: str, config: AIConfig, api_key: str) -> str:
    prompt = _build_prompt(log_text)
    payload = {
        "model": config.model,
        "max_tokens": 2000,
        "temperature": 0,
        "system": _system_prompt(),
        "messages": [{"role": "user", "content": prompt}],
    }
    data = _http_post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout_seconds=config.timeout_seconds,
    )

    try:
        blocks = data["content"]
        for block in blocks:
            if block.get("type") == "text":
                return block["text"]
    except (KeyError, TypeError) as exc:
        raise AIAnalysisError("Unexpected response format from Anthropic") from exc
    raise AIAnalysisError("Anthropic response did not contain text content")


def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            **headers,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        raise AIAnalysisError(f"AI provider HTTP error {exc.code}: {details}") from exc
    except URLError as exc:
        raise AIAnalysisError(f"AI provider connection failed: {exc.reason}") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIAnalysisError("AI provider returned invalid JSON") from exc


def _system_prompt() -> str:
    return (
        "You are a CI/CD log analysis assistant. "
        "Return strictly JSON with this exact top-level shape: "
        '{"findings": [{"rule_id": "string", "category": "string", "severity": "low|medium|high", '
        '"line_number": 1, "line": "string", "recommendation": "string"}]}. '
        "Only include findings supported by the provided log text."
    )


def _build_prompt(log_text: str) -> str:
    return (
        "Analyze the following CI/CD log and find actionable failures. "
        "Prefer precision over recall. If there are no issues, return {\"findings\": []}.\n\n"
        "LOG START\n"
        f"{log_text}\n"
        "LOG END"
    )
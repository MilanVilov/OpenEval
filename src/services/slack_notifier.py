"""Slack notifier — builds Block Kit messages and POSTs them to webhooks.

Failures are logged but never raised; a broken webhook must not fail a run.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10.0


def resolve_webhook_url(schedule_override: str | None) -> str | None:
    """Return the effective webhook URL, or ``None`` if Slack is not configured."""
    if schedule_override:
        return schedule_override
    default = get_settings().slack_webhook_url
    return default or None


def build_run_url(run_id: str) -> str | None:
    """Return an absolute URL to the run detail page, or ``None`` if unset."""
    base = get_settings().app_base_url.rstrip("/")
    if not base:
        return None
    return f"{base}/runs/{run_id}"


def build_blocks(
    *,
    run: Any,
    schedule: Any,
    previous_run: Any | None,
) -> list[dict]:
    """Build a Slack Block Kit payload summarising a completed scheduled run."""
    summary: dict = run.summary or {}
    prev_summary: dict | None = previous_run.summary if previous_run else None

    accuracy = summary.get("accuracy")
    below_threshold = (
        schedule.min_accuracy is not None
        and isinstance(accuracy, (int, float))
        and accuracy < schedule.min_accuracy
    )
    header_emoji = "🚨" if below_threshold else "✅"
    header_text = f"{header_emoji} {schedule.name}"

    config_name = run.config.name if run.config else "—"
    dataset_name = run.dataset.name if run.dataset else "—"

    fields: list[dict] = []
    fields.append(_field("Accuracy", _format_percent(accuracy, prev_summary, "accuracy")))
    fields.append(_field("Avg Score", _format_score(summary, prev_summary)))
    fields.append(_field("Avg Latency", _format_latency(summary, prev_summary)))
    fields.append(_field(
        "Passed / Failed / Errors",
        f"{summary.get('passed', 0)} / {summary.get('failed', 0)} / {summary.get('errors', 0)}",
    ))

    context_lines = [f"*Config:* {config_name}    *Dataset:* {dataset_name}"]
    if below_threshold:
        context_lines.append(
            f"⚠️ Accuracy below threshold ({_percent(schedule.min_accuracy)})"
        )

    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": header_text}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(context_lines)},
        },
        {"type": "section", "fields": fields},
    ]

    run_url = build_run_url(run.id)
    if run_url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open run"},
                    "url": run_url,
                }
            ],
        })

    return blocks


async def send(webhook_url: str, blocks: list[dict]) -> bool:
    """POST a Block Kit payload to a Slack webhook. Returns ``True`` on success."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook_url, json={"blocks": blocks})
        if response.status_code >= 400:
            logger.warning(
                "Slack webhook responded %s: %s",
                response.status_code,
                response.text[:200],
            )
            return False
        return True
    except httpx.HTTPError as exc:
        logger.warning("Slack webhook request failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _field(label: str, value: str) -> dict:
    """Build a Slack Block Kit field entry."""
    return {"type": "mrkdwn", "text": f"*{label}*\n{value}"}


def _percent(value: float | None) -> str:
    """Render a 0-1 value as a whole-number percent, or em dash."""
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value * 100:.1f}%"


def _format_percent(value: float | None, prev: dict | None, key: str) -> str:
    """Render a percent with a delta if a previous value exists."""
    current = _percent(value)
    if prev is None or not isinstance(prev.get(key), (int, float)):
        return current
    delta = (value or 0) - prev[key]
    return f"{current} {_arrow(delta, unit='pp', scale=100)}"


def _format_score(summary: dict, prev: dict | None) -> str:
    """Render avg_score with a delta."""
    current = summary.get("avg_score")
    if not isinstance(current, (int, float)):
        return "—"
    text = f"{current:.3f}"
    if prev is None or not isinstance(prev.get("avg_score"), (int, float)):
        return text
    delta = current - prev["avg_score"]
    return f"{text} {_arrow(delta, unit='', scale=1, decimals=3)}"


def _format_latency(summary: dict, prev: dict | None) -> str:
    """Render avg_latency_ms with a delta (lower is better)."""
    current = summary.get("avg_latency_ms")
    if not isinstance(current, (int, float)):
        return "—"
    text = f"{int(current)} ms"
    if prev is None or not isinstance(prev.get("avg_latency_ms"), (int, float)):
        return text
    delta = current - prev["avg_latency_ms"]
    return f"{text} {_arrow(delta, unit='ms', scale=1, higher_is_better=False)}"


def _arrow(
    delta: float,
    *,
    unit: str,
    scale: float = 1,
    decimals: int = 1,
    higher_is_better: bool = True,
) -> str:
    """Return an arrow + signed delta string, e.g. ``▲ +2.1pp``."""
    scaled = delta * scale
    if abs(scaled) < 10 ** (-decimals) / 2:
        return "•"
    sign = "+" if scaled > 0 else "-"
    magnitude = f"{abs(scaled):.{decimals}f}".rstrip("0").rstrip(".")
    if not magnitude:
        magnitude = "0"
    improving = (delta > 0) == higher_is_better
    arrow = "▲" if delta > 0 else "▼"
    color = "🟢" if improving else "🔴"
    tail = f"{unit}" if unit else ""
    return f"{color} {arrow} {sign}{magnitude}{tail}"

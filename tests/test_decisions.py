"""Decisions endpoint routing, validation, and configuration persistence."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import AsyncOpenAI
from pydantic import ValidationError

from src.providers.openai import OpenAIProvider
from src.routers.schemas.configs import CreateConfigRequest

QUESTIONS = [{"type": "predicate", "name": "relevant", "instructions": "Is it relevant?"}]


async def test_decisions_uses_dedicated_endpoint_and_returns_answers() -> None:
    """Decisions must omit Responses settings and retain typed answers for grading."""
    client = AsyncMock()
    answers = [{"type": "predicate", "name": "relevant", "probability": 0.9}]
    client.post.return_value = {
        "id": "dec_test",
        "answers": answers,
        "usage": {"input_tokens": 12},
    }
    result = await OpenAIProvider(client=client).generate(
        model="gpt-6-luna",
        system_prompt="Use the support rubric.",
        user_input="Help me",
        decision_config={"questions": QUESTIONS},
        tools=["shell"],
        reasoning_config={"effort": "high"},
        response_format={"type": "json_object"},
        max_tokens=100,
        flex_enabled=True,
    )
    assert result.raw_request == {
        "model": "gpt-6-luna",
        "input": "Help me",
        "questions": [
            {
                **QUESTIONS[0],
                "instructions": "Use the support rubric.\n\nIs it relevant?",
            }
        ],
    }
    assert client.post.await_args.args == ("/decisions",)
    client.responses.create.assert_not_awaited()
    assert json.loads(result.text) == {"answers": answers}
    assert result.token_usage == {"input_tokens": 12, "output_tokens": 0}


@pytest.mark.parametrize(
    "question",
    [
        {
            "type": "choice",
            "name": "team",
            "instructions": "Pick a team",
            "choices": [
                {"value": "billing", "description": "Payment issues"},
                {"value": "support", "description": "Technical issues"},
            ],
        },
        {
            "type": "score",
            "name": "severity",
            "instructions": "Rate severity",
            "levels": [
                {"label": "Low", "description": "Cosmetic"},
                {"label": "High", "description": "Blocked"},
            ],
        },
    ],
)
def test_decision_config_accepts_documented_question_types(question: dict) -> None:
    """Question settings survive request validation without losing type-specific fields."""
    config = CreateConfigRequest(
        name="Decisions",
        system_prompt="",
        model="gpt-6-luna",
        decision_config={"questions": [question]},
    )
    assert config.model_dump()["decision_config"]["questions"] == [question]


@pytest.mark.parametrize(
    "questions",
    [
        [],
        [*QUESTIONS, *QUESTIONS],
        [{"type": "text", "name": "answer", "instructions": "Explain"}],
        [{"type": "choice", "name": "team", "instructions": "Pick", "choices": []}],
        [{"type": "score", "name": "rating", "instructions": "Rate", "levels": []}],
    ],
)
def test_invalid_decision_questions_are_rejected(questions: list) -> None:
    """Invalid Decisions settings fail locally before a paid request."""
    with pytest.raises(ValidationError):
        CreateConfigRequest(
            name="Decisions",
            system_prompt="",
            model="gpt-6-luna",
            decision_config={"questions": questions},
        )


def test_decisions_requires_questions() -> None:
    """Choosing the Decisions model requires its API-specific configuration."""
    with pytest.raises(ValidationError, match="questions"):
        CreateConfigRequest(name="Decisions", system_prompt="", model="gpt-6-luna")


async def test_decision_refusal_is_preserved() -> None:
    """A refusal remains visible instead of being converted into a successful answer."""
    client = AsyncMock()
    answers = [{"type": "refusal", "name": "relevant"}]
    client.post.return_value = {"answers": answers}
    result = await OpenAIProvider(client=client).generate(
        model="gpt-6-luna",
        system_prompt="",
        user_input="input",
        decision_config={"questions": QUESTIONS},
    )
    assert json.loads(result.text) == {"answers": answers}


async def test_decisions_generic_sdk_transport_sends_real_http_contract() -> None:
    """The installed SDK sends JSON to /v1/decisions without a generated Decisions resource."""
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "gpt-6-luna",
                "answers": [
                    {"type": "choice", "name": "relevant", "choice": True, "confidence": 0.9},
                ],
                "usage": {"input_tokens": 5, "output_tokens": 0},
            },
        )

    async with AsyncOpenAI(
        api_key="test-only",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle_request)),
    ) as sdk:
        result = await OpenAIProvider(client=sdk).generate(
            model="gpt-6-luna",
            system_prompt="",
            user_input="Hello",
            decision_config={
                "questions": [
                    {
                        "type": "choice",
                        "name": "relevant",
                        "instructions": "Is it relevant?",
                        "choices": [{"value": True}, {"value": "true"}],
                    }
                ]
            },
        )
    assert str(requests[0].url) == "https://api.openai.com/v1/decisions"
    assert json.loads(requests[0].content) == result.raw_request
    assert json.loads(result.text)["answers"][0]["choice"] is True


def test_decisions_rejects_numeric_choice_values() -> None:
    """The documented choice schema accepts only strings and booleans."""
    with pytest.raises(ValidationError):
        CreateConfigRequest(
            name="Decision",
            system_prompt="",
            model="gpt-6-luna",
            decision_config={
                "questions": [
                    {
                        "type": "choice",
                        "name": "number",
                        "instructions": "Pick",
                        "choices": [
                            {"value": 1},
                            {"value": 2},
                        ],
                    }
                ],
            },
        )

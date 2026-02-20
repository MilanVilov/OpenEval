"""AI-powered JSON schema generation route."""

import json
import logging

from fastapi import APIRouter, HTTPException

from open_eval.services.openai_client import get_openai_client
from open_eval.routers.schemas.generate_schema import (
    GenerateSchemaRequest,
    GenerateSchemaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate-schema", tags=["generate-schema"])

SCHEMA_GENERATION_PROMPT = """\
You are a JSON Schema generator. Given a user description, produce a valid JSON Schema \
that can be used with OpenAI's structured output (strict mode).

Rules:
- Output ONLY valid JSON — no markdown, no explanation, no code fences.
- The root must be {"type": "object", "properties": {...}, "required": [...], "additionalProperties": false}.
- Every object in the schema must have "additionalProperties": false.
- Use standard JSON Schema types: string, number, integer, boolean, array, object, null.
- For enums use {"type": "string", "enum": [...]}.
- Keep it minimal but complete for the described use-case.
"""


@router.post("", response_model=GenerateSchemaResponse)
async def generate_schema(body: GenerateSchemaRequest) -> GenerateSchemaResponse:
    """Use AI to generate a JSON schema from a natural-language description."""
    if not body.description.strip():
        raise HTTPException(status_code=400, detail="Description must not be empty")

    client = get_openai_client()

    try:
        response = await client.responses.create(
            model="gpt-5.2",
            instructions=SCHEMA_GENERATION_PROMPT,
            input=body.description,
            reasoning={"effort": "low"},
        )

        raw_text = response.output_text.strip()

        # Strip markdown code fences if the model included them
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(lines).strip()

        schema_body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("AI returned invalid JSON: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=f"AI generated invalid JSON: {exc}",
        )
    except Exception as exc:
        logger.exception("Schema generation failed")
        raise HTTPException(
            status_code=502,
            detail=f"Schema generation failed: {exc}",
        )

    # Derive a schema name from the description (first few words, snake_cased)
    words = body.description.strip().split()[:3]
    schema_name = "_".join(w.lower() for w in words if w.isalnum())

    return GenerateSchemaResponse(
        schema_name=schema_name or "response",
        schema_body=schema_body,
    )

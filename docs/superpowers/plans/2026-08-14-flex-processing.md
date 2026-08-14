# Flex Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow an evaluation configuration to opt compatible OpenAI Responses requests into Flex processing.

**Architecture:** Store `flex_enabled` with `EvalConfig`, return it from the config API, and pass it through the existing primary-run, prompt-grader, and Playground Responses call paths. Embeddings stay unchanged because their endpoint has no `service_tier` parameter.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy/Alembic, pytest, React 18, TypeScript, Tailwind.

## Global Constraints

- `flex_enabled` defaults to `false` for existing and new configurations.
- Send `service_tier="flex"` only for Responses calls when `flex_enabled` is true.
- Do not use a model allowlist or send Flex to embeddings, vector stores, or containers.

---

### Task 1: Persist and return the config setting

**Files:**

- Create: `alembic/versions/022_add_eval_config_flex_enabled.py`
- Modify: `src/db/models.py`, `src/routers/schemas/configs.py`, `src/routers/configs.py`
- Test: `tests/test_config.py`, `tests/test_alembic_migrations.py`

**Interfaces:** Produces `EvalConfig.flex_enabled: bool`, `CreateConfigRequest.flex_enabled: bool = False`, `UpdateConfigRequest.flex_enabled: bool | None`, and `ConfigResponse.flex_enabled: bool`.

- [ ] **Step 1: Write failing API and migration tests**

```python
async def test_create_config_flex_enabled_is_returned(client):
    response = await client.post("/api/configs", json={**valid_config, "flex_enabled": True})
    assert response.status_code == 201
    assert response.json()["flex_enabled"] is True
```

Add a migration assertion that the column is non-null and defaults to false for existing rows.

- [ ] **Step 2: Run the new tests and verify they fail because the field and migration do not exist.**

Run: `uv run pytest tests/test_config.py tests/test_alembic_migrations.py -q`

- [ ] **Step 3: Add the minimal model, migration, schema, creation, and response changes.**

Use `sa.Boolean()`, `server_default=sa.false()`, and `nullable=False` in the migration. Forward the field in `_config_to_response` and config creation.

- [ ] **Step 4: Run the same tests and verify they pass.**

### Task 2: Apply Flex to Responses API execution paths

**Files:**

- Modify: `src/providers/openai.py`, `src/services/eval_client.py`, `src/services/eval_runner.py`, `src/comparers/custom_grader.py`, `src/routers/playground.py`
- Test: `tests/test_openai_provider.py`, `tests/test_eval_runner.py`, `tests/comparers/test_custom_grader.py`, `tests/test_app_module.py`

**Interfaces:** Extends `OpenAIProvider.generate(..., flex_enabled: bool = False)` and `call_llm(..., flex_enabled: bool = False)`. Prompt-grader config receives `flex_enabled` from the runner.

- [ ] **Step 1: Write failing propagation tests.**

```python
await provider.generate(system_prompt="test", user_input="input", model="gpt-4.1", flex_enabled=True)
assert captured_kwargs["service_tier"] == "flex"
```

Also verify absence when disabled; runner propagation; a prompt grader's `responses.create` kwargs; and Playground's provider kwargs.

- [ ] **Step 2: Run focused tests and verify the failures are due to missing Flex parameters.**

Run: `uv run pytest tests/test_openai_provider.py tests/test_eval_runner.py tests/comparers/test_custom_grader.py tests/test_app_module.py -q`

- [ ] **Step 3: Implement the minimal propagation.**

Add `kwargs["service_tier"] = "flex"` only when enabled. Thread the flag from `EvalConfig` to the primary call, custom prompt grader, and Playground. Do not change semantic-similarity embeddings.

- [ ] **Step 4: Run the focused tests and verify they pass.**

### Task 3: Expose Flex in configuration forms

**Files:**

- Modify: `frontend/src/types/config.ts`, `frontend/src/pages/configs/ConfigNew.tsx`, `frontend/src/pages/configs/ConfigEdit.tsx`

**Interfaces:** `EvalConfig` and `CreateConfigRequest` define `flex_enabled: boolean`; both forms submit checkbox state under that property.

- [ ] **Step 1: Add the new frontend field and run the strict build to observe the missing form integration.**

Run: `npm run build`

- [ ] **Step 2: Add minimal form integration.**

Add `flexEnabled` state initialized to `false`, load it in edit mode, include it in both submit payloads, and add a disabled-aware checkbox labelled `Use Flex processing` below model selection. Explain that compatible config requests use lower-cost Flex processing and can take longer.

- [ ] **Step 3: Run the frontend build and verify it passes.**

Run: `npm run build`

### Task 4: Verify and commit

- [ ] **Step 1: Run focused verification.**

Run: `uv run pytest tests/test_config.py tests/test_alembic_migrations.py tests/test_openai_provider.py tests/test_eval_runner.py tests/comparers/test_custom_grader.py tests/test_app_module.py -q && npm run build`

- [ ] **Step 2: Run the full backend suite.**

Run: `uv run pytest -q`

- [ ] **Step 3: Inspect `git diff --check`, review the diff, and commit with `feat(openai): add flex processing to eval configs`.**

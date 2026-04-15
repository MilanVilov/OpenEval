# OpenEval

An open-source AI prompt & tool evaluation framework. Configure prompts, models, and tools (including OpenAI file_search and code_interpreter), upload evaluation datasets as CSV, run evaluations with parallel execution, and compare results with pluggable comparers.

## Features

- **Eval Configuration** — Define system prompts, model settings, tools, and comparers
- **Dataset Management** — Upload CSV datasets with input/expected_output columns
- **Vector Store Management** — Create and manage OpenAI vector stores for file_search
- **Parallel Evaluation** — Run evals with configurable concurrency via asyncio
- **6 Built-in Comparers** — exact_match, pattern_match, json_schema_match, json_field_match, semantic_similarity, llm_judge
- **Plugin System** — Add custom comparers via Python entry points
- **Live Progress** — Real-time progress tracking with polling
- **Run Comparison** — Side-by-side comparison of two evaluation runs
- **Dark UI** — Cursor Dark Midnight theme with responsive layout

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy (async), SQLite, Alembic
- **Frontend**: React 19 (Vite + TypeScript) + Tailwind CSS
- **AI**: OpenAI Responses API
- **Package Manager**: uv
- **Container**: Docker (multi-stage build with Node.js + Python)

## Quick Start

### Docker (recommended)

```bash
# Clone the repo
git clone https://github.com/your-org/OpenEval.git
cd OpenEval

# Copy env file and add your OpenAI API key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# If using Colima (macOS without Docker Desktop):
colima start

# Build and run
docker build -t openeval .
docker run -p 8000:8000 --env-file .env openeval

# Or with docker-compose (if available):
docker-compose up --build
```

Open http://localhost:8000

### Local Development

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set environment variables
export OPENAI_API_KEY=sk-...
export DATABASE_URL=sqlite+aiosqlite:///data/open_eval.db

# Run database migrations
mkdir -p data
uv run alembic upgrade head

# Start the backend dev server
uv run uvicorn src.app:create_app --factory --reload --host 0.0.0.0 --port 8000

# In a separate terminal, start the React frontend dev server
cd frontend
npm install
npm run dev
# Frontend runs at http://localhost:5173 with API proxy to :8000
```

## Usage

1. **Create an Eval Config** — Go to Eval Configs → New Config. Set a name, system prompt, model, tools, and comparer.
2. **Upload a Dataset** — Go to Datasets → Upload. CSV must have `input` and `expected_output` columns.
3. **Run an Evaluation** — Go to Eval Runs → New Run. Select a config and dataset, then start.
4. **View Results** — Watch live progress, then review results with pass/fail badges and scores.
5. **Compare Runs** — Go to Eval Runs → Compare to see two runs side by side.

## Sample Files

The `misc/` directory contains example files you can use to explore the platform:

- **sample-prompt.md** — An example classification system prompt
- **sample-schema.json** — JSON schema for structured response format
- **sample-dataset.csv** — A small evaluation dataset (CSV) with golden test cases

Upload the CSV file as a dataset and use the prompt/schema to create an eval config to see OpenEval in action.

## CSV Format

```csv
input,expected_output
"What is 2+2?","4"
"Capital of France?","Paris"
```

Required columns: `input`, `expected_output`. Additional columns are preserved but not used by the evaluator.

## Custom Comparers

Create a Python package with a class inheriting from `BaseComparer`:

```python
from src.comparers.base import BaseComparer, register_comparer

@register_comparer("my_comparer")
class MyComparer(BaseComparer):
    async def compare(self, *, expected: str, actual: str) -> tuple[float, bool, dict]:
        # Your comparison logic
        score = 1.0 if expected == actual else 0.0
        return score, score >= 0.5, {"detail": "..."}
```

Register via entry point in your package's `pyproject.toml`:

```toml
[project.entry-points."open_eval.comparers"]
my_comparer = "my_package.comparers:MyComparer"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/open_eval.db` | Database connection URL |
| `UPLOAD_DIR` | `data/uploads` | Directory for uploaded files |
| `DEFAULT_CONCURRENCY` | `5` | Default parallel eval workers |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

## Project Structure

```
openeval/
├── src/
│   ├── app.py              # FastAPI app factory
│   ├── config.py           # Pydantic Settings
│   ├── comparers/          # Comparer framework + 5 built-in
│   ├── db/                 # Models, session, repositories
│   ├── providers/          # LLM provider abstraction
│   ├── routers/            # FastAPI route handlers
│   └── services/           # CSV parser, eval runner, OpenAI client
├── frontend/               # React SPA (Vite + TypeScript + Tailwind)
├── alembic/                # Database migrations
├── tests/                  # Test suite
├── Dockerfile
└── docker-compose.yml
```

## License

OSASSY License. See [LICENSE](LICENSE) for details.
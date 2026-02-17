# Skill: Git Workflow — Commits, Branches, and PRs

This skill defines version control conventions for ai-eval. Follow these rules for all commits, branches, and pull requests.

---

## Commit Messages

Use **Conventional Commits** format:

```
<type>(<scope>): <description>

[optional body]
```

### Types

| Type | When to use |
|---|---|
| `feat` | New feature or functionality |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `docs` | Documentation changes (README, PRD, skills, docstrings) |
| `test` | Adding or updating tests |
| `chore` | Build, CI, dependencies, tooling |
| `style` | Formatting, whitespace (no logic change) |

### Scopes

Use the module or area affected:

| Scope | Covers |
|---|---|
| `comparers` | Comparer base, registry, built-in comparers |
| `runner` | Eval runner, execution engine |
| `openai` | OpenAI client, provider, vector store service |
| `db` | Models, repositories, migrations |
| `api` | Routers, endpoints |
| `ui` | Templates, CSS, static assets |
| `config` | Settings, env vars |
| `docker` | Dockerfile, docker-compose |

### Examples

```
feat(comparers): add LLM-as-judge comparer
fix(runner): prevent duplicate results on retry
refactor(db): extract vector store repository from monolith
docs: update PRD with vector store management section
test(comparers): add tests for semantic similarity threshold
chore(docker): pin Python base image to 3.12.8-slim
```

### Rules

- **Subject line**: imperative mood ("add", not "added" or "adds"), max 72 characters.
- **No period** at the end of the subject line.
- **Body** (optional): explain *why*, not *what*. The diff shows what changed.
- **One logical change per commit.** Don't mix a feature with a refactor.

---

## Branch Naming

```
<type>/<short-description>
```

### Examples

```
feat/llm-judge-comparer
fix/csv-upload-encoding
refactor/split-repositories
chore/ci-docker-build
docs/contributing-guide
```

### Rules

- Lowercase, hyphens for spaces.
- Max 50 characters.
- Branch from `main`, merge back to `main`.
- Delete branch after merge.

---

## Branch Strategy

Simple **trunk-based development**:

- `main` is always deployable.
- Short-lived feature branches (1–3 days max).
- No `develop` branch, no `release/*` branches, no git-flow.
- Rebase feature branches on `main` before merging to keep history linear.

```
main ─────●─────●─────●─────●─────●
           \         /
            feat/xxx ●───●
```

---

## Pull Requests

### Title

Same format as commit messages:

```
feat(comparers): add LLM-as-judge comparer
```

### Description

```markdown
## What

Brief description of what changed and why.

## How

Key implementation decisions or trade-offs.

## Testing

How this was tested (manual, unit tests, etc.).
```

### Rules

- **One concern per PR.** Don't mix features.
- **Small PRs** — under 400 lines changed. Split large work into stacked PRs.
- **All tests pass** before requesting review.
- **Self-review first** — read your own diff before asking others.
- **Squash merge** into main to keep history clean.

---

## .gitignore Essentials

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# App data (never commit)
data/
*.db
uploads/

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

### Rules

- **Never commit secrets** (`.env`, API keys).
- **Never commit app data** (SQLite databases, uploaded files).
- **Never commit IDE settings** unless the team explicitly agrees.

---

## Do's and Don'ts

### Do

- Write meaningful commit messages that explain intent.
- Keep branches short-lived — merge within 1–3 days.
- Rebase on main before merging.
- Delete branches after merge.
- Use `git add -p` to stage intentional changes only.

### Don't

- Don't commit half-finished work to main.
- Don't use `git add .` without reviewing what's staged.
- Don't force-push to main.
- Don't create branches that live for weeks.
- Don't put merge commits in the main branch — squash merge.

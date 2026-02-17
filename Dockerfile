FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml .
COPY README.md .

# Install dependencies
RUN uv pip install --system --no-cache .

# Copy application code
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY alembic/ alembic/
COPY alembic.ini .

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create data directory
RUN mkdir -p /app/data/uploads

VOLUME /app/data
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

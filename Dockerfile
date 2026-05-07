# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files and source
COPY app/ app/
COPY pyproject.toml .
COPY README.md .
COPY src/ src/

# Install package and dependencies
RUN uv pip install --system --no-cache .

# Copy remaining files
COPY alembic/ alembic/
COPY alembic.ini .

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create data directory
RUN mkdir -p /app/data/uploads

VOLUME /app/data
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

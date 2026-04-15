"""OpenAI API client service."""

import httpx

from openai import AsyncOpenAI

from src.config import get_settings


def get_openai_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client."""
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.openai_api_key)


# ---------------------------------------------------------------------------
# Containers (Shell tool)
# ---------------------------------------------------------------------------


async def create_container(name: str, expires_after_minutes: int = 20) -> dict:
    """Create a new container in OpenAI for the shell tool.

    Uses the Containers API: POST /v1/containers
    Returns dict with keys: id, name, status.

    Args:
        name: Display name for the container.
        expires_after_minutes: Idle timeout in minutes (1-20). The timer
            resets each time the container is used.
    """
    settings = get_settings()
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://api.openai.com/v1/containers",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "name": name,
                "expires_after": {
                    "anchor": "last_active_at",
                    "minutes": expires_after_minutes,
                },
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    return {"id": data["id"], "name": data.get("name", name), "status": data.get("status", "active")}


async def delete_container(openai_container_id: str) -> bool:
    """Delete a container from OpenAI. Returns True on success."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.delete(
                f"https://api.openai.com/v1/containers/{openai_container_id}",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                timeout=30.0,
            )
            resp.raise_for_status()
        return True
    except Exception:
        return False


async def upload_file_to_container(openai_container_id: str, file_path: str, file_name: str) -> dict:
    """Upload a file to an OpenAI container.

    Uses the Containers Files API: POST /v1/containers/{container_id}/files
    Returns dict with keys: file_id, status.
    """
    settings = get_settings()
    async with httpx.AsyncClient() as http:
        with open(file_path, "rb") as f:
            resp = await http.post(
                f"https://api.openai.com/v1/containers/{openai_container_id}/files",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                },
                files={"file": (file_name, f)},
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
    return {"file_id": data.get("id", ""), "status": data.get("status", "completed")}


async def get_container_info(openai_container_id: str) -> dict:
    """Fetch current container metadata from OpenAI.

    Returns dict with keys: id, name, status.
    """
    settings = get_settings()
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"https://api.openai.com/v1/containers/{openai_container_id}",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "status": data.get("status", "active"),
    }


async def list_container_files(openai_container_id: str) -> list[dict]:
    """List files in an OpenAI container.

    Returns list of dicts with keys: id, path.
    """
    settings = get_settings()
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"https://api.openai.com/v1/containers/{openai_container_id}/files",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    files = data.get("data", [])
    return [{"id": f.get("id", ""), "path": f.get("path", "")} for f in files]


# ---------------------------------------------------------------------------
# Vector Stores
# ---------------------------------------------------------------------------


async def create_vector_store(name: str) -> dict:
    """Create a new vector store in OpenAI.

    Uses the Vector Stores API: POST /v1/vector_stores
    Returns dict with keys: id, name, status.
    """
    client = get_openai_client()
    store = await client.vector_stores.create(name=name)
    return {"id": store.id, "name": store.name, "status": store.status}


async def delete_vector_store(openai_store_id: str) -> bool:
    """Delete a vector store from OpenAI. Returns True on success."""
    client = get_openai_client()
    try:
        await client.vector_stores.delete(openai_store_id)
        return True
    except Exception:
        return False


async def upload_file_to_vector_store(openai_store_id: str, file_path: str, file_name: str) -> dict:
    """Upload a file to an OpenAI vector store.

    Uses the combined upload_and_poll method which uploads the file and
    adds it to the vector store in a single call, then polls until
    processing is complete.

    Returns dict with keys: file_id, status.
    """
    client = get_openai_client()
    with open(file_path, "rb") as f:
        vs_file = await client.vector_stores.files.upload_and_poll(
            vector_store_id=openai_store_id,
            file=f,
        )
    return {"file_id": vs_file.id, "status": vs_file.status}


async def get_vector_store_info(openai_store_id: str) -> dict:
    """Fetch current vector store metadata from OpenAI.

    Uses the Vector Stores API: GET /v1/vector_stores/{vector_store_id}
    Returns dict with keys: id, name, status, file_counts.
    """
    client = get_openai_client()
    store = await client.vector_stores.retrieve(openai_store_id)
    return {
        "id": store.id,
        "name": store.name,
        "status": store.status,
        "file_counts": store.file_counts.completed if store.file_counts else 0,
    }


async def list_openai_vector_stores() -> list[dict]:
    """List vector stores from OpenAI API.

    Returns list of dicts with keys: id, name, status, file_counts.
    """
    client = get_openai_client()
    result = await client.vector_stores.list(limit=100)
    stores = []
    for store in result.data:
        stores.append({
            "id": store.id,
            "name": store.name,
            "status": store.status,
            "file_counts": store.file_counts.completed if store.file_counts else 0,
        })
    return stores

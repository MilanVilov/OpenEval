"""OpenAI API client service."""

from openai import AsyncOpenAI

from ai_eval.config import get_settings


def get_openai_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client."""
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def create_vector_store(name: str) -> dict:
    """Create a new vector store in OpenAI.

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

    Returns dict with keys: file_id, status.
    """
    client = get_openai_client()
    with open(file_path, "rb") as f:
        file_obj = await client.files.create(file=f, purpose="assistants")

    vs_file = await client.vector_stores.files.create(
        vector_store_id=openai_store_id,
        file_id=file_obj.id,
    )
    return {"file_id": vs_file.id, "status": vs_file.status}


async def get_vector_store_info(openai_store_id: str) -> dict:
    """Fetch current vector store metadata from OpenAI.

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

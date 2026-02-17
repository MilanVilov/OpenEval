"""EvalConfig CRUD routes."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.app import templates
from ai_eval.db.repositories import ConfigRepository, VectorStoreRepository
from ai_eval.db.session import get_session

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("", response_class=HTMLResponse)
async def list_configs(request: Request, session: AsyncSession = Depends(get_session)):
    """List all evaluation configurations."""
    configs = await ConfigRepository(session).list_all()
    return templates.TemplateResponse(
        "configs/list.html",
        {"request": request, "active_page": "configs", "configs": configs},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_config(request: Request, session: AsyncSession = Depends(get_session)):
    """Render the create-config form."""
    vector_stores = await VectorStoreRepository(session).list_all()
    return templates.TemplateResponse(
        "configs/new.html",
        {"request": request, "active_page": "configs", "vector_stores": vector_stores},
    )


@router.post("", response_class=HTMLResponse)
async def create_config(
    request: Request,
    session: AsyncSession = Depends(get_session),
    name: str = Form(...),
    system_prompt: str = Form(...),
    model: str = Form("gpt-4o"),
    temperature: float = Form(0.7),
    max_tokens: str = Form(""),
    comparer_type: str = Form(...),
    comparer_config_threshold: str = Form(""),
    concurrency: int = Form(5),
    vector_store_id: str = Form(""),
):
    """Create a new evaluation configuration."""
    form_data = await request.form()
    tools = form_data.getlist("tools")

    tool_options: dict = {}
    if "file_search" in tools and vector_store_id:
        tool_options["vector_store_id"] = vector_store_id

    comparer_config: dict = {}
    if comparer_config_threshold:
        comparer_config["threshold"] = float(comparer_config_threshold)

    config = await ConfigRepository(session).create(
        name=name,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=int(max_tokens) if max_tokens else None,
        tools=list(tools),
        tool_options=tool_options,
        comparer_type=comparer_type,
        comparer_config=comparer_config,
        concurrency=concurrency,
    )
    return RedirectResponse(f"/configs/{config.id}", status_code=303)


@router.get("/{config_id}", response_class=HTMLResponse)
async def detail_config(
    config_id: str, request: Request, session: AsyncSession = Depends(get_session),
):
    """Show a single evaluation configuration."""
    config = await ConfigRepository(session).get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return templates.TemplateResponse(
        "configs/detail.html",
        {"request": request, "active_page": "configs", "config": config},
    )


@router.get("/{config_id}/edit", response_class=HTMLResponse)
async def edit_config_form(
    config_id: str, request: Request, session: AsyncSession = Depends(get_session),
):
    """Render the edit-config form."""
    config = await ConfigRepository(session).get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    vector_stores = await VectorStoreRepository(session).list_all()
    return templates.TemplateResponse(
        "configs/edit.html",
        {"request": request, "active_page": "configs", "config": config, "vector_stores": vector_stores},
    )


@router.post("/{config_id}", response_class=HTMLResponse)
async def update_config(
    config_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    name: str = Form(...),
    system_prompt: str = Form(...),
    model: str = Form("gpt-4o"),
    temperature: float = Form(0.7),
    max_tokens: str = Form(""),
    comparer_type: str = Form(...),
    comparer_config_threshold: str = Form(""),
    concurrency: int = Form(5),
    vector_store_id: str = Form(""),
):
    """Update an existing evaluation configuration."""
    form_data = await request.form()
    tools = form_data.getlist("tools")

    tool_options: dict = {}
    if "file_search" in tools and vector_store_id:
        tool_options["vector_store_id"] = vector_store_id

    comparer_config: dict = {}
    if comparer_config_threshold:
        comparer_config["threshold"] = float(comparer_config_threshold)

    repo = ConfigRepository(session)
    config = await repo.update(
        config_id,
        name=name,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=int(max_tokens) if max_tokens else None,
        tools=list(tools),
        tool_options=tool_options,
        comparer_type=comparer_type,
        comparer_config=comparer_config,
        concurrency=concurrency,
    )
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return RedirectResponse(f"/configs/{config.id}", status_code=303)


@router.delete("/{config_id}")
async def delete_config(
    config_id: str, session: AsyncSession = Depends(get_session),
):
    """Delete an evaluation configuration."""
    deleted = await ConfigRepository(session).delete(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return Response(status_code=200, headers={"HX-Redirect": "/configs"})

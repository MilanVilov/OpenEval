"""Comparer registry — resolves comparer names to instances."""

import importlib.metadata
import logging

from open_eval.comparers.base import BaseComparer, _COMPARER_REGISTRY

logger = logging.getLogger(__name__)

_entry_points_loaded = False


def _load_entry_points() -> None:
    """Discover and load comparers registered as Python entry points."""
    global _entry_points_loaded
    if _entry_points_loaded:
        return
    _entry_points_loaded = True

    try:
        eps = importlib.metadata.entry_points(group="open_eval.comparers")
    except Exception:
        return

    for ep in eps:
        if ep.name not in _COMPARER_REGISTRY:
            try:
                cls = ep.load()
                _COMPARER_REGISTRY[ep.name] = cls
                logger.debug("Loaded comparer entry point: %s", ep.name)
            except Exception:
                logger.warning("Failed to load comparer entry point: %s", ep.name, exc_info=True)


def get_comparer(name: str, config: dict | None = None) -> BaseComparer:
    """Return a comparer instance by name.

    Checks the decorator registry first, then entry points.
    Raises ValueError if the comparer is not found.
    """
    # Ensure built-in comparers are imported (trigger @register_comparer)
    _ensure_builtins_imported()
    _load_entry_points()

    cls = _COMPARER_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(_COMPARER_REGISTRY.keys()))
        raise ValueError(f"Unknown comparer: {name!r}. Available: {available}")
    return cls(config)


def list_comparers() -> list[str]:
    """Return sorted list of registered comparer names."""
    _ensure_builtins_imported()
    _load_entry_points()
    return sorted(_COMPARER_REGISTRY.keys())


def _ensure_builtins_imported() -> None:
    """Import built-in comparer modules to trigger registration."""
    import open_eval.comparers.exact_match  # noqa: F401
    import open_eval.comparers.pattern_match  # noqa: F401
    import open_eval.comparers.semantic_similarity  # noqa: F401
    import open_eval.comparers.llm_judge  # noqa: F401
    import open_eval.comparers.json_schema_match  # noqa: F401
    import open_eval.comparers.contact_reason  # noqa: F401

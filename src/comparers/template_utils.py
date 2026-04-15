"""Template rendering utility for grader variable substitution.

Resolves Jinja-style ``{{ item.field }}`` placeholders by traversing a
nested dict context.  Only simple dot-separated paths are supported
(e.g. ``{{ item.input }}`` or ``{{ sample.output_text }}``).
"""

import re

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([\w]+(?:\.[\w]+)*)\s*\}\}")


def render_template(template: str, context: dict) -> str:
    """Replace ``{{ path.to.value }}`` tokens with values from *context*.

    Args:
        template: String containing ``{{ var.field }}`` placeholders.
        context: Nested dict used for lookups (e.g. ``{"item": {...}, "sample": {...}}``).

    Returns:
        The rendered string.  Unresolvable placeholders are left as-is.
    """

    def _resolve(match: re.Match) -> str:
        path = match.group(1).split(".")
        obj: object = context
        for part in path:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return match.group(0)  # leave unresolved
        return str(obj)

    return _PLACEHOLDER_RE.sub(_resolve, template)

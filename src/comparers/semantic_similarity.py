"""Semantic similarity comparer — cosine similarity via OpenAI embeddings."""

import math

from src.comparers.base import BaseComparer, register_comparer


@register_comparer("semantic_similarity")
class SemanticSimilarityComparer(BaseComparer):
    """Compare outputs using cosine similarity of OpenAI embeddings.

    Config options:
        threshold (float): Minimum similarity for a pass. Default 0.8.
        model (str): Embedding model to use. Default "text-embedding-3-small".
    """

    async def compare(self, *, expected: str, actual: str, row_data: dict | None = None) -> tuple[float, bool, dict]:
        """Return cosine similarity score and pass/fail based on threshold."""
        from src.services.openai_client import get_openai_client

        threshold = self.config.get("threshold", 0.8)
        model = self.config.get("model", "text-embedding-3-small")

        client = get_openai_client()
        response = await client.embeddings.create(
            input=[expected, actual],
            model=model,
        )

        vec_expected = response.data[0].embedding
        vec_actual = response.data[1].embedding

        score = self._cosine_similarity(vec_expected, vec_actual)
        passed = score >= threshold
        return score, passed, {"threshold": threshold, "model": model}

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return round(dot / (norm_a * norm_b), 4)

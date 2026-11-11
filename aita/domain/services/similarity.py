"""Similitud entre embeddings. La usa el emparejamiento semántico mock."""

import math
from collections.abc import Sequence

from aita.domain.exceptions import DomainValidationError


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Devuelve la similitud coseno en el rango [-1, 1]."""

    if not left or not right:
        raise DomainValidationError("Los embeddings no pueden estar vacíos.")
    if len(left) != len(right):
        raise DomainValidationError("Los embeddings deben tener la misma dimensión.")

    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(value * value for value in left))
    norm_right = math.sqrt(sum(value * value for value in right))
    if norm_left == 0 or norm_right == 0:
        raise DomainValidationError("Un embedding nulo no tiene similitud definida.")
    return dot / (norm_left * norm_right)

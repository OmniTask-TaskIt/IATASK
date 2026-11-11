"""Adaptador en memoria para búsqueda vectorial (mock de base de datos vectorial)."""

import asyncio
from typing import NamedTuple

from aita.domain.exceptions import DomainValidationError
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import VectorHit
from aita.domain.models.task import TaskText
from aita.domain.ports.outbound import IVectorSearchPort
from aita.domain.services.similarity import cosine_similarity


class ProviderEntry(NamedTuple):
    profile: ProviderProfile
    embedding: list[float]


class TaskEntry(NamedTuple):
    task: TaskText
    embedding: list[float]


class InMemoryVectorSearchAdapter(IVectorSearchPort):
    """Almacén vectorial en memoria seguro para concurrencia."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderEntry] = {}
        self._tasks: dict[str, TaskEntry] = {}
        self._lock = asyncio.Lock()

    async def upsert_task(self, task: TaskText, embedding: list[float]) -> None:
        async with self._lock:
            self._tasks[task.task_id] = TaskEntry(task=task, embedding=embedding)

    async def upsert_provider(self, profile: ProviderProfile, embedding: list[float]) -> None:
        async with self._lock:
            self._providers[profile.provider_id] = ProviderEntry(profile=profile, embedding=embedding)

    async def search_providers(self, embedding: list[float], limit: int) -> list[VectorHit]:
        async with self._lock:
            entries = list(self._providers.values())

        if not entries:
            return []

        hits: list[VectorHit] = []
        for entry in entries:
            try:
                score = cosine_similarity(embedding, entry.embedding)
            except DomainValidationError:
                score = 0.0

            # Limitar score al rango [-1.0, 1.0]
            clamped_score = max(-1.0, min(1.0, round(score, 4)))
            hits.append(
                VectorHit(
                    provider_id=entry.profile.provider_id,
                    score=clamped_score,
                    display_name=entry.profile.display_name,
                )
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]


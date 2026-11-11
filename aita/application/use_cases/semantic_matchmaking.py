"""Indexado y búsqueda semántica de prestadores."""

from aita.application.audit import audit
from aita.application.support import run_ai
from aita.domain.models.commands import SemanticMatchCommand
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import MatchResult, VectorHit
from aita.domain.models.task import TaskText
from aita.domain.ports.inbound import ISemanticMatchmakingUseCase
from aita.domain.ports.outbound import IAiModelPort, IVectorSearchPort


def task_document(task_name: str, task_description: str, category: str) -> str:
    return f"{task_name}\n{task_description}\n{category}"


def profile_document(profile: ProviderProfile) -> str:
    skills = ", ".join(profile.skills)
    categories = ", ".join(category.value for category in profile.categories)
    return f"{profile.display_name}\n{profile.bio}\n{skills}\n{profile.location}\n{categories}"


class SemanticMatchmakingUseCase(ISemanticMatchmakingUseCase):
    def __init__(self, ai: IAiModelPort, vectors: IVectorSearchPort) -> None:
        self._ai = ai
        self._vectors = vectors

    async def index_task(self, task: TaskText) -> None:
        audit("AI-MATCH", f"Indexado de tarea ID: {task.task_id}")
        embedding = await run_ai(
            "AI-MATCH",
            f"embedding de tarea {task.task_id}",
            lambda: self._ai.embed(
                task_document(task.task_name, task.task_description, task.category.value)
            ),
        )
        await self._vectors.upsert_task(task, embedding)  # type: ignore[arg-type]

    async def index_provider(self, profile: ProviderProfile) -> None:
        audit("AI-MATCH", f"Indexado de prestador ID: {profile.provider_id}")
        embedding = await run_ai(
            "AI-MATCH",
            f"embedding de prestador {profile.provider_id}",
            lambda: self._ai.embed(profile_document(profile)),
        )
        await self._vectors.upsert_provider(profile, embedding)  # type: ignore[arg-type]

    async def match(self, command: SemanticMatchCommand) -> list[MatchResult]:
        audit("AI-MATCH", f"Búsqueda de prestadores para tarea ID: {command.task_id}")
        embedding = await run_ai(
            "AI-MATCH",
            f"búsqueda semántica de tarea {command.task_id}",
            lambda: self._ai.embed(
                task_document(command.task_name, command.task_description, command.category.value)
            ),
        )
        hits = await self._vectors.search_providers(embedding, command.limit)  # type: ignore[arg-type]
        ordered = sorted(hits, key=lambda hit: hit.score, reverse=True)[: command.limit]
        if not ordered:
            audit("AI-MATCH", f"Sin coincidencias para tarea ID: {command.task_id}")
        return [self._to_match(command.task_id, hit) for hit in ordered]

    @staticmethod
    def _to_match(task_id: str, hit: VectorHit) -> MatchResult:
        name = hit.display_name or hit.provider_id
        return MatchResult(
            task_id=task_id,
            provider_id=hit.provider_id,
            score=hit.score,
            rationale=f"Similitud coseno {hit.score:.2f} con {name}.",
        )

"""Redacción asistida de una tarea a partir de una idea corta."""

from aita.application.audit import audit
from aita.application.support import run_ai
from aita.domain.models.commands import GenerateTaskDescriptionCommand
from aita.domain.models.results import GeneratedTaskContent
from aita.domain.ports.inbound import IGenerateTaskDescriptionUseCase
from aita.domain.ports.outbound import IAiModelPort


class GenerateTaskDescriptionUseCase(IGenerateTaskDescriptionUseCase):
    def __init__(self, ai: IAiModelPort) -> None:
        self._ai = ai

    async def execute(self, command: GenerateTaskDescriptionCommand) -> GeneratedTaskContent:
        audit("AI-GENERATE", "Solicitud de redacción de tarea")
        result = await run_ai(
            "AI-GENERATE",
            "generación de descripción",
            lambda: self._ai.generate_task_description(command.idea),
        )
        return result  # type: ignore[return-value]

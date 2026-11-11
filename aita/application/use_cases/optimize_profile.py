"""Sugerencias de perfil y publicación hacia el microservicio de Perfiles."""

from aita.application.audit import audit
from aita.application.support import new_event_id, run_ai, utc_now
from aita.domain.exceptions import IntegrationError
from aita.domain.models.events import ProfileOptimizationSuggestedEvent
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import ProfileOptimization
from aita.domain.ports.inbound import IOptimizeProfileUseCase
from aita.domain.ports.outbound import IAiModelPort, IEventPublisherPort


class OptimizeProfileUseCase(IOptimizeProfileUseCase):
    def __init__(self, ai: IAiModelPort, publisher: IEventPublisherPort) -> None:
        self._ai = ai
        self._publisher = publisher

    async def execute(self, profile: ProviderProfile) -> ProfileOptimization:
        audit("AI-PROFILE", f"Optimización solicitada para prestador ID: {profile.provider_id}")
        result = await run_ai(
            "AI-PROFILE",
            f"optimización de perfil {profile.provider_id}",
            lambda: self._ai.suggest_profile_optimization(profile),
        )
        optimization: ProfileOptimization = result  # type: ignore[assignment]
        event = ProfileOptimizationSuggestedEvent(
            event_id=new_event_id(),
            occurred_at=utc_now(),
            optimization=optimization,
        )
        try:
            await self._publisher.publish_profile_optimization(event)
        except IntegrationError:
            audit(
                "AI-PROFILE",
                f"No se pudo publicar la sugerencia del prestador ID: {profile.provider_id}",
            )
            raise
        audit("AI-PROFILE", f"Sugerencia publicada para prestador ID: {profile.provider_id}")
        return optimization

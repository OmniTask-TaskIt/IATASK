"""Inyección de dependencias para FastAPI y servicios de infraestructura."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from aita.application.container import UseCases, build_use_cases
from aita.application.event_dispatcher import AitaEventDispatcher
from aita.domain.ports.outbound import IAiModelPort, IEventPublisherPort, IVectorSearchPort
from aita.infrastructure.config import Settings
from aita.infrastructure.outbound.ai.gemini_adapter import GeminiAiAdapter
from aita.infrastructure.outbound.ai.qwen_adapter import LocalQwenAiAdapter
from aita.infrastructure.outbound.rabbitmq_publisher import NullEventPublisher, RabbitMqEventPublisher
from aita.infrastructure.outbound.vector_search import InMemoryVectorSearchAdapter


@lru_cache()
def get_settings() -> Settings:
    """Configuración cacheada del microservicio."""
    return Settings()


@lru_cache()
def get_vector_search() -> IVectorSearchPort:
    """Instancia singleton del almacén vectorial en memoria."""
    return InMemoryVectorSearchAdapter()


def get_ai_adapter(settings: Annotated[Settings, Depends(get_settings)]) -> IAiModelPort:
    """Selecciona el adaptador de IA según la variable de entorno AI_PROVIDER."""
    provider = settings.ai_provider.strip().lower()

    if provider in {"gemini", "google_gemini"}:
        return GeminiAiAdapter(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            embed_model=settings.gemini_embed_model,
            timeout=settings.http_timeout_seconds,
        )

    # Por defecto usamos el adaptador local Ollama / Qwen
    return LocalQwenAiAdapter(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        embed_model=settings.ollama_embed_model,
        timeout=settings.http_timeout_seconds,
    )


def get_event_publisher(settings: Annotated[Settings, Depends(get_settings)]) -> IEventPublisherPort:
    """Selecciona el publicador de eventos adecuado."""
    if settings.rabbitmq_enabled and settings.rabbitmq_url:
        return RabbitMqEventPublisher(
            rabbitmq_url=settings.rabbitmq_url,
            exchange_name=settings.rabbitmq_exchange,
            security_routing_key=settings.rabbitmq_security_routing_key,
            profile_routing_key=settings.rabbitmq_profile_routing_key,
        )
    return NullEventPublisher()


def get_use_cases(
    ai: Annotated[IAiModelPort, Depends(get_ai_adapter)],
    vectors: Annotated[IVectorSearchPort, Depends(get_vector_search)],
    publisher: Annotated[IEventPublisherPort, Depends(get_event_publisher)],
) -> UseCases:
    """Construye e inyecta la suite de casos de uso."""
    return build_use_cases(ai=ai, vectors=vectors, publisher=publisher)


def get_event_dispatcher(
    use_cases: Annotated[UseCases, Depends(get_use_cases)],
) -> AitaEventDispatcher:
    """Crea el despachador de eventos con los casos de uso inyectados."""
    return AitaEventDispatcher(use_cases=use_cases)


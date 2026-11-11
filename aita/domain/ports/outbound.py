"""Puertos de salida. La aplicación depende de estas abstracciones, no de adaptadores."""

from abc import ABC, abstractmethod

from aita.domain.models.commands import FraudCheckCommand
from aita.domain.models.enums import TaskCategory
from aita.domain.models.events import FraudAlertDetectedEvent, ProfileOptimizationSuggestedEvent
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import (
    FraudAnalysis,
    GeneratedTaskContent,
    PriceEstimate,
    ProfileOptimization,
    SentimentAnalysis,
    VectorHit,
)
from aita.domain.models.review import Review
from aita.domain.models.task import TaskText


class IAiModelPort(ABC):
    """Modelo de lenguaje intercambiable (Qwen vía Ollama o Gemini).

    El adaptador traduce cualquier fallo de red, timeout o respuesta inválida
    a `AiServiceUnavailableError`. La aplicación no captura excepciones del cliente HTTP.
    """

    @abstractmethod
    async def generate_task_description(self, idea: str) -> GeneratedTaskContent:
        """Redacta título y descripción a partir de una idea corta."""

    @abstractmethod
    async def estimate_fair_price(
        self,
        description: str,
        category: TaskCategory,
        location: str,
    ) -> PriceEstimate:
        """Estima un rango de precio justo para la tarea."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Devuelve el vector semántico de un texto."""

    @abstractmethod
    async def analyze_sentiment(self, review: Review) -> SentimentAnalysis:
        """Clasifica el sentimiento y extrae palabras clave de una reseña."""

    @abstractmethod
    async def detect_anomalies(self, command: FraudCheckCommand) -> FraudAnalysis:
        """Detecta fraude, acoso, spam o phishing en un texto."""

    @abstractmethod
    async def suggest_profile_optimization(self, profile: ProviderProfile) -> ProfileOptimization:
        """Propone mejoras concretas para el perfil de un prestador."""


class IVectorSearchPort(ABC):
    """Índice vectorial de tareas y prestadores. La primera implementación es un mock."""

    @abstractmethod
    async def upsert_task(self, task: TaskText, embedding: list[float]) -> None:
        """Indexa o reemplaza el embedding de una tarea."""

    @abstractmethod
    async def upsert_provider(self, profile: ProviderProfile, embedding: list[float]) -> None:
        """Indexa o reemplaza el embedding de un prestador."""

    @abstractmethod
    async def search_providers(self, embedding: list[float], limit: int) -> list[VectorHit]:
        """Busca los prestadores más cercanos al embedding de una tarea."""


class IEventPublisherPort(ABC):
    """Publicación de eventos de AITA.

    `publish_fraud_alert` debe salir por la routing key `taskit.security.events`.
    `publish_profile_optimization` debe salir por `taskit.profile.events`.
    """

    @abstractmethod
    async def publish_fraud_alert(self, event: FraudAlertDetectedEvent) -> None:
        """Notifica una anomalía al microservicio de Auditoría HITL."""

    @abstractmethod
    async def publish_profile_optimization(
        self,
        event: ProfileOptimizationSuggestedEvent,
    ) -> None:
        """Envía sugerencias de perfil al microservicio de Perfiles."""

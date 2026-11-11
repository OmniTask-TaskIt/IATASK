"""Puertos de entrada. Los adaptadores HTTP y RabbitMQ llaman a estas interfaces."""

from abc import ABC, abstractmethod

from aita.domain.models.commands import (
    EstimateFairPriceCommand,
    FraudCheckCommand,
    GenerateTaskDescriptionCommand,
    SemanticMatchCommand,
)
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import (
    FraudAnalysis,
    GeneratedTaskContent,
    MatchResult,
    PriceEstimate,
    ProfileOptimization,
    SentimentAnalysis,
)
from aita.domain.models.review import Review
from aita.domain.models.task import TaskText


class IGenerateTaskDescriptionUseCase(ABC):
    @abstractmethod
    async def execute(self, command: GenerateTaskDescriptionCommand) -> GeneratedTaskContent:
        """Convierte una idea corta en título y descripción listos para publicar."""


class IEstimateFairPriceUseCase(ABC):
    @abstractmethod
    async def execute(self, command: EstimateFairPriceCommand) -> PriceEstimate:
        """Sugiere un rango de precio a partir de descripción, categoría y ubicación."""


class ISemanticMatchmakingUseCase(ABC):
    @abstractmethod
    async def index_task(self, task: TaskText) -> None:
        """Calcula y guarda el embedding de una tarea recién publicada."""

    @abstractmethod
    async def index_provider(self, profile: ProviderProfile) -> None:
        """Calcula y guarda el embedding del perfil de un prestador."""

    @abstractmethod
    async def match(self, command: SemanticMatchCommand) -> list[MatchResult]:
        """Devuelve prestadores ordenados por cercanía semántica a la tarea."""


class IAnalyzeReviewSentimentUseCase(ABC):
    @abstractmethod
    async def execute(self, review: Review) -> SentimentAnalysis:
        """Extrae sentimiento, puntaje y palabras clave de una reseña."""


class IFraudDetectionShieldUseCase(ABC):
    @abstractmethod
    async def execute(self, command: FraudCheckCommand) -> FraudAnalysis:
        """Analiza un texto y, si hay anomalía, emite la alerta de seguridad."""


class IOptimizeProfileUseCase(ABC):
    """Produce `ProfileOptimizationSuggestedEvent` a partir de un perfil."""

    @abstractmethod
    async def execute(self, profile: ProviderProfile) -> ProfileOptimization:
        """Sugiere cómo mejorar la biografía y las habilidades del prestador."""

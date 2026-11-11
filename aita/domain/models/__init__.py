"""Modelos Pydantic del dominio."""

from aita.domain.models.chat import Chat, Message
from aita.domain.models.commands import (
    EstimateFairPriceCommand,
    FraudCheckCommand,
    GenerateTaskDescriptionCommand,
    SemanticMatchCommand,
)
from aita.domain.models.enums import (
    AnomalyType,
    AuditReaction,
    EventType,
    FraudRiskLevel,
    SentimentLabel,
    TaskCategory,
    TaskStatus,
    TextAnalysisSource,
)
from aita.domain.models.events import (
    ChatMessageSentEvent,
    DomainEvent,
    FraudAlertDetectedEvent,
    ProfileOptimizationSuggestedEvent,
    ReviewCompletedEvent,
    TaskCreatedEvent,
)
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import (
    FraudAnalysis,
    GeneratedTaskContent,
    MatchResult,
    PriceEstimate,
    ProfileOptimization,
    SentimentAnalysis,
    VectorHit,
)
from aita.domain.models.review import Review
from aita.domain.models.task import Task, TaskBase, TaskText

__all__ = [
    "AnomalyType",
    "AuditReaction",
    "Chat",
    "ChatMessageSentEvent",
    "DomainEvent",
    "EstimateFairPriceCommand",
    "EventType",
    "FraudAlertDetectedEvent",
    "FraudAnalysis",
    "FraudCheckCommand",
    "FraudRiskLevel",
    "GenerateTaskDescriptionCommand",
    "GeneratedTaskContent",
    "MatchResult",
    "Message",
    "PriceEstimate",
    "ProfileOptimization",
    "ProfileOptimizationSuggestedEvent",
    "ProviderProfile",
    "Review",
    "ReviewCompletedEvent",
    "SemanticMatchCommand",
    "SentimentAnalysis",
    "SentimentLabel",
    "Task",
    "TaskBase",
    "TaskCategory",
    "TaskCreatedEvent",
    "TaskStatus",
    "TaskText",
    "TextAnalysisSource",
    "VectorHit",
]

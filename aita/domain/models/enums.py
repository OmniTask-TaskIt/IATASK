"""Enumeraciones compartidas por el dominio y los eventos."""

from enum import Enum


class TaskCategory(str, Enum):
    ARREGLOS = "ARREGLOS"
    EDUCACION = "EDUCACION"


class TaskStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ASSIGNED = "ASSIGNED"
    REPORTED = "REPORTED"
    DISPUTED = "DISPUTED"


class EventType(str, Enum):
    TASK_CREATED = "TaskCreatedEvent"
    REVIEW_COMPLETED = "ReviewCompletedEvent"
    CHAT_MESSAGE_SENT = "ChatMessageSentEvent"
    FRAUD_ALERT_DETECTED = "FraudAlertDetectedEvent"
    PROFILE_OPTIMIZATION_SUGGESTED = "ProfileOptimizationSuggestedEvent"


class TextAnalysisSource(str, Enum):
    TASK_DESCRIPTION = "TASK_DESCRIPTION"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    REVIEW = "REVIEW"


class SentimentLabel(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class FraudRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    FRAUD = "FRAUD"
    HARASSMENT = "HARASSMENT"
    SPAM = "SPAM"
    PHISHING = "PHISHING"


class AuditReaction(str, Enum):
    """Acción que el microservicio de Auditoría HITL debe aplicar."""

    UNDER_REVIEW = "UNDER_REVIEW"
    ALERT_ADMIN = "ALERT_ADMIN"

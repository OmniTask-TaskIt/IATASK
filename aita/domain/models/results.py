"""Resultados que los casos de uso devuelven a los adaptadores de entrada."""

from typing import Optional

from pydantic import Field, model_validator

from aita.domain.models.base import DomainModel
from aita.domain.models.enums import (
    AnomalyType,
    FraudRiskLevel,
    SentimentLabel,
    TextAnalysisSource,
)


class GeneratedTaskContent(DomainModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10)


class PriceEstimate(DomainModel):
    min_price: int = Field(ge=0)
    max_price: int = Field(ge=0)
    currency: str = Field(default="COP", min_length=3, max_length=3)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def max_price_covers_min_price(self) -> "PriceEstimate":
        if self.max_price < self.min_price:
            raise ValueError("max_price debe ser mayor o igual que min_price.")
        return self


class VectorHit(DomainModel):
    """Coincidencia de la búsqueda vectorial, antes de explicarla al usuario."""

    provider_id: str = Field(min_length=1)
    score: float = Field(ge=-1.0, le=1.0)
    display_name: str = ""


class MatchResult(DomainModel):
    task_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    score: float = Field(ge=-1.0, le=1.0)
    rationale: str = ""


class SentimentAnalysis(DomainModel):
    review_id: str = Field(min_length=1)
    sentiment: SentimentLabel
    score: float = Field(ge=-1.0, le=1.0)
    keywords: list[str]
    summary: str = Field(min_length=1)


class FraudAnalysis(DomainModel):
    source: TextAnalysisSource
    source_id: str = Field(min_length=1)
    task_id: Optional[str] = None
    chat_id: Optional[str] = None
    is_anomaly: bool
    risk_level: FraudRiskLevel
    anomaly_types: list[AnomalyType]
    explanation: str = Field(min_length=1)
    flagged_excerpt: str = ""


class ProfileOptimization(DomainModel):
    provider_id: str = Field(min_length=1)
    suggestions: list[str] = Field(min_length=1)
    optimized_bio: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)

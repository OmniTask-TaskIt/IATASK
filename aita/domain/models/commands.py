"""Entradas de los casos de uso. No conocen HTTP ni mensajería."""

from typing import Optional

from pydantic import Field

from aita.domain.models.base import DomainModel
from aita.domain.models.enums import TaskCategory, TextAnalysisSource


class GenerateTaskDescriptionCommand(DomainModel):
    idea: str = Field(min_length=3, max_length=500)


class EstimateFairPriceCommand(DomainModel):
    description: str = Field(min_length=3)
    category: TaskCategory
    location: str = Field(min_length=2)


class SemanticMatchCommand(DomainModel):
    task_id: str = Field(min_length=1)
    task_name: str = Field(min_length=1)
    task_description: str = Field(min_length=1)
    category: TaskCategory
    limit: int = Field(default=5, ge=1, le=50)


class FraudCheckCommand(DomainModel):
    source: TextAnalysisSource
    source_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    task_id: Optional[str] = None
    chat_id: Optional[str] = None
    sender_id: Optional[str] = None

"""Reseña dejada al cerrar una tarea."""

from datetime import datetime

from pydantic import Field

from aita.domain.models.base import DomainModel


class Review(DomainModel):
    review_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    reviewee_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1)
    created_at: datetime

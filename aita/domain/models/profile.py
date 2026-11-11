"""Perfil de un prestador usado en matchmaking y optimización."""

from pydantic import Field

from aita.domain.models.base import DomainModel
from aita.domain.models.enums import TaskCategory


class ProviderProfile(DomainModel):
    provider_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    bio: str = ""
    skills: list[str] = Field(default_factory=list)
    location: str = ""
    categories: list[TaskCategory] = Field(default_factory=list)

"""Tarea publicada en Task It y la proyección mínima que usa la IA."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from aita.domain.models.base import DomainModel
from aita.domain.models.enums import TaskCategory, TaskStatus


class Task(DomainModel):
    """Equivalente de dominio al contrato `TaskBase` de la plataforma."""

    task_id: str = Field(min_length=1)
    task_name: str = Field(min_length=1)
    task_description: str = Field(min_length=1)
    task_status: TaskStatus
    task_owner: str = Field(min_length=1)
    task_assignee: Optional[str] = None
    creation_date: datetime
    category: TaskCategory
    price: int = Field(ge=0)
    report_reason: Optional[str] = None
    dispute_reason: Optional[str] = None
    owner_approval: bool = False
    assignee_approval: bool = False


# Alias de compatibilidad con el contrato TaskBase de la plataforma
TaskBase = Task


class TaskText(DomainModel):
    """Texto indexable de una tarea, sin el ciclo de vida operativo."""

    task_id: str = Field(min_length=1)
    task_name: str = Field(min_length=1)
    task_description: str = Field(min_length=1)
    category: TaskCategory

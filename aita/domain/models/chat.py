"""Conversación asociada a una tarea."""

from datetime import datetime

from pydantic import Field

from aita.domain.models.base import DomainModel


class Message(DomainModel):
    message_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)
    sender_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    timestamp: datetime


class Chat(DomainModel):
    chat_id: str = Field(min_length=1)
    task_name: str = Field(min_length=1)
    seller_id: str = Field(min_length=1)
    buyer_id: str = Field(min_length=1)
    participants: list[str]
    active: bool
    created_at: datetime
    messages: list[Message]
    task_id: str = Field(min_length=1)

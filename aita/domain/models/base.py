"""Modelo base de la capa de dominio."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Entidad o valor inmutable. Rechaza campos no declarados."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

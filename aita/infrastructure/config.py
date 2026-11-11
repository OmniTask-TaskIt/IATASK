"""Configuración leída de variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_provider: str = "qwen"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3"
    ollama_embed_model: str = "nomic-embed-text"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "gemini-embedding-001"
    http_timeout_seconds: float = 2.5

    rabbitmq_url: str = ""
    rabbitmq_enabled: bool = False
    rabbitmq_exchange: str = "taskit.events"
    rabbitmq_dead_letter_exchange: str = "taskit.dlx"
    rabbitmq_aita_queue: str = "aita.events"
    rabbitmq_aita_routing_key: str = "taskit.aita.events"
    rabbitmq_security_routing_key: str = "taskit.security.events"
    rabbitmq_profile_routing_key: str = "taskit.profile.events"

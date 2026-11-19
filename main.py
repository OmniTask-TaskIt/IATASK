import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aita.application.container import build_use_cases
from aita.application.event_dispatcher import AitaEventDispatcher
from aita.infrastructure.config import Settings
from aita.infrastructure.dependencies import (
    get_ai_adapter,
    get_event_publisher,
    get_settings,
    get_vector_search,
)
from aita.infrastructure.http.errors import register_exception_handlers
from aita.infrastructure.http.middleware import audit_http_access
from aita.infrastructure.http.router import router
from aita.infrastructure.inbound.rabbitmq_consumer import RabbitMqConsumer
from aita.infrastructure.logging_config import configure_logging
from aita.infrastructure.outbound.rabbitmq_publisher import RabbitMqEventPublisher

configure_logging()
logger = logging.getLogger("aita.main")
settings: Settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación: inicialización y apagado controlado."""
    logger.info("Iniciando microservicio AITA...")

    ai_adapter = get_ai_adapter(settings)
    vector_search = get_vector_search()
    publisher = get_event_publisher(settings)
    use_cases = build_use_cases(ai=ai_adapter, vectors=vector_search, publisher=publisher)

    app.state.use_cases = use_cases
    app.state.settings = settings
    app.state.publisher = publisher
    app.state.consumer = None

    if settings.rabbitmq_enabled and settings.rabbitmq_url:
        logger.info("RabbitMQ está habilitado. Conectando broker...")
        if isinstance(publisher, RabbitMqEventPublisher):
            await publisher.connect()

        dispatcher = AitaEventDispatcher(use_cases=use_cases)
        consumer = RabbitMqConsumer(
            rabbitmq_url=settings.rabbitmq_url,
            dispatcher=dispatcher,
            exchange_name=settings.rabbitmq_exchange,
            dead_letter_exchange=settings.rabbitmq_dead_letter_exchange,
            queue_name=settings.rabbitmq_aita_queue,
            routing_key=settings.rabbitmq_aita_routing_key,
        )
        await consumer.start()
        app.state.consumer = consumer
        logger.info("Consumidor RabbitMQ iniciado exitosamente.")
    else:
        logger.info("RabbitMQ deshabilitado en configuración.")

    yield

    logger.info("Deteniendo microservicio AITA...")
    if app.state.consumer:
        try:
            await app.state.consumer.stop()
        except Exception as exc:
            logger.error("Error deteniendo consumidor RabbitMQ: %s", exc)

    if isinstance(app.state.publisher, RabbitMqEventPublisher):
        try:
            await app.state.publisher.close()
        except Exception as exc:
            logger.error("Error cerrando publicador RabbitMQ: %s", exc)

    logger.info("Microservicio AITA detenido.")


app = FastAPI(
    title="AITA - AI Task Assistant",
    description="Microservicio de Inteligencia Artificial para la plataforma Task It",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(
        settings,
        "cors_origins",
        ["http://localhost:5173", "https://taskit-frontend-ten.vercel.app"],
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.middleware("http")(audit_http_access)
register_exception_handlers(app)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=getattr(settings, "host", "127.0.0.1"),
        port=getattr(settings, "port", 8000),
        reload=False,
    )
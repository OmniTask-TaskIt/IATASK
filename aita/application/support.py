"""Utilidades de aplicación: reloj, identificadores y degradación del modelo."""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import uuid4

from aita.application.audit import audit
from aita.domain.exceptions import AiServiceUnavailableError, AitaError

logger = logging.getLogger(__name__)


def new_event_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def run_ai(component: str, action: str, operation: Callable[[], Awaitable[object]]) -> object:
    """Ejecuta una llamada al puerto de IA y convierte fallos inesperados en error controlado."""

    try:
        result = await operation()
    except AiServiceUnavailableError:
        audit(component, f"Degradación controlada durante {action}")
        raise
    except AitaError:
        raise
    except Exception as exc:
        logger.exception("Fallo inesperado del puerto de IA durante %s", action)
        audit(component, f"Degradación controlada durante {action}")
        raise AiServiceUnavailableError() from exc
    audit(component, f"Acción completada: {action}")
    return result

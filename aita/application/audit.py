"""Logs de auditoría AAA. El texto queda en el mensaje para los recolectores de logs."""

import logging

logger = logging.getLogger("aita.audit")


def audit(component: str, message: str) -> None:
    logger.info("[AUDIT] [%s] %s", component, message)

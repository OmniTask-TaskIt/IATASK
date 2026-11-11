"""Registra cada acceso HTTP."""

from fastapi import Request

from aita.application.audit import audit


async def audit_http_access(request: Request, call_next):
    audit("ACCESS", f"{request.method} {request.url.path}")
    return await call_next(request)

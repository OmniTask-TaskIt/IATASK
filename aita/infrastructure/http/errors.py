"""JSON de error único para toda la API."""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aita.domain.exceptions import AitaError

_STATUS_BY_CODE = {
    "AI_SERVICE_UNAVAILABLE": 503,
    "EVENT_PUBLISH_FAILED": 503,
    "DOMAIN_VALIDATION_ERROR": 422,
    "REQUEST_VALIDATION_ERROR": 422,
}


def error_body(code: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AitaError)
    async def handle_aita_error(_request: Request, exc: AitaError) -> JSONResponse:
        status = _STATUS_BY_CODE.get(exc.code, 500)
        return JSONResponse(status_code=status, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                "REQUEST_VALIDATION_ERROR",
                "La solicitud no cumple el contrato de entrada.",
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "La solicitud no se pudo completar."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body("HTTP_ERROR", detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "Error interno del servicio."),
        )

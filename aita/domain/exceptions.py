"""Excepciones de negocio. No dependen de FastAPI ni de clientes HTTP."""


class AitaError(Exception):
    """Error de dominio con código estable para el contrato JSON de la API."""

    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class AiServiceUnavailableError(AitaError):
    """El modelo de IA no respondió o devolvió una salida inutilizable.

    Los casos de uso deben degradar de forma controlada: responder este error
    y no propagar fallos de red, timeouts ni payloads del proveedor.
    """

    def __init__(
        self,
        message: str = "El proveedor de IA no está disponible. Intente más tarde.",
    ) -> None:
        super().__init__(message, code="AI_SERVICE_UNAVAILABLE")


class DomainValidationError(AitaError):
    """Una regla del dominio no se cumple (datos incoherentes o incompletos)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="DOMAIN_VALIDATION_ERROR")


class IntegrationError(AitaError):
    """No se pudo entregar un evento a otro microservicio."""

    def __init__(self, message: str = "No se pudo publicar el evento.") -> None:
        super().__init__(message, code="EVENT_PUBLISH_FAILED")

"""Contrato de integración entre AITA y el resto de Task It.

Los nombres viven en el dominio porque otros microservicios deben enlazar
exactamente estas routing keys. La conexión, el exchange type y los
adaptadores de RabbitMQ pertenecen a infraestructura.
"""


class ExchangeName:
    EVENTS = "taskit.events"
    DEAD_LETTER = "taskit.dlx"


class QueueName:
    AITA_EVENTS = "aita.events"


class RoutingKey:
    """Claves que AITA consume o que otros servicios deben escuchar."""

    AITA_EVENTS = "taskit.aita.events"
    SECURITY_EVENTS = "taskit.security.events"
    PROFILE_EVENTS = "taskit.profile.events"

"""AI Shield: detecta anomalías y publica la alerta hacia Auditoría HITL."""

from aita.application.audit import audit
from aita.application.support import new_event_id, run_ai, utc_now
from aita.domain.exceptions import IntegrationError
from aita.domain.models.commands import FraudCheckCommand
from aita.domain.models.enums import AuditReaction, FraudRiskLevel
from aita.domain.models.events import FraudAlertDetectedEvent
from aita.domain.models.results import FraudAnalysis
from aita.domain.ports.inbound import IFraudDetectionShieldUseCase
from aita.domain.ports.outbound import IAiModelPort, IEventPublisherPort


class FraudDetectionShieldUseCase(IFraudDetectionShieldUseCase):
    def __init__(self, ai: IAiModelPort, publisher: IEventPublisherPort) -> None:
        self._ai = ai
        self._publisher = publisher

    async def execute(self, command: FraudCheckCommand) -> FraudAnalysis:
        audit(
            "AI-SHIELD",
            f"Análisis solicitado para {command.source.value} ID: {command.source_id}",
        )
        result = await run_ai(
            "AI-SHIELD",
            f"AI Shield sobre {command.source.value} {command.source_id}",
            lambda: self._ai.detect_anomalies(command),
        )
        analysis: FraudAnalysis = result  # type: ignore[assignment]
        if not analysis.is_anomaly:
            audit("AI-SHIELD", f"Sin anomalías en {command.source.value} ID: {command.source_id}")
            return analysis

        event = FraudAlertDetectedEvent(
            event_id=new_event_id(),
            occurred_at=utc_now(),
            analysis=analysis,
            recommended_action=self._reaction(analysis.risk_level),
        )
        try:
            await self._publisher.publish_fraud_alert(event)
        except IntegrationError:
            audit("AI-SHIELD", f"No se pudo publicar la alerta de {self._subject(command)}")
            raise
        audit("AI-SHIELD", f"Anomalía detectada en {self._subject(command)}")
        return analysis

    @staticmethod
    def _reaction(risk_level: FraudRiskLevel) -> AuditReaction:
        if risk_level in {FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL}:
            return AuditReaction.ALERT_ADMIN
        return AuditReaction.UNDER_REVIEW

    @staticmethod
    def _subject(command: FraudCheckCommand) -> str:
        if command.task_id:
            return f"tarea ID: {command.task_id}"
        if command.chat_id:
            return f"chat ID: {command.chat_id}"
        return f"origen ID: {command.source_id}"

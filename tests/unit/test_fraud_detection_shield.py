"""Pruebas unitarias para FraudDetectionShieldUseCase (AI Shield)."""

import pytest

from aita.application.use_cases.fraud_detection_shield import FraudDetectionShieldUseCase
from aita.domain.exceptions import AiServiceUnavailableError, IntegrationError
from aita.domain.models.commands import FraudCheckCommand
from aita.domain.models.enums import AnomalyType, AuditReaction, FraudRiskLevel, TextAnalysisSource
from aita.domain.models.events import FraudAlertDetectedEvent
from aita.domain.models.results import FraudAnalysis


@pytest.mark.asyncio
async def test_fraud_shield_no_anomaly(mock_ai, mock_publisher):
    # Arrange
    analysis = FraudAnalysis(
        source=TextAnalysisSource.TASK_DESCRIPTION,
        source_id="task-001",
        task_id="task-001",
        chat_id=None,
        is_anomaly=False,
        risk_level=FraudRiskLevel.LOW,
        anomaly_types=[],
        explanation="Texto limpio, solicitud legítima.",
        flagged_excerpt="",
    )
    mock_ai.detect_anomalies.return_value = analysis
    use_case = FraudDetectionShieldUseCase(ai=mock_ai, publisher=mock_publisher)
    command = FraudCheckCommand(
        source=TextAnalysisSource.TASK_DESCRIPTION,
        source_id="task-001",
        text="Necesito pintar mi habitación color blanco.",
        task_id="task-001",
    )

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result == analysis
    assert not result.is_anomaly
    mock_publisher.publish_fraud_alert.assert_not_called()


@pytest.mark.asyncio
async def test_fraud_shield_with_anomaly_publishes_alert(mock_ai, mock_publisher):
    # Arrange: Se detecta intento de pago por fuera
    analysis = FraudAnalysis(
        source=TextAnalysisSource.CHAT_MESSAGE,
        source_id="msg-999",
        task_id="task-001",
        chat_id="chat-555",
        is_anomaly=True,
        risk_level=FraudRiskLevel.HIGH,
        anomaly_types=[AnomalyType.FRAUD],
        explanation="Se sugiere pagar por transferencia externa para evitar comisiones.",
        flagged_excerpt="escríbeme al WhatsApp y te pago por Nequi directo",
    )
    mock_ai.detect_anomalies.return_value = analysis
    use_case = FraudDetectionShieldUseCase(ai=mock_ai, publisher=mock_publisher)
    command = FraudCheckCommand(
        source=TextAnalysisSource.CHAT_MESSAGE,
        source_id="msg-999",
        text="No pagues por aquí, escríbeme al WhatsApp y te pago por Nequi directo.",
        task_id="task-001",
        chat_id="chat-555",
    )

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result == analysis
    assert result.is_anomaly
    assert mock_publisher.publish_fraud_alert.await_count == 1
    call_args = mock_publisher.publish_fraud_alert.call_args[0][0]
    assert isinstance(call_args, FraudAlertDetectedEvent)
    assert call_args.analysis == analysis
    assert call_args.recommended_action == AuditReaction.ALERT_ADMIN


@pytest.mark.asyncio
async def test_fraud_shield_ai_failure(mock_ai, mock_publisher):
    # Arrange
    mock_ai.detect_anomalies.side_effect = RuntimeError("Modelo sobrecargado")
    use_case = FraudDetectionShieldUseCase(ai=mock_ai, publisher=mock_publisher)
    command = FraudCheckCommand(
        source=TextAnalysisSource.TASK_DESCRIPTION,
        source_id="task-002",
        text="Texto cualquiera",
    )

    # Act & Assert
    with pytest.raises(AiServiceUnavailableError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_fraud_shield_publisher_integration_error(mock_ai, mock_publisher):
    # Arrange: AI detecta fraude pero RabbitMQ falla al publicar
    analysis = FraudAnalysis(
        source=TextAnalysisSource.TASK_DESCRIPTION,
        source_id="task-003",
        task_id="task-003",
        chat_id=None,
        is_anomaly=True,
        risk_level=FraudRiskLevel.CRITICAL,
        anomaly_types=[AnomalyType.PHISHING],
        explanation="Enlace externo fraudulento.",
        flagged_excerpt="entra a http://link-falso.com",
    )
    mock_ai.detect_anomalies.return_value = analysis
    mock_publisher.publish_fraud_alert.side_effect = IntegrationError("Conexión perdida con broker")
    use_case = FraudDetectionShieldUseCase(ai=mock_ai, publisher=mock_publisher)
    command = FraudCheckCommand(
        source=TextAnalysisSource.TASK_DESCRIPTION,
        source_id="task-003",
        text="entra a http://link-falso.com para recibir el pago",
        task_id="task-003",
    )

    # Act & Assert
    with pytest.raises(IntegrationError) as exc_info:
        await use_case.execute(command)

    assert "Conexión perdida" in exc_info.value.message


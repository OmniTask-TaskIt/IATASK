"""Pruebas de endpoints HTTP de FastAPI y exception handler global."""

from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from aita.application.container import UseCases
from aita.domain.exceptions import AiServiceUnavailableError
from aita.domain.models.results import GeneratedTaskContent
from main import app


@pytest.fixture
def client_with_mock_use_cases():
    mock_use_cases = UseCases(
        generate_task_description=AsyncMock(),
        estimate_fair_price=AsyncMock(),
        semantic_matchmaking=AsyncMock(),
        analyze_review_sentiment=AsyncMock(),
        fraud_detection_shield=AsyncMock(),
        optimize_profile=AsyncMock(),
    )
    with TestClient(app) as test_client:
        # Asignar mocks DESPUÉS del arranque del lifespan
        app.state.use_cases = mock_use_cases
        yield test_client, mock_use_cases


def test_health_check(client_with_mock_use_cases):
    client, _ = client_with_mock_use_cases
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_description_endpoint_success(client_with_mock_use_cases):
    client, mock_uc = client_with_mock_use_cases
    mock_uc.generate_task_description.execute.return_value = GeneratedTaskContent(
        title="Instalación de cortinas",
        description="Se requiere instalar barras y cortinas pesadas.",
    )

    response = client.post(
        "/api/v1/tasks/description",
        json={"idea": "instalar cortinas en el cuarto"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Instalación de cortinas"
    assert data["description"] == "Se requiere instalar barras y cortinas pesadas."


def test_generate_description_endpoint_ai_failure_exception_handler(client_with_mock_use_cases):
    client, mock_uc = client_with_mock_use_cases
    mock_uc.generate_task_description.execute.side_effect = AiServiceUnavailableError(
        "Proveedor de IA no responde"
    )

    response = client.post(
        "/api/v1/tasks/description",
        json={"idea": "pintar pared sala"},
    )

    # Debe retornar 503 con formato estándar: code, message, timestamp
    assert response.status_code == 503
    data = response.json()
    assert data["code"] == "AI_SERVICE_UNAVAILABLE"
    assert "Proveedor de IA no responde" in data["message"]
    assert "timestamp" in data


def test_validation_error_standard_format(client_with_mock_use_cases):
    client, _ = client_with_mock_use_cases
    # Enviamos idea demasiado corta (< 3 caracteres)
    response = client.post(
        "/api/v1/tasks/description",
        json={"idea": "a"},
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "REQUEST_VALIDATION_ERROR"
    assert "timestamp" in data

"""Pruebas unitarias para AnalyzeReviewSentimentUseCase."""

import pytest

from aita.application.use_cases.analyze_review_sentiment import AnalyzeReviewSentimentUseCase
from aita.domain.exceptions import AiServiceUnavailableError
from aita.domain.models.enums import SentimentLabel
from aita.domain.models.results import SentimentAnalysis


@pytest.mark.asyncio
async def test_analyze_review_sentiment_happy_path(mock_ai, sample_review):
    # Arrange
    expected = SentimentAnalysis(
        review_id=sample_review.review_id,
        sentiment=SentimentLabel.POSITIVE,
        score=0.95,
        keywords=["puntual", "impecable", "excelente"],
        summary="Cliente muy satisfecho con la atención y puntualidad.",
    )
    mock_ai.analyze_sentiment.return_value = expected
    use_case = AnalyzeReviewSentimentUseCase(ai=mock_ai)

    # Act
    result = await use_case.execute(sample_review)

    # Assert
    assert result == expected
    assert result.sentiment == SentimentLabel.POSITIVE
    assert result.score == 0.95
    assert "excelente" in result.keywords
    mock_ai.analyze_sentiment.assert_awaited_once_with(sample_review)


@pytest.mark.asyncio
async def test_analyze_review_sentiment_ai_failure(mock_ai, sample_review):
    # Arrange
    mock_ai.analyze_sentiment.side_effect = RuntimeError("Ollama crashed")
    use_case = AnalyzeReviewSentimentUseCase(ai=mock_ai)

    # Act & Assert
    with pytest.raises(AiServiceUnavailableError):
        await use_case.execute(sample_review)


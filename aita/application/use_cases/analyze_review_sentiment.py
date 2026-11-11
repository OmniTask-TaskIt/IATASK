"""Lectura de sentimiento y palabras clave de una reseña."""

from aita.application.audit import audit
from aita.application.support import run_ai
from aita.domain.models.results import SentimentAnalysis
from aita.domain.models.review import Review
from aita.domain.ports.inbound import IAnalyzeReviewSentimentUseCase
from aita.domain.ports.outbound import IAiModelPort


class AnalyzeReviewSentimentUseCase(IAnalyzeReviewSentimentUseCase):
    def __init__(self, ai: IAiModelPort) -> None:
        self._ai = ai

    async def execute(self, review: Review) -> SentimentAnalysis:
        audit("AI-SENTIMENT", f"Análisis de reseña ID: {review.review_id}")
        result = await run_ai(
            "AI-SENTIMENT",
            f"análisis de sentimiento de reseña {review.review_id}",
            lambda: self._ai.analyze_sentiment(review),
        )
        analysis: SentimentAnalysis = result  # type: ignore[assignment]
        audit(
            "AI-SENTIMENT",
            f"Reseña ID: {review.review_id} sentimiento {analysis.sentiment.value}",
        )
        return analysis

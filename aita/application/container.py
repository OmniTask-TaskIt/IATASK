"""Agrupa los casos de uso que comparten los routers y el consumidor."""

from dataclasses import dataclass

from aita.application.use_cases import (
    AnalyzeReviewSentimentUseCase,
    EstimateFairPriceUseCase,
    FraudDetectionShieldUseCase,
    GenerateTaskDescriptionUseCase,
    OptimizeProfileUseCase,
    SemanticMatchmakingUseCase,
)
from aita.domain.ports.outbound import IAiModelPort, IEventPublisherPort, IVectorSearchPort


@dataclass
class UseCases:
    generate_task_description: GenerateTaskDescriptionUseCase
    estimate_fair_price: EstimateFairPriceUseCase
    semantic_matchmaking: SemanticMatchmakingUseCase
    analyze_review_sentiment: AnalyzeReviewSentimentUseCase
    fraud_detection_shield: FraudDetectionShieldUseCase
    optimize_profile: OptimizeProfileUseCase


def build_use_cases(
    ai: IAiModelPort,
    vectors: IVectorSearchPort,
    publisher: IEventPublisherPort,
) -> UseCases:
    return UseCases(
        generate_task_description=GenerateTaskDescriptionUseCase(ai),
        estimate_fair_price=EstimateFairPriceUseCase(ai),
        semantic_matchmaking=SemanticMatchmakingUseCase(ai, vectors),
        analyze_review_sentiment=AnalyzeReviewSentimentUseCase(ai),
        fraud_detection_shield=FraudDetectionShieldUseCase(ai, publisher),
        optimize_profile=OptimizeProfileUseCase(ai, publisher),
    )

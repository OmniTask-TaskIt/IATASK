"""Rutas HTTP de AITA."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from aita.application.container import UseCases
from aita.domain.models.commands import (
    EstimateFairPriceCommand,
    FraudCheckCommand,
    GenerateTaskDescriptionCommand,
    SemanticMatchCommand,
)
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import (
    FraudAnalysis,
    GeneratedTaskContent,
    MatchResult,
    PriceEstimate,
    ProfileOptimization,
    SentimentAnalysis,
)
from aita.domain.models.review import Review
from aita.domain.models.task import TaskText

router = APIRouter()


class IndexedResource(BaseModel):
    status: str = Field(default="indexed")
    resource_id: str


def _use_cases(request: Request) -> UseCases:
    return request.app.state.use_cases


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/tasks/description", response_model=GeneratedTaskContent)
async def generate_description(
    command: GenerateTaskDescriptionCommand,
    request: Request,
) -> GeneratedTaskContent:
    return await _use_cases(request).generate_task_description.execute(command)


@router.post("/api/v1/tasks/price-estimate", response_model=PriceEstimate)
async def estimate_price(command: EstimateFairPriceCommand, request: Request) -> PriceEstimate:
    return await _use_cases(request).estimate_fair_price.execute(command)


@router.post("/api/v1/matchmaking/tasks", response_model=IndexedResource)
async def index_task(task: TaskText, request: Request) -> IndexedResource:
    await _use_cases(request).semantic_matchmaking.index_task(task)
    return IndexedResource(resource_id=task.task_id)


@router.post("/api/v1/matchmaking/providers", response_model=IndexedResource)
async def index_provider(profile: ProviderProfile, request: Request) -> IndexedResource:
    await _use_cases(request).semantic_matchmaking.index_provider(profile)
    return IndexedResource(resource_id=profile.provider_id)


@router.post("/api/v1/matchmaking/search", response_model=list[MatchResult])
async def search_providers(command: SemanticMatchCommand, request: Request) -> list[MatchResult]:
    return await _use_cases(request).semantic_matchmaking.match(command)


@router.post("/api/v1/reviews/sentiment", response_model=SentimentAnalysis)
async def analyze_sentiment(review: Review, request: Request) -> SentimentAnalysis:
    return await _use_cases(request).analyze_review_sentiment.execute(review)


@router.post("/api/v1/shield/analyze", response_model=FraudAnalysis)
async def analyze_shield(command: FraudCheckCommand, request: Request) -> FraudAnalysis:
    return await _use_cases(request).fraud_detection_shield.execute(command)


@router.post("/api/v1/profiles/optimize", response_model=ProfileOptimization)
async def optimize_profile(profile: ProviderProfile, request: Request) -> ProfileOptimization:
    return await _use_cases(request).optimize_profile.execute(profile)

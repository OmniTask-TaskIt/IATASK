"""Adaptador de IA para Google Gemini usando API REST HTTP asíncrona."""

import json
import logging
from typing import Any

import httpx

from aita.domain.exceptions import AiServiceUnavailableError
from aita.domain.models.commands import FraudCheckCommand
from aita.domain.models.enums import (
    AnomalyType,
    FraudRiskLevel,
    SentimentLabel,
    TaskCategory,
)
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.results import (
    FraudAnalysis,
    GeneratedTaskContent,
    PriceEstimate,
    ProfileOptimization,
    SentimentAnalysis,
)
from aita.domain.models.review import Review
from aita.domain.ports.outbound import IAiModelPort
from aita.infrastructure.outbound.ai.parsing import parse_embedding, parse_model_payload

logger = logging.getLogger(__name__)


class GeminiAiAdapter(IAiModelPort):
    """Llama a los endpoints v1beta de Google Generative Language API con httpx."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        embed_model: str = "gemini-embedding-001",
        timeout: float = 2.5,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._embed_model = embed_model
        self._timeout = timeout

    async def _post_generate(self, prompt: str, system: str = "") -> dict[str, Any]:
        if not self._api_key:
            raise AiServiceUnavailableError("GEMINI_API_KEY no está configurada.")

        url = f"{self.BASE_URL}/models/{self._model}:generateContent?key={self._api_key}"
        contents = [{"parts": [{"text": prompt}]}]
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        }
        if system:
            body["systemInstruction"] = {
                "parts": [{"text": system}]
            }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=body)
                if response.status_code != 200:
                    logger.error("Gemini API respondió %s: %s", response.status_code, response.text)
                    raise AiServiceUnavailableError(f"Gemini API error HTTP {response.status_code}")
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise AiServiceUnavailableError("Gemini no devolvió candidatos de respuesta.")
                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    raise AiServiceUnavailableError("Gemini no devolvió contenido de texto.")
                raw_text = content_parts[0].get("text", "")
                return parse_model_payload(raw_text)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Fallo al contactar Gemini API: %s", exc)
            raise AiServiceUnavailableError("No se pudo conectar con el servicio Google Gemini.") from exc

    async def generate_task_description(self, idea: str) -> GeneratedTaskContent:
        system = (
            "Eres un asistente de redacción para la plataforma Task It. "
            "Responde únicamente en JSON con las claves: "
            "'title' (string de 3 a 120 caracteres) y "
            "'description' (string de al menos 10 caracteres)."
        )
        prompt = f"Idea de la tarea: {idea}"
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            return GeneratedTaskContent(
                title=str(data.get("title", idea[:120])),
                description=str(data.get("description", f"Servicio requerido: {idea}")),
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de Gemini no cumple contrato de descripción.") from exc

    async def estimate_fair_price(
        self,
        description: str,
        category: TaskCategory,
        location: str,
    ) -> PriceEstimate:
        system = (
            "Eres un estimador de precios de servicios para Colombia (moneda COP). "
            "Responde estrictamente en JSON con: "
            "'min_price' (entero positivo), 'max_price' (entero >= min_price), "
            "'currency' ('COP'), 'confidence' (float 0.0 a 1.0), 'rationale' (string)."
        )
        prompt = (
            f"Categoría: {category.value}\n"
            f"Ubicación: {location}\n"
            f"Descripción: {description}"
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            min_p = int(data.get("min_price", 25000))
            max_p = int(data.get("max_price", max(min_p, 60000)))
            conf = float(data.get("confidence", 0.85))
            conf = max(0.0, min(1.0, conf))
            rationale = str(data.get("rationale", "Precio estimado según mercado local."))
            return PriceEstimate(
                min_price=min_p,
                max_price=max_p,
                currency="COP",
                confidence=conf,
                rationale=rationale,
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de Gemini no cumple contrato de precio.") from exc

    async def embed(self, text: str) -> list[float]:
        if not self._api_key:
            raise AiServiceUnavailableError("GEMINI_API_KEY no está configurada.")

        url = f"{self.BASE_URL}/models/{self._embed_model}:embedContent?key={self._api_key}"
        body = {
            "content": {
                "parts": [{"text": text}]
            }
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=body)
                if response.status_code != 200:
                    logger.error("Gemini Embeddings error %s: %s", response.status_code, response.text)
                    raise AiServiceUnavailableError(f"Gemini Embeddings error HTTP {response.status_code}")
                data = response.json()
                values = data.get("embedding", {}).get("values", [])
                return parse_embedding(values)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Fallo al obtener embedding de Gemini: %s", exc)
            raise AiServiceUnavailableError("No se pudo generar embedding con Google Gemini.") from exc

    async def analyze_sentiment(self, review: Review) -> SentimentAnalysis:
        system = (
            "Eres un analizador de sentimiento de reseñas en Task It. "
            "Responde en JSON con: "
            "'sentiment' ('POSITIVE' | 'NEUTRAL' | 'NEGATIVE'), "
            "'score' (float entre -1.0 y 1.0), "
            "'keywords' (lista de strings), 'summary' (string breve)."
        )
        prompt = (
            f"Calificación: {review.rating}/5\n"
            f"Comentario: {review.comment}"
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            raw_sentiment = str(data.get("sentiment", "NEUTRAL")).upper()
            if raw_sentiment not in {s.value for s in SentimentLabel}:
                raw_sentiment = "POSITIVE" if review.rating >= 4 else ("NEGATIVE" if review.rating <= 2 else "NEUTRAL")
            score = float(data.get("score", (review.rating - 3) / 2.0))
            score = max(-1.0, min(1.0, score))
            keywords = [str(k) for k in data.get("keywords", [])]
            summary = str(data.get("summary", f"Reseña calificada con {review.rating}/5."))

            return SentimentAnalysis(
                review_id=review.review_id,
                sentiment=SentimentLabel(raw_sentiment),
                score=score,
                keywords=keywords,
                summary=summary,
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de Gemini no cumple contrato de sentimiento.") from exc

    async def detect_anomalies(self, command: FraudCheckCommand) -> FraudAnalysis:
        system = (
            "Eres AI Shield de Task It. Detecta fraudes, pagos externos, acoso, spam o phishing. "
            "Responde en JSON con: "
            "'is_anomaly' (boolean), "
            "'risk_level' ('LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'), "
            "'anomaly_types' (lista con: 'FRAUD', 'HARASSMENT', 'SPAM', 'PHISHING'), "
            "'explanation' (string), 'flagged_excerpt' (string o vacío)."
        )
        prompt = (
            f"Fuente: {command.source.value}\n"
            f"Texto: \"\"\"{command.text}\"\"\""
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            is_anomaly = bool(data.get("is_anomaly", False))
            raw_risk = str(data.get("risk_level", "LOW")).upper()
            if raw_risk not in {r.value for r in FraudRiskLevel}:
                raw_risk = "LOW" if not is_anomaly else "MEDIUM"
            anomaly_types: list[AnomalyType] = []
            for item in data.get("anomaly_types", []):
                upper_item = str(item).upper()
                if upper_item in {a.value for a in AnomalyType}:
                    anomaly_types.append(AnomalyType(upper_item))
            if is_anomaly and not anomaly_types:
                anomaly_types.append(AnomalyType.FRAUD)

            explanation = str(data.get("explanation", "Análisis completado sin riesgos detectados."))
            flagged_excerpt = str(data.get("flagged_excerpt", ""))

            return FraudAnalysis(
                source=command.source,
                source_id=command.source_id,
                task_id=command.task_id,
                chat_id=command.chat_id,
                is_anomaly=is_anomaly,
                risk_level=FraudRiskLevel(raw_risk),
                anomaly_types=anomaly_types,
                explanation=explanation,
                flagged_excerpt=flagged_excerpt,
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de Gemini no cumple contrato de AI Shield.") from exc

    async def suggest_profile_optimization(self, profile: ProviderProfile) -> ProfileOptimization:
        system = (
            "Eres un consultor de optimización de perfil profesional en Task It. "
            "Responde en JSON con: "
            "'suggestions' (lista de consejos), "
            "'optimized_bio' (propuesta redactada o null), "
            "'keywords' (lista de habilidades clave sugeridas)."
        )
        prompt = (
            f"Prestador: {profile.display_name}\n"
            f"Bio: {profile.bio}\n"
            f"Habilidades: {', '.join(profile.skills)}\n"
            f"Ubicación: {profile.location}"
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            suggestions = [str(s) for s in data.get("suggestions", [])]
            if not suggestions:
                suggestions = ["Añade una descripción más detallada de tus servicios."]
            optimized_bio = data.get("optimized_bio")
            if optimized_bio is not None:
                optimized_bio = str(optimized_bio)
            keywords = [str(k) for k in data.get("keywords", [])]

            return ProfileOptimization(
                provider_id=profile.provider_id,
                suggestions=suggestions,
                optimized_bio=optimized_bio,
                keywords=keywords,
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de Gemini no cumple contrato de optimización.") from exc


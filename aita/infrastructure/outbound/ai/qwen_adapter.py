"""Adaptador de IA para modelo Qwen ejecutado localmente mediante Ollama."""

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


class LocalQwenAiAdapter(IAiModelPort):
    """Llama a la API HTTP local de Ollama (por defecto http://localhost:11434)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3",
        embed_model: str = "nomic-embed-text",
        timeout: float = 2.5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._embed_model = embed_model
        self._timeout = timeout

    async def _post_generate(self, prompt: str, system: str = "") -> dict[str, Any]:
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.error("Ollama devolvió código %s: %s", response.status_code, response.text)
                    raise AiServiceUnavailableError(
                        f"Ollama respondió con error HTTP {response.status_code}"
                    )
                data = response.json()
                raw_response = data.get("response", "")
                return parse_model_payload(raw_response)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Fallo al contactar Ollama en %s: %s", url, exc)
            raise AiServiceUnavailableError(
                "No se pudo establecer conexión con el servicio local Ollama/Qwen."
            ) from exc

    async def generate_task_description(self, idea: str) -> GeneratedTaskContent:
        system = (
            "Eres un asistente de redacción para la plataforma Task It. "
            "Devuelve un JSON estrictamente con las claves: "
            "'title' (título conciso de 3 a 120 caracteres) y "
            "'description' (descripción detallada de al menos 10 caracteres)."
        )
        prompt = f"Crea un título y una descripción clara y profesional para la siguiente tarea:\n{idea}"
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            return GeneratedTaskContent(
                title=str(data.get("title", idea[:120])),
                description=str(data.get("description", f"Servicio requerido: {idea}")),
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de IA no cumple el contrato de descripción.") from exc

    async def estimate_fair_price(
        self,
        description: str,
        category: TaskCategory,
        location: str,
    ) -> PriceEstimate:
        system = (
            "Eres un analista de precios para servicios en Colombia (moneda COP). "
            "Devuelve un JSON con las claves: 'min_price' (entero positivo), "
            "'max_price' (entero >= min_price), 'currency' ('COP'), "
            "'confidence' (float entre 0 y 1), 'rationale' (explicación breve)."
        )
        prompt = (
            f"Categoría: {category.value}\n"
            f"Ubicación: {location}\n"
            f"Descripción: {description}\n"
            "Calcula un rango de precio justo en COP."
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            min_p = int(data.get("min_price", 20000))
            max_p = int(data.get("max_price", max(min_p, 50000)))
            confidence = float(data.get("confidence", 0.8))
            confidence = max(0.0, min(1.0, confidence))
            rationale = str(data.get("rationale", "Estimación calculada según categoría y complejidad."))
            return PriceEstimate(
                min_price=min_p,
                max_price=max_p,
                currency="COP",
                confidence=confidence,
                rationale=rationale,
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de IA no cumple el contrato de estimación.") from exc

    async def embed(self, text: str) -> list[float]:
        url = f"{self._base_url}/api/embeddings"
        payload = {
            "model": self._embed_model,
            "prompt": text,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    # Intento alternativo con endpoint /api/embed
                    alt_url = f"{self._base_url}/api/embed"
                    alt_resp = await client.post(alt_url, json={"model": self._embed_model, "input": text})
                    if alt_resp.status_code == 200:
                        embeddings = alt_resp.json().get("embeddings", [[]])[0]
                        return parse_embedding(embeddings)
                    raise AiServiceUnavailableError(f"Ollama embedding falló con código {response.status_code}")
                data = response.json()
                embedding = data.get("embedding", [])
                return parse_embedding(embedding)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("Fallo al obtener embedding de Ollama: %s", exc)
            raise AiServiceUnavailableError(
                "No se pudo generar embedding semántico mediante Ollama."
            ) from exc

    async def analyze_sentiment(self, review: Review) -> SentimentAnalysis:
        system = (
            "Eres un analizador de sentimiento de reseñas para Task It. "
            "Devuelve un JSON estrictamente con: "
            "'sentiment' ('POSITIVE' | 'NEUTRAL' | 'NEGATIVE'), "
            "'score' (float entre -1.0 y 1.0), "
            "'keywords' (lista de palabras clave en minúsculas), "
            "'summary' (resumen de 1 frase)."
        )
        prompt = (
            f"Calificación numérica: {review.rating}/5\n"
            f"Comentario del usuario: {review.comment}"
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            raw_sentiment = str(data.get("sentiment", "NEUTRAL")).upper()
            if raw_sentiment not in {s.value for s in SentimentLabel}:
                raw_sentiment = "POSITIVE" if review.rating >= 4 else ("NEGATIVE" if review.rating <= 2 else "NEUTRAL")
            score = float(data.get("score", (review.rating - 3) / 2.0))
            score = max(-1.0, min(1.0, score))
            keywords = [str(k) for k in data.get("keywords", [])]
            summary = str(data.get("summary", f"Reseña con calificación {review.rating}/5."))

            return SentimentAnalysis(
                review_id=review.review_id,
                sentiment=SentimentLabel(raw_sentiment),
                score=score,
                keywords=keywords,
                summary=summary,
            )
        except Exception as exc:
            raise AiServiceUnavailableError("Respuesta de IA no cumple el contrato de sentimiento.") from exc

    async def detect_anomalies(self, command: FraudCheckCommand) -> FraudAnalysis:
        system = (
            "Eres AI Shield, el sistema de seguridad y prevención de fraudes de Task It. "
            "Detecta fraudes, intentos de pago por fuera de la plataforma, estafas, acoso, spam o phishing. "
            "Devuelve un JSON con: "
            "'is_anomaly' (boolean), "
            "'risk_level' ('LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'), "
            "'anomaly_types' (lista que puede contener: 'FRAUD', 'HARASSMENT', 'SPAM', 'PHISHING'), "
            "'explanation' (explicación del análisis), "
            "'flagged_excerpt' (fragmento exacto o vacío si no hay anomalía)."
        )
        prompt = (
            f"Origen: {command.source.value}\n"
            f"Texto a inspeccionar:\n\"\"\"{command.text}\"\"\""
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

            explanation = str(data.get("explanation", "Texto analizado sin anomalías detectadas."))
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
            raise AiServiceUnavailableError("Respuesta de IA no cumple el contrato de AI Shield.") from exc

    async def suggest_profile_optimization(self, profile: ProviderProfile) -> ProfileOptimization:
        system = (
            "Eres un asesor de reputación profesional de Task It. "
            "Devuelve un JSON estrictamente con: "
            "'suggestions' (lista de consejos concretos para mejorar el perfil), "
            "'optimized_bio' (propuesta de biografía mejorada o null), "
            "'keywords' (lista de términos sugeridos para búsqueda)."
        )
        prompt = (
            f"Nombre prestador: {profile.display_name}\n"
            f"Bio actual: {profile.bio}\n"
            f"Habilidades actuales: {', '.join(profile.skills)}\n"
            f"Ubicación: {profile.location}\n"
            f"Categorías: {', '.join(c.value for c in profile.categories)}"
        )
        data = await self._post_generate(prompt=prompt, system=system)
        try:
            suggestions = [str(s) for s in data.get("suggestions", [])]
            if not suggestions:
                suggestions = ["Detalla más tus herramientas y años de experiencia."]
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
            raise AiServiceUnavailableError("Respuesta de IA no cumple el contrato de optimización de perfil.") from exc


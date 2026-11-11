"""Lectura defensiva de la salida del modelo."""

import json

from aita.domain.exceptions import AiServiceUnavailableError


def parse_model_payload(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise AiServiceUnavailableError("La IA devolvió una respuesta que no es JSON.")
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise AiServiceUnavailableError("La IA devolvió una respuesta que no es JSON.") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AiServiceUnavailableError("La IA devolvió una respuesta que no es JSON.") from exc
    if not isinstance(data, dict):
        raise AiServiceUnavailableError("La IA devolvió una respuesta que no es un objeto JSON.")
    return data


def parse_embedding(values: object) -> list[float]:
    if not isinstance(values, list) or not values:
        raise AiServiceUnavailableError("La IA no devolvió un embedding utilizable.")
    try:
        return [float(item) for item in values]
    except (TypeError, ValueError) as exc:
        raise AiServiceUnavailableError("La IA no devolvió un embedding utilizable.") from exc

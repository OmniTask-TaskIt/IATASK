"""Adaptadores de salida para proveedores de Inteligencia Artificial."""

from aita.infrastructure.outbound.ai.gemini_adapter import GeminiAiAdapter
from aita.infrastructure.outbound.ai.qwen_adapter import LocalQwenAiAdapter

__all__ = ["GeminiAiAdapter", "LocalQwenAiAdapter"]


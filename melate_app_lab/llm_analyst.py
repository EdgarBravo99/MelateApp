from __future__ import annotations

import json
from typing import Any, Callable

from .guardrails import validate_output_json
from .llm_provider import call_llm, get_llm_config


class LLMAnalystEngine:
    def __init__(self, provider_fn: Callable[[str, str | None], str | None] | None = None) -> None:
        self.provider_fn = provider_fn or call_llm

    def build_context(self, components: dict[str, Any]) -> str:
        trace = components.get("trace", {})
        postmortem = components.get("postmortem", {})
        stress = components.get("stress_review", {})
        history_summary = components.get("history_summary", {})
        lessons = components.get("memory_lessons", [])
        theses = components.get("recent_theses", [])
        
        context = {
            "trace_signature": trace.get("block_signature"),
            "trace_sum": trace.get("sum"),
            "captured_numbers": postmortem.get("captured_numbers"),
            "missed_numbers": postmortem.get("missed_numbers"),
            "repeated_anchors": stress.get("anchor_concentration", {}).get("repeated_numbers"),
            "history_total_draws": history_summary.get("total_draws"),
            "lessons_count": len(lessons),
            "theses_count": len(theses)
        }
        return json.dumps(context, indent=2)

    def review(self, components: dict[str, Any], memory_lessons: list[dict[str, Any]]) -> dict[str, str]:
        # Si el provider esta desactivado, pasamos directo al stub deterministico
        config = get_llm_config()
        if config["provider"] in ("disabled", "local_stub"):
            return self._fallback_stub(components, memory_lessons)

        system_prompt = (
            "Eres un analista tecnico postmortem. Tu tarea es generar una revision estructurada en JSON.\n"
            "REGLA CRITICA 1: NO DEBES incluir ningun termino o frase que rompa las reglas del sistema.\n"
            "En especifico, evita usar lenguaje que implique adivinacion, juego de azar, resultados futuros, o suposicion de eventos no ocurridos.\n"
            "Solo reporta sobre hechos ocurridos en los datos proporcionados (trace, capturados, no capturados).\n"
            "REGLA CRITICA 2: NO DEBES generar ni sugerir boletos o numeros nuevos.\n"
            "REGLA CRITICA 3: Devuelve estricta y unicamente un objeto JSON con las siguientes llaves (todas strings):\n"
            "- diagnosis_es\n"
            "- what_worked_es\n"
            "- what_was_missed_es\n"
            "- structural_reading_es\n"
            "- history_context_es\n"
            "- next_cycle_review_thesis_es\n"
            "- risk_notes_es\n"
            "- action_items_es\n"
            "- confidence_notes_es\n"
        )
        
        context_str = self.build_context(components)
        prompt = f"Analiza estos datos postmortem y genera el reporte JSON:\n{context_str}"
        
        try:
            response_text = self.provider_fn(prompt, system_prompt)
            if not response_text:
                return self._fallback_stub(components, memory_lessons)
                
            parsed = json.loads(response_text)
            
            # Verificar estructura minima
            required_keys = {
                "diagnosis_es", "what_worked_es", "what_was_missed_es",
                "structural_reading_es", "history_context_es",
                "next_cycle_review_thesis_es", "risk_notes_es"
            }
            if not required_keys.issubset(parsed.keys()):
                return self._fallback_stub(components, memory_lessons)

            # Para asegurarse de que no haya filtracion, pasamos solo valores validos al dict
            narrative = {
                "diagnosis_es": str(parsed.get("diagnosis_es", "")),
                "what_worked_es": str(parsed.get("what_worked_es", "")),
                "what_was_missed_es": str(parsed.get("what_was_missed_es", "")),
                "structural_reading_es": str(parsed.get("structural_reading_es", "")),
                "history_context_es": str(parsed.get("history_context_es", "")),
                "next_cycle_review_thesis_es": str(parsed.get("next_cycle_review_thesis_es", "")),
                "risk_notes_es": str(parsed.get("risk_notes_es", "")),
                "action_items_es": str(parsed.get("action_items_es", "")),
                "confidence_notes_es": str(parsed.get("confidence_notes_es", "")),
                "llm_provider": config["provider"],
                "llm_model": config["model"]
            }
            
            # Pasar por validate_output_json para garantizar guardrails.
            # Si rompe reglas, fallara o limpiara. Como aqui es un dict, validara sus values.
            # Si validate lanza excepcion, caemos al except y usamos fallback.
            validate_output_json(narrative)
            
            return narrative

        except Exception:
            return self._fallback_stub(components, memory_lessons)

    def _fallback_stub(self, components: dict[str, Any], memory_lessons: list[dict[str, Any]]) -> dict[str, str]:
        postmortem = components.get("postmortem", {})
        trace = components.get("trace", {})
        stress = components.get("stress_review", {})
        history_summary = components.get("history_summary") or {}
        
        captured = postmortem.get("captured_numbers", [])
        missed = postmortem.get("missed_numbers", [])
        repeated = stress.get("anchor_concentration", {}).get("repeated_numbers", [])
        
        memory_note = (
            f" Memoria local consultada: {len(memory_lessons)} lecciones recientes."
            if memory_lessons
            else " Memoria local sin lecciones previas para este contexto."
        )
        history_count = history_summary.get("total_draws") or history_summary.get("draw_count")
        history_note = (
            f" Historial local revisado: {history_count} registros."
            if history_count
            else " Historial local no cargado para esta revision."
        )
        return {
            "diagnosis_es": (
                "Diagnostico de revision: el set jugado capturo parte del rastro, "
                "pero dejo abierta una franja alta y un inicio bajo del resultado."
                + memory_note
            ),
            "what_worked_es": f"Funciono la captura de numeros {', '.join(map(str, captured))}.",
            "what_was_missed_es": f"No se capturaron {', '.join(map(str, missed))}.",
            "structural_reading_es": (
                f"Lectura estructural: suma {trace.get('sum')}, banda {trace.get('sum_band')}, "
                f"firma {trace.get('block_signature')} y anclas repetidas {repeated}."
            ),
            "history_context_es": (
                "Contexto historico descriptivo: se usa solo para comparar huellas ya registradas."
                + history_note
            ),
            "next_cycle_review_thesis_es": (
                "Tesis de revision siguiente ciclo: ampliar diversidad de firmas, "
                "revisar concentracion de anclas y documentar cobertura por bloques."
            ),
            "risk_notes_es": (
                "Notas de revision: evitar que anclas repetidas reduzcan diversidad del set "
                "y mantener el analisis como postmortem local."
            ),
            "llm_provider": "local_stub"
        }

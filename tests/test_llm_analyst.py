import json
import os
from unittest.mock import patch
from melate_app_lab.llm_analyst import LLMAnalystEngine
from melate_app_lab.evaluator_brain import brain_review
from melate_app_lab.historical_store import suggest_next_draw
import sqlite3

def test_llm_provider_disabled_uses_fallback():
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "disabled"}):
        engine = LLMAnalystEngine()
        res = engine.review({}, [])
        assert res["llm_provider"] == "local_stub"
        assert "Diagnostico de revision" in res["diagnosis_es"]


def test_llm_valid_mock_uses_llm_narrative():
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "openai_compatible", "MELATE_LLM_API_KEY": "secret"}):
        def mock_provider(prompt, system):
            return json.dumps({
                "diagnosis_es": "Test diagnosis LLM",
                "what_worked_es": "X",
                "what_was_missed_es": "Y",
                "structural_reading_es": "Z",
                "history_context_es": "W",
                "next_cycle_review_thesis_es": "A",
                "risk_notes_es": "B",
                "action_items_es": "C",
                "confidence_notes_es": "D"
            })
            
        engine = LLMAnalystEngine(provider_fn=mock_provider)
        res = engine.review({}, [])
        
        assert res["llm_provider"] == "openai_compatible"
        assert res["diagnosis_es"] == "Test diagnosis LLM"
        assert "secret" not in json.dumps(res)


def test_llm_invalid_json_uses_fallback():
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "openai_compatible"}):
        def mock_provider(prompt, system):
            return "This is not json"
            
        engine = LLMAnalystEngine(provider_fn=mock_provider)
        res = engine.review({}, [])
        
        assert res["llm_provider"] == "local_stub"


def test_llm_provider_error_uses_fallback():
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "openai_compatible"}):
        def mock_provider(prompt, system):
            raise Exception("Timeout or network error")
            
        engine = LLMAnalystEngine(provider_fn=mock_provider)
        res = engine.review({}, [])
        
        assert res["llm_provider"] == "local_stub"


def test_llm_guardrail_violation_uses_fallback():
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "openai_compatible"}):
        def mock_provider(prompt, system):
            # "predecir" is a forbidden word in guardrails usually
            return json.dumps({
                "diagnosis_es": "Vamos a predecir el futuro",
                "what_worked_es": "X",
                "what_was_missed_es": "Y",
                "structural_reading_es": "Z",
                "history_context_es": "W",
                "next_cycle_review_thesis_es": "A",
                "risk_notes_es": "B",
                "action_items_es": "C",
                "confidence_notes_es": "D"
            })
            
        engine = LLMAnalystEngine(provider_fn=mock_provider)
        res = engine.review({}, [])
        
        # Guardrails will raise ValueError, engine catches it and falls back
        assert res["llm_provider"] == "local_stub"
        assert "predecir" not in res["diagnosis_es"]


def test_brain_review_includes_metadata():
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "disabled"}):
        res = brain_review(4218, [1, 2, 3, 4, 5, 6], [[1, 2, 3, 4, 5, 6]])
        assert res.get("llm_provider") == "local_stub"


def test_suggest_next_draw_from_memory():
    conn = sqlite3.connect(":memory:")
    # Empty memory -> 4218
    assert suggest_next_draw(conn) == 4218
    
    # After 4218 -> 4219 (table already created by suggest_next_draw above)
    conn.execute("INSERT INTO historical_draws (game, draw, draw_date, numbers_json, sum, sum_band, block_signature, block_presence_signature) VALUES ('melate', 4218, '2026-05-28', '[1,2,3,4,5,6]', 21, 'Low', 'A', 'B')")
    assert suggest_next_draw(conn) == 4219


def test_prompt_has_no_literal_forbidden_words():
    engine = LLMAnalystEngine()
    # To check the prompt, we mock the provider to capture the system prompt
    captured_system = ""
    def mock_provider(prompt, system):
        nonlocal captured_system
        captured_system = system
        return json.dumps({"diagnosis_es": "A", "what_worked_es": "X", "what_was_missed_es": "Y", "structural_reading_es": "Z", "history_context_es": "W", "next_cycle_review_thesis_es": "A", "risk_notes_es": "B"})
        
    engine.provider_fn = mock_provider
    with patch.dict(os.environ, {"MELATE_LLM_PROVIDER": "openai_compatible"}):
        engine.review({}, [])
        
    lower_prompt = captured_system.lower()
    assert "predecir" not in lower_prompt.split()
    assert "apostar" not in lower_prompt.split()
    assert "ganar" not in lower_prompt.split()
    assert "probabilidad futura" not in lower_prompt

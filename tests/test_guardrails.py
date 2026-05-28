import pytest

from melate_app_lab.guardrails import validate_output_json, validate_text


@pytest.mark.parametrize("text", ["probabilidad", "ganador", "más probable"])
def test_validate_text_blocks_forbidden_terms(text):
    with pytest.raises(ValueError):
        validate_text(text)


@pytest.mark.parametrize("text", ["revisión", "huella", "tesis de revisión"])
def test_validate_text_allows_review_language(text):
    assert validate_text(text) == text


def test_validate_output_json_walks_nested_values():
    with pytest.raises(ValueError):
        validate_output_json({"nested": ["ganador"]})

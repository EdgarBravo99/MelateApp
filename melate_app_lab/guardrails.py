from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


FORBIDDEN_TERMS = [
    "predicción",
    "predecir",
    "probabilidad",
    "seguro",
    "garantizado",
    "certeza",
    "va a salir",
    "ganador",
    "apostar",
    "más probable",
    "mejor probabilidad",
    "win probability",
    "likely winner",
    "best pick",
]


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def validate_text(text: str) -> str:
    normalized = _normalize(text)
    for term in FORBIDDEN_TERMS:
        pattern = re.escape(_normalize(term))
        if re.search(rf"(?<!\w){pattern}(?!\w)", normalized):
            raise ValueError(f"Lenguaje no permitido detectado: {term}")
    return text


def validate_output_json(obj: Any) -> Any:
    if isinstance(obj, str):
        validate_text(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            validate_text(str(key))
            validate_output_json(value)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            validate_output_json(item)
    else:
        json.dumps(obj)
    return obj

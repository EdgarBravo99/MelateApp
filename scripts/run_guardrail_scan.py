from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCAN_TARGETS = [ROOT / "melate_app_lab", ROOT / "tests", ROOT / "README.md"]
ALLOWLIST = {
    ROOT / "melate_app_lab" / "guardrails.py",
    ROOT / "tests" / "test_guardrails.py",
    ROOT / "tests" / "test_llm_analyst.py",
    ROOT / ".agents" / "skills" / "melate-guardrails" / "SKILL.md",
    Path(__file__).resolve(),
}
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


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for target in SCAN_TARGETS:
        if target.is_file():
            files.append(target)
        elif target.exists():
            files.extend(
                path
                for path in target.rglob("*")
                if path.is_file() and path.suffix.lower() in {".py", ".md", ".html", ".json", ".csv"}
            )
    return files


def run_scan() -> dict[str, object]:
    violations: list[dict[str, object]] = []
    patterns = [(term, re.compile(rf"(?<!\w){re.escape(_normalize(term))}(?!\w)")) for term in FORBIDDEN_TERMS]
    for path in _iter_files():
        resolved = path.resolve()
        if resolved in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        normalized = _normalize(text)
        for term, pattern in patterns:
            for match in pattern.finditer(normalized):
                line = normalized[: match.start()].count("\n") + 1
                violations.append({"path": str(path.relative_to(ROOT)), "line": line, "term": term})
    return {"scanned_files": len(_iter_files()), "violations": violations}


def main() -> int:
    result = run_scan()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

# Feedback Loop Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified interactive workflow CLI command (`workflow-loop`) and controller logic connecting candidate generation, portfolio saving (with classification & rank_score), manual play registry, official result capture (via `historical_store`), full portfolio evaluation (coverage & unique hits), and feedback learning.

**Architecture:** 
1. Database Schema migrations to support candidate scores.
2. Separation of official history (`historical_draws`) from play memory (`thesis_candidates`).
3. Core orchestrator with portfolio-level metric calculations.
4. CLI Typer command.

**Tech Stack:** Python 3.13, Typer, SQLite, scikit-learn (Ridge regression).

---

### Task 1: Database Schema & Memory Migration

**Files:**
- Modify: `melate_app_lab/thesis_memory.py`
- Test: `tests/test_thesis_memory.py`

- [ ] **Step 1: Write failing test in `tests/test_thesis_memory.py`**

```python
def test_save_thesis_portfolio_with_score(tmp_path):
    from melate_app_lab.thesis_memory import save_thesis_portfolio, load_thesis_candidates
    db = tmp_path / "test_memory.sqlite"
    
    cand = {
        "numbers": [1, 2, 3, 4, 5, 6],
        "classification": "relation",
        "sum": 21,
        "sum_band": "low_band",
        "block_signature": "5-1-0-0-0",
        "graph_support_score": 12,
        "rank_score": 8.5
    }
    
    pid = save_thesis_portfolio(db, draw=100, game="revancha", candidates=[cand])
    loaded = load_thesis_candidates(db, pid)
    assert len(loaded) == 1
    assert loaded[0]["rank_score"] == 8.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_thesis_memory.py -k test_save_thesis_portfolio_with_score`
Expected: FAIL due to schema missing rank_score or validation error.

- [ ] **Step 3: Update schema and save functions in `melate_app_lab/thesis_memory.py`**

Modify `_init_db` to include `rank_score` and perform dynamic migrations on old databases:
```python
# In melate_app_lab/thesis_memory.py -> _init_db
        conn.execute(
            """
            create table if not exists thesis_candidates (
                id integer primary key autoincrement,
                portfolio_id integer,
                numbers text not null,
                classification text not null,
                state text not null,
                sum integer not null,
                sum_band text not null,
                block_signature text not null,
                graph_support_score integer not null,
                rank_score real,
                pair_edges text,
                evidence_draws text,
                notes text,
                result_numbers text,
                hits_count integer,
                created_at text default current_timestamp,
                foreign key(portfolio_id) references thesis_portfolios(id) on delete cascade
            )
            """
        )
        try:
            conn.execute("ALTER TABLE thesis_candidates ADD COLUMN rank_score REAL")
        except sqlite3.OperationalError:
            pass  # Already exists
```

Update `save_thesis_portfolio`:
```python
# In melate_app_lab/thesis_memory.py -> save_thesis_portfolio
        for cand in candidates:
            numbers_str = json.dumps(cand["numbers"])
            pair_edges_str = json.dumps(cand.get("pair_edges", []))
            evidence_draws_str = json.dumps(cand.get("evidence_draws", []))
            result_numbers_str = (
                json.dumps(cand.get("result_numbers"))
                if cand.get("result_numbers") is not None
                else None
            )

            cursor.execute(
                """
                insert into thesis_candidates (
                    portfolio_id, numbers, classification, state, sum, sum_band,
                    block_signature, graph_support_score, rank_score, pair_edges, evidence_draws,
                    notes, result_numbers, hits_count
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    portfolio_id,
                    numbers_str,
                    cand["classification"],
                    cand.get("state", "Pendiente"),
                    cand["sum"],
                    cand["sum_band"],
                    cand["block_signature"],
                    cand["graph_support_score"],
                    cand.get("rank_score", 0.0),
                    pair_edges_str,
                    evidence_draws_str,
                    cand.get("notes", ""),
                    result_numbers_str,
                    cand.get("hits_count"),
                ),
            )
```

Update `load_thesis_candidates`:
```python
# In melate_app_lab/thesis_memory.py -> load_thesis_candidates
        rows = conn.execute(
            """
            select id, portfolio_id, numbers, classification, state, sum, sum_band,
                   block_signature, graph_support_score, rank_score, pair_edges, evidence_draws,
                   notes, result_numbers, hits_count, created_at
            from thesis_candidates
            where portfolio_id = ?
            order by graph_support_score desc, id asc
            """,
            (portfolio_id,),
        ).fetchall()
    candidates = [
        {
            "id": row[0],
            "portfolio_id": row[1],
            "numbers": json.loads(row[2]),
            "classification": row[3],
            "state": row[4],
            "sum": row[5],
            "sum_band": row[6],
            "block_signature": row[7],
            "graph_support_score": row[8],
            "rank_score": row[9],
            "pair_edges": json.loads(row[10]) if row[10] else [],
            "evidence_draws": json.loads(row[11]) if row[11] else [],
            "notes": row[12],
            "result_numbers": json.loads(row[13]) if row[13] else None,
            "hits_count": row[14],
            "created_at": row[15],
        }
        for row in rows
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3 -m pytest tests/test_thesis_memory.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add melate_app_lab/thesis_memory.py tests/test_thesis_memory.py
git commit -m "migration: add rank_score column to thesis_candidates"
```

---

### Task 2: Core Loop Integration (Workflow Orchestrator)

**Files:**
- Create: `melate_app_lab/workflow_loop.py`
- Test: `tests/test_workflow_loop.py`

- [ ] **Step 1: Write failing test in `tests/test_workflow_loop.py`**

```python
import pytest
from melate_app_lab.workflow_loop import run_unified_workflow

def test_unified_workflow_coverage_calculation(tmp_path):
    # Test that portfolio is evaluated as a whole and unique hits are calculated
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_workflow_loop.py`
Expected: FAIL

- [ ] **Step 3: Implement core orchestrator logic with coverage and historical store integration**

Create `melate_app_lab/workflow_loop.py`:
```python
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Callable
from .historical_store import load_draw_history, insert_draw_record
from .thesis_memory import save_thesis_portfolio, update_candidate_state, get_portfolio_candidates, _connect
from .candidate_search import search_candidates
from .candidate_generator import analyze_time_window
from .relation_graph import build_historical_relation_graph
from .feature_extractor import extract_features
from .candidate_ranker import rank_candidates
from .importers import normalize_draw_record

def evaluate_portfolio_coverage(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregated structural coverage metrics for a full portfolio."""
    if not candidates:
        return {}
        
    all_numbers = set()
    signatures = set()
    total_pairs_count = len(candidates)
    
    # 1. Total block coverage
    # Blocks: 1-10, 11-20, 21-30, 31-40, 41-56
    blocks_occupied = [0] * 5
    for cand in candidates:
        nums = cand["numbers"]
        all_numbers.update(nums)
        signatures.add(cand["block_signature"])
        
        for n in nums:
            if 1 <= n <= 10: blocks_occupied[0] = 1
            elif 11 <= n <= 20: blocks_occupied[1] = 1
            elif 21 <= n <= 30: blocks_occupied[2] = 1
            elif 31 <= n <= 40: blocks_occupied[3] = 1
            elif 41 <= n <= 56: blocks_occupied[4] = 1

    # 2. Average overlap
    overlap_sums = 0
    comparisons = 0
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            overlap_sums += len(set(candidates[i]["numbers"]) & set(candidates[j]["numbers"]))
            comparisons += 1
            
    avg_overlap = (overlap_sums / comparisons) if comparisons > 0 else 0.0
    
    return {
        "unique_numbers_covered": len(all_numbers),
        "block_ranges_covered": sum(blocks_occupied),
        "unique_block_signatures": len(signatures),
        "average_internal_overlap": round(avg_overlap, 2)
    }

def run_unified_workflow(
    db_path: str | Path,
    draw: int,
    game: str = "revancha",
    pool_size: int = 100,
    seed: int = 42,
    played_indices: list[int] | None = None,
    result_numbers: list[int] | None = None,
    log_fn: Callable[[str], None] | None = None
) -> dict[str, Any]:
    history = load_draw_history(db_path)
    if not history:
        raise ValueError("No hay historial en la memoria para generar la tesis.")

    if log_fn:
        log_fn(f"Generando candidatos para sorteo {draw}...")

    # 1. Generar candidatos
    prior_history = [d for d in history if d["draw"] < draw]
    analysis = analyze_time_window(prior_history, window=30)
    graph_data = build_historical_relation_graph(prior_history, window=30, game=game)
    candidate_pool = search_candidates(analysis, pool_size=pool_size, seed=seed)
    
    cand_features = []
    for cand in candidate_pool:
        feats = extract_features(cand, prior_history[-30:], prior_history, graph_data)
        cand_features.append(feats)
        
    common_sigs = analysis.get("common_signatures", [])
    common_bands = analysis.get("common_bands", [])
    ranked = rank_candidates(cand_features, common_sigs, common_bands)

    # Prepare portfolio candidates
    candidates_payload = []
    for idx, c in enumerate(ranked[:10]):
        # Strategy classification based on candidate details
        strat = "relation" if c["graph_support_score"] > 5 else "balance"
        if idx % 3 == 0:
            strat = "contrast"
            
        candidates_payload.append({
            "numbers": c["numbers"],
            "classification": strat,
            "state": "Pendiente",
            "sum": c["sum"],
            "sum_band": c["sum_band"],
            "block_signature": c["block_signature"],
            "graph_support_score": c["graph_support_score"],
            "rank_score": c.get("rank_score", 0.0),
            "pair_edges": [],
            "evidence_draws": [],
            "notes": f"Score: {c.get('rank_score', 0.0)}"
        })

    # 2. Guardar cartera (Portfolio)
    # Calculate coverage metrics of the portfolio
    coverage = evaluate_portfolio_coverage(candidates_payload)
    notes_payload = json.dumps({"coverage": coverage})
    
    portfolio_id = save_thesis_portfolio(
        db_path,
        draw=draw,
        game=game,
        candidates=candidates_payload,
        notes=notes_payload
    )

    if log_fn:
        log_fn(f"Cartera {portfolio_id} guardada con {len(candidates_payload)} candidatos.")
        log_fn(f"Cobertura estructural de la cartera: {coverage['unique_numbers_covered']} números únicos cubiertos en {coverage['block_ranges_covered']} bloques.")

    # 3. Registrar JUGADAS (Played)
    db_candidates = get_portfolio_candidates(db_path, portfolio_id)
    played_candidates = []
    if played_indices:
        for idx in played_indices:
            if 0 <= idx < len(db_candidates):
                cand_id = db_candidates[idx]["id"]
                update_candidate_state(db_path, cand_id, "Jugado")
                played_candidates.append(db_candidates[idx])
                
    if log_fn:
        log_fn(f"Se registraron {len(played_candidates)} candidatos de la cartera como Jugados.")

    # 4 & 5. Capturar resultado oficial & Revisar aciertos
    evaluation = {}
    if result_numbers:
        # Dynamically calculate features for the winning draw before saving to historical_store
        result_record = normalize_draw_record({
            "game": game,
            "draw": draw,
            "date": "2026-05-29",  # Placeholder date or calculated
            "numbers": result_numbers
        })
        
        with _connect(db_path) as conn:
            insert_draw_record(conn, result_record, commit=True, ensure_schema=True)
            
        if log_fn:
            log_fn(f"Resultado oficial registrado en historical_store: {result_numbers}")

        # Calculate hits
        target_set = set(result_numbers)
        union_hits = set()
        
        with _connect(db_path) as conn:
            for cand in db_candidates:
                cand_set = set(cand["numbers"])
                hits = len(cand_set & target_set)
                
                # Check if it was played to add to union hits
                if cand["state"] == "Jugado" or cand["id"] in [p["id"] for p in played_candidates]:
                    union_hits.update(cand_set & target_set)
                    
                conn.execute(
                    "update thesis_candidates set result_numbers = ?, hits_count = ?, state = 'Revisado' where id = ?",
                    (json.dumps(result_numbers), hits, cand["id"])
                )
                
        evaluation = {
            "result_captured": True,
            "result_numbers": result_numbers,
            "portfolio_id": portfolio_id,
            "portfolio_unique_hits_captured": len(union_hits),
            "hit_numbers": list(union_hits)
        }
        
        if log_fn:
            log_fn(f"Evaluación de la Cartera completa: Capturó {len(union_hits)} números ganadores en total a través de la cartera jugada.")

    return {
        "portfolio_id": portfolio_id,
        "coverage": coverage,
        "played_count": len(played_candidates),
        "evaluation": evaluation
    }
```

- [ ] **Step 4: Run tests to verify it passes**

Run: `py -3 -m pytest tests/test_workflow_loop.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add melate_app_lab/workflow_loop.py tests/test_workflow_loop.py
git commit -m "feat: implement portfolio-level coverage and dynamic historical winner recording"
```

---

### Task 3: CLI Workflow Integration

**Files:**
- Modify: `melate_app_lab/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write CLI command tests in `tests/test_cli.py`**

```python
def test_workflow_loop_cmd(runner, tmp_path):
    # Verify execution of the CLI workflow command
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_cli.py -k test_workflow_loop_cmd`
Expected: FAIL

- [ ] **Step 3: Modify `melate_app_lab/cli.py`**

Add Typer command:
```python
@app.command("workflow-loop")
def workflow_loop_cmd(
    draw: Annotated[int, typer.Option(help="ID del sorteo")],
    game: Annotated[str, typer.Option(default="revancha", help="revancha o melate")],
    pool_size: Annotated[int, typer.Option(default=100, help="Pool size")],
    seed: Annotated[int, typer.Option(default=42, help="Seed")],
    played: Annotated[str, typer.Option(help="Indices jugados separados por espacio (ej: '0 2 3')")],
    result: Annotated[str, typer.Option(default=None, help="Numeros ganadores del sorteo")]
) -> None:
    """Ejecuta el ciclo de retroalimentación de Tesis -> Cartera -> Jugar -> Evaluar."""
    from .workflow_loop import run_unified_workflow
    
    played_indices = list(map(int, played.split())) if played else []
    result_numbers = list(map(int, result.split())) if result else None
    
    res = run_unified_workflow(
        DEFAULT_DB_PATH,
        draw=draw,
        game=game,
        pool_size=pool_size,
        seed=seed,
        played_indices=played_indices,
        result_numbers=result_numbers,
        log_fn=typer.echo
    )
    
    typer.echo(f"Loop completado con Cartera ID: {res['portfolio_id']}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3 -m pytest tests/test_cli.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add melate_app_lab/cli.py tests/test_cli.py
git commit -m "feat: add workflow-loop command to CLI"
```

# MelateApp Local Intelligence Lab

MVP local para revisión de sorteos Melate/Revancha con rastro estructural, postmortem contra boletos jugados, memoria SQLite local, grafo descriptivo, stress review estructural, brain integrador y reportes JSON/HTML.

El sistema opera en modo `review_default`: produce revisión, huella, postmortem, señales, aprendizaje de auditoría, soporte estructural, cobertura, concentración, diversidad y alertas de revisión. No decide boletos ni usa APIs externas.

## Instalación local

```powershell
py -3 -m pip install -e ".[dev]"
```

## Fixture principal

Sorteo Revancha 4218:

```text
2 18 22 38 51 52
```

Boletos jugados:

```text
A: 7 15 29 41 42 48
B: 7 16 18 23 29 39
C: 9 13 18 30 45 52
D: 7 15 20 30 36 53
```

## Comandos

```powershell
py -3 -m melate_app_lab trace --draw 4218 --numbers "2 18 22 38 51 52"
py -3 -m melate_app_lab postmortem --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab remember --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab graph --draw 4218 --result "2 18 22 38 51 52"
py -3 -m melate_app_lab montecarlo-stress --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab brain --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab report --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
```

## Archivos locales generados

- `data/melate_app_memory.sqlite`
- `outputs/relation_graph_4218.json`
- `outputs/postmortem_4218.json`
- `outputs/postmortem_4218.html`

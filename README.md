# MelateApp Local Intelligence Lab

Aplicacion local para revision de sorteos Melate/Revancha en Windows. Incluye rastro estructural, postmortem contra boletos jugados, memoria SQLite local, historial importado, grafo descriptivo optimizado, stress review estructural, brain integrador, reportes JSON/HTML/CSV y una interfaz de escritorio con PySide6.

El sistema opera en modo `review_default`: produce revision, huella, postmortem, senales, aprendizaje de auditoria, soporte estructural, cobertura, concentracion, diversidad, diagnostico y alertas de revision. No decide boletos ni usa APIs externas.

## Instalacion local

```powershell
py -3 -m pip install -e ".[dev]"
```

Extras opcionales:

```powershell
py -3 -m pip install -e ".[desktop]"
py -3 -m pip install -e ".[desktop,build]"
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

## CLI

```powershell
py -3 -m melate_app_lab trace --draw 4218 --numbers "2 18 22 38 51 52"
py -3 -m melate_app_lab postmortem --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab remember --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab graph --draw 4218 --result "2 18 22 38 51 52"
py -3 -m melate_app_lab montecarlo-stress --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab brain --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab report --draw 4218 --result "2 18 22 38 51 52" --played "7 15 29 41 42 48" "7 16 18 23 29 39" "9 13 18 30 45 52" "7 15 20 30 36 53"
py -3 -m melate_app_lab import-history --file data/samples/revancha_4218.csv
py -3 -m melate_app_lab history-summary
py -3 -m melate_app_lab guardrail-scan
py -3 -m melate_app_lab build-info
```

## Desktop

La interfaz local se abre con:

```powershell
py -3 -m melate_app_lab desktop
```

La ventana incluye sidebar, secciones de analisis, cards de metricas, botones de ejecucion, panel de resultados, consola interna y barra de progreso. Las tareas se ejecutan dentro de la app mediante worker local.

## Build Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

El build usa PyInstaller y deja artefactos en `dist/`, que no se versiona.

## Archivos locales generados

- `data/melate_app_memory.sqlite`
- `outputs/relation_graph_4218.json`
- `outputs/postmortem_4218.json`
- `outputs/postmortem_4218.html`
- `outputs/postmortem_4218.csv`

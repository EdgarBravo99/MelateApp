from __future__ import annotations

import sys
from pathlib import Path

# Try importing dependencies
try:
    import pytest
except ImportError:
    print("Error: pytest no está instalado. Instálalo con 'pip install pytest'.")
    sys.exit(1)

try:
    import PyInstaller.__main__
except ImportError:
    print("Error: PyInstaller no está instalado. Instálalo con 'pip install pyinstaller'.")
    sys.exit(1)

from scripts.run_guardrail_scan import run_scan


def main() -> int:
    print("Iniciando validaciones previas al build...")

    # 1. Run pytest
    print("Ejecutando pruebas unitarias...")
    pytest_ret = pytest.main(["-v", "tests"])
    if pytest_ret != 0:
        print("Error: Las pruebas unitarias fallaron. Corrige los errores antes de compilar.")
        return int(pytest_ret)
    print("Pruebas unitarias aprobadas.")

    # 2. Run guardrail scan
    print("Ejecutando escaneo de guardrails...")
    scan_res = run_scan()
    violations = scan_res.get("violations", [])
    if violations:
        print("Error: Se detectaron violaciones de guardrails en los siguientes archivos:")
        for v in violations:
            print(f"  - {v['path']}:{v['line']} (término: '{v['term']}')")
        return 1
    print("Escaneo de guardrails limpio. 0 violaciones detectadas.")

    # 3. Create resources folder if it doesn't exist
    ROOT = Path(__file__).resolve().parent.parent
    resources_path = ROOT / "resources"
    resources_path.mkdir(parents=True, exist_ok=True)

    # 4. Run PyInstaller
    print("Iniciando compilación con PyInstaller...")

    pyinstaller_args = [
        "--noconfirm",
        "--name=MelateApp",
        "--windowed",
        "--collect-all=PySide6",
        f"--add-data={resources_path};resources",
        str(ROOT / "melate_app_lab" / "desktop_app.py"),
    ]

    try:
        PyInstaller.__main__.run(pyinstaller_args)
        print("Compilación completada exitosamente.")
        print(f"El ejecutable portable está disponible en: {ROOT / 'dist' / 'MelateApp'}")
        return 0
    except Exception as e:
        print(f"Error durante la compilación con PyInstaller: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

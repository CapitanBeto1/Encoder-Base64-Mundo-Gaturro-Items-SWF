"""Arma el instalador de MG Items para Windows.

1. Descarga FFDec y Java a vendor/ (scripts/obtener_binarios.py).
2. Arma el programa con PyInstaller en dist/MGItems (carpeta con MGItems.exe, sin consola).
3. Si está Inno Setup 6, arma dist/MGItems-Setup-<versión>.exe con instalador/mgitems.iss.

Uso (desde la raíz del repo, con el entorno de desarrollo):
    .venv/Scripts/python scripts/armar_instalador.py
"""

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist"
BUILD = RAIZ / "build"
SCRIPT_INNO = RAIZ / "instalador" / "mgitems.iss"


def version() -> str:
    with open(RAIZ / "pyproject.toml", "rb") as archivo:
        return tomllib.load(archivo)["project"]["version"]


def armar_programa() -> Path:
    import PyInstaller.__main__

    datos = {
        RAIZ / "src" / "mgitems" / "ui": "mgitems/ui",
        RAIZ / "src" / "mgitems" / "datos": "mgitems/datos",
        RAIZ / "vendor" / "ffdec": "vendor/ffdec",
        RAIZ / "vendor" / "java": "vendor/java",
    }
    argumentos = [
        str(RAIZ / "src" / "mgitems" / "__main__.py"),
        "--name", "MGItems",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(RAIZ / "src"),
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
    ]
    for origen, destino in datos.items():
        argumentos += ["--add-data", f"{origen}{os.pathsep}{destino}"]
    PyInstaller.__main__.run(argumentos)
    return DIST / "MGItems"


def iscc() -> Path | None:
    candidatos = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    encontrado = shutil.which("iscc")
    return Path(encontrado) if encontrado else next((c for c in candidatos if c.is_file()), None)


def armar_instalador(programa: Path) -> Path | None:
    compilador = iscc()
    if compilador is None:
        print("No se encontró Inno Setup 6: se armó solo la carpeta del programa.")
        print("Para el instalador, instalá Inno Setup 6 (jrsoftware.org) y volvé a correr este script.")
        return None
    subprocess.run(
        [str(compilador), f"/DVersion={version()}", f"/DPrograma={programa}", f"/O{DIST}", str(SCRIPT_INNO)],
        check=True,
    )
    return DIST / f"MGItems-Setup-{version()}.exe"


def main() -> None:
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "obtener_binarios.py")], check=True)
    programa = armar_programa()
    print(f"Programa: {programa / 'MGItems.exe'}")
    instalador = armar_instalador(programa)
    if instalador:
        print(f"Instalador: {instalador}")


if __name__ == "__main__":
    main()

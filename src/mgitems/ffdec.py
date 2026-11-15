"""FFDec (JPEXS Free Flash Decompiler): cómo encontrarlo y ejecutarlo.

Lo usan las imágenes de los Items y el truqueo de Prendas. Se busca en `vendor/`
(o en la carpeta del programa instalado) y con el Java incluido o el del sistema.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


class FFDecNoDisponible(Exception):
    """Falta Java o FFDec."""


# Java para un trabajo corto (cada llamada es una exportación de segundos): sin su compilador más pesado (C2), que en
# eso gasta más CPU de la que ahorra, y con el recolector de memoria simple, que pide mucha menos. Medido con el Java
# incluido: tarda lo mismo, con un 40 a 75 % menos de CPU y entre 100 MB y 1 GB menos de memoria.
_OPCIONES_DE_JAVA = ("-XX:TieredStopAtLevel=1", "-XX:+UseSerialGC")


class FFDec:
    _SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def __init__(self, java: Path | None = None, jar: Path | None = None):
        self._java = java
        self._jar = jar

    def programas(self) -> tuple[Path, Path]:
        """(java, ffdec-cli.jar). Lanza FFDecNoDisponible si falta alguno."""
        vendor = carpeta_vendor()
        java = self._java or _java_incluido(vendor) or (Path(p) if (p := shutil.which("java")) else None)
        jar = self._jar or vendor / "ffdec" / "ffdec-cli.jar"
        if java is None:
            raise FFDecNoDisponible("No se encontró Java")
        if not jar.is_file():
            raise FFDecNoDisponible("No se encontró FFDec")
        return java, jar

    def ejecutar(self, *argumentos: str, tiempo_maximo: int = 300) -> subprocess.CompletedProcess:
        java, jar = self.programas()
        return subprocess.run(
            [str(java), *_OPCIONES_DE_JAVA, "-jar", str(jar), *argumentos],
            capture_output=True, timeout=tiempo_maximo, env=_entorno_java(), creationflags=self._SIN_VENTANA,
        )


def _entorno_java() -> dict[str, str]:
    """Variables para Java: FFDec lee los JPEG de 4 componentes con un lector propio que usa un
    módulo interno de Java; desde Java 9 hay que habilitarlo o el primero de esos JPEG aborta
    toda la exportación. `JDK_JAVA_OPTIONS` la leen Java 9+ y Java 8 la ignora."""
    entorno = dict(os.environ)
    permiso = "--add-exports=java.desktop/com.sun.imageio.plugins.jpeg=ALL-UNNAMED"
    entorno["JDK_JAVA_OPTIONS"] = f"{entorno.get('JDK_JAVA_OPTIONS', '')} {permiso}".strip()
    return entorno


def carpeta_vendor() -> Path:
    """`vendor/` del proyecto, o la carpeta del programa instalado (PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "vendor"
    return Path(__file__).resolve().parent.parent.parent / "vendor"


def _java_incluido(vendor: Path) -> Path | None:
    for nombre in ("java.exe", "java"):
        candidato = vendor / "java" / "bin" / nombre
        if candidato.is_file():
            return candidato
    return None

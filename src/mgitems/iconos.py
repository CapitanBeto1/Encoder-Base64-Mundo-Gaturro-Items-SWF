"""Imágenes de los Items: el primer cuadro de cada símbolo, exportado a PNG con FFDec.

Se exportan una vez por versión de cada SWF de assets y quedan en una carpeta por
SWF: `<carpeta>/<swf>/<Clase>.png`, con un archivo `version` que dice de qué
versión del SWF salieron.
"""

import base64
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ZOOM = 2


class ExportadorNoDisponible(Exception):
    """Falta Java o FFDec."""


def version_de(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


class ExportadorFFDec:
    """Exporta el primer cuadro de sprites elegidos por id, en una sola llamada a FFDec."""

    _SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def __init__(self, java: Path | None = None, ffdec: Path | None = None):
        self._java = java
        self._ffdec = ffdec

    def _programas(self) -> tuple[Path, Path]:
        vendor = _carpeta_vendor()
        java = self._java or _java_incluido(vendor) or (Path(p) if (p := shutil.which("java")) else None)
        ffdec = self._ffdec or vendor / "ffdec" / "ffdec-cli.jar"
        if java is None:
            raise ExportadorNoDisponible("No se encontró Java")
        if not ffdec.is_file():
            raise ExportadorNoDisponible("No se encontró FFDec")
        return java, ffdec

    def exportar(self, swf: Path, simbolos: dict[int, str], destino: Path) -> None:
        """Escribe `destino/<Clase>.png` para cada símbolo (id → nombre de clase) que se pueda dibujar."""
        if not simbolos:
            return
        java, ffdec = self._programas()
        ids = ",".join(str(i) for i in simbolos)
        cuadros = ",".join(f"{i}:1" for i in simbolos)
        with tempfile.TemporaryDirectory(prefix="mgitems-") as temporal:
            comando = [
                str(java), "-jar", str(ffdec),
                "-selectid", ids, "-select", cuadros, "-zoom", str(ZOOM),
                "-format", "sprite:png", "-export", "sprite", temporal, str(swf),
            ]
            subprocess.run(comando, capture_output=True, timeout=300, creationflags=self._SIN_VENTANA)
            # FFDec deja cada sprite en `DefineSprite_<id>_<clase>/1.png`.
            destino.mkdir(parents=True, exist_ok=True)
            for carpeta in Path(temporal).iterdir():
                partes = carpeta.name.split("_", 2)
                png = carpeta / "1.png"
                if len(partes) >= 2 and partes[1].isdigit() and int(partes[1]) in simbolos and png.is_file():
                    shutil.move(png, destino / f"{simbolos[int(partes[1])]}.png")


class IconosItems:
    def __init__(self, carpeta: Path, exportador: ExportadorFFDec):
        self._carpeta = carpeta
        self._exportador = exportador

    def _carpeta_swf(self, swf: str) -> Path:
        return self._carpeta.joinpath(*swf.split("/"))

    def listos(self, swf: str, version: str) -> bool:
        marca = self._carpeta_swf(swf) / "version"
        return marca.is_file() and marca.read_text(encoding="utf-8").strip() == version

    def preparar(self, swf: str, data: bytes, simbolos: dict[int, str]) -> None:
        """Exporta las imágenes de los Items (id → clase) si no están para esta versión del SWF."""
        version = version_de(data)
        if self.listos(swf, version):
            return
        carpeta = self._carpeta_swf(swf)
        if carpeta.exists():
            shutil.rmtree(carpeta)
        with tempfile.TemporaryDirectory(prefix="mgitems-") as temporal:
            archivo = Path(temporal) / "assets.swf"
            archivo.write_bytes(data)
            self._exportador.exportar(archivo, simbolos, carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "version").write_text(version, encoding="utf-8")

    def icono(self, ruta_item: str) -> str | None:
        """La imagen de un Item como data URL PNG, o None si no está exportada."""
        swf, _, clase = ruta_item.rpartition(".")
        png = self._carpeta_swf(swf) / f"{clase}.png"
        try:
            return "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode("ascii")
        except OSError:
            return None


def _carpeta_vendor() -> Path:
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

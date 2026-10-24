"""Imágenes de los Items: el primer cuadro de cada símbolo, exportado a PNG con FFDec.

Se exportan una vez por versión de cada SWF de assets y quedan en una carpeta por
SWF: `<carpeta>/<swf>/<Clase>.png`, con un archivo `version` que dice de qué
versión del SWF salieron.
"""

import base64
import hashlib
import shutil
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDec

ZOOM = 2
# Qué se exporta de cada SWF. Si cambia, las imágenes guardadas se vuelven a exportar aunque el SWF sea el mismo.
CONTENIDO = "items+piezas"


def version_de(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


class ExportadorFFDec:
    """Exporta el primer cuadro de sprites elegidos por id, en una sola llamada a FFDec."""

    def __init__(self, ffdec: FFDec | None = None):
        self._ffdec = ffdec or FFDec()

    def exportar(self, swf: Path, simbolos: dict[int, str], destino: Path) -> None:
        """Escribe `destino/<Clase>.png` para cada símbolo (id → nombre de clase) que se pueda dibujar."""
        if not simbolos:
            return
        ids = ",".join(str(i) for i in simbolos)
        cuadros = ",".join(f"{i}:1" for i in simbolos)
        with tempfile.TemporaryDirectory(prefix="mgitems-") as temporal:
            self._ffdec.ejecutar(
                "-selectid", ids, "-select", cuadros, "-zoom", str(ZOOM),
                "-format", "sprite:png", "-export", "sprite", temporal, str(swf),
            )
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
        version = f"{version_de(data)} {CONTENIDO}"
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

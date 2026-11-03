"""Fondos: objetos de la casa que muestran, de los cuadros de su dibujo, el que se elija (pestaña Fondos).

Algunos dibujos del juego tienen varios cuadros y se quedan quietos en el primero (`stop()`), como
`socialNetBackgrounds.SocialNetBackgrounds`, 23 fondos de los que el juego solo usa uno por vez (en el perfil).
Puesto en la casa con el comportamiento `painting` del juego (`npc/painting.npc`), el objeto muestra el cuadro
guardado en su atributo `frame`, para todos los que entren, y el dueño lo cambia tocándolo (ver ADR 0007).
Probado en el juego: lo ven los demás y sigue al volver a entrar.

La lista de los que sirven la arma `scripts/armar_fondos.py`. Los cuadros se exportan con FFDec una vez por
versión del SWF, para mostrarlos al elegir.
"""

import base64
import hashlib
import io
import json
import re
import shutil
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDec
from mgitems.swf import leer_simbolos

ARCHIVO_FONDOS = Path(__file__).parent / "datos" / "fondos.json"
COMPORTAMIENTO = "painting"
# Más cuadros son animaciones largas, no fondos; y exportarlos tardaría mucho.
MAXIMO_CUADROS = 60
# El tamaño más grande de las vistas previas de cada cuadro (en píxeles).
LADO_VISTA = 260

_CUADRO_1 = re.compile(r"function\s+frame1\s*\(\s*\)[^{]*\{(.*?)\n[ \t]*\}", re.S)


def frena_en_el_primer_cuadro(codigo: str) -> bool:
    """Si el código AS3 de la clase la deja quieta en el primer cuadro (`stop()` en `frame1`)."""
    cuerpo = _CUADRO_1.search(codigo)
    return bool(cuerpo) and re.search(r"\bstop\s*\(\s*\)", cuerpo.group(1)) is not None


class Fondos:
    """Los objetos que sirven de fondo que trae el programa: `{"fondos": {"swf.clase": cuadros}}`."""

    def __init__(self, archivo: Path = ARCHIVO_FONDOS):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        self._fondos: dict[str, int] = datos.get("fondos", {})

    def todos(self) -> dict[str, int]:
        return self._fondos

    def cuadros(self, ruta: str) -> int | None:
        return self._fondos.get(ruta)


class CuadrosFFDec:
    """Las vistas previas de cada cuadro del dibujo de una clase, exportadas con FFDec y guardadas en
    `<carpeta>/<swf>/<clase>/<n>.png` (con un archivo `version`). Cada cuadro se recorta a lo que tiene dibujado:
    en algunos dibujos un cuadro es mucho más ancho que los otros y, recortados juntos, los demás quedaban chiquitos."""

    def __init__(self, carpeta: Path, ffdec: FFDec | None = None):
        self._carpeta = carpeta
        self._ffdec = ffdec or FFDec()

    def cuadros(self, swf: str, clase: str, data: bytes) -> list[str]:
        """Data URL PNG de cada cuadro, en orden (el primero es el cuadro 1)."""
        carpeta = self._carpeta.joinpath(*swf.split("/"), clase)
        version = hashlib.sha1(data).hexdigest()
        marca = carpeta / "version"
        if not (marca.is_file() and marca.read_text(encoding="utf-8").strip() == version):
            self._exportar(data, clase, carpeta)
            marca.write_text(version, encoding="utf-8")
        archivos = sorted(carpeta.glob("*.png"), key=lambda a: int(a.stem))
        return ["data:image/png;base64," + base64.b64encode(a.read_bytes()).decode("ascii") for a in archivos]

    def _exportar(self, data: bytes, clase: str, carpeta: Path) -> None:
        from PIL import Image

        ids = [i for i, c in leer_simbolos(data) if c == clase]
        if not ids:
            raise ValueError(f"{clase} no está en el SWF")
        if carpeta.exists():
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True)
        with tempfile.TemporaryDirectory(prefix="mgitems-", ignore_cleanup_errors=True) as temporal:
            archivo = Path(temporal) / "assets.swf"
            archivo.write_bytes(data)
            salida = Path(temporal) / "cuadros"
            self._ffdec.ejecutar("-selectid", str(ids[0]), "-format", "sprite:png", "-export", "sprite",
                                 str(salida), str(archivo))
            pngs = sorted(salida.rglob("*.png"), key=lambda a: int(a.stem) if a.stem.isdigit() else 0)
            imagenes = [Image.open(p).convert("RGBA") for p in pngs if p.stem.isdigit()]
            if not imagenes:
                raise OSError(f"FFDec no exportó los cuadros de {clase}")
            for n, imagen in enumerate(imagenes, 1):
                recorte = imagen.crop(imagen.getbbox() or (0, 0, *imagen.size))
                recorte.thumbnail((LADO_VISTA, LADO_VISTA))
                bytes_png = io.BytesIO()
                recorte.save(bytes_png, "PNG")
                (carpeta / f"{n}.png").write_bytes(bytes_png.getvalue())

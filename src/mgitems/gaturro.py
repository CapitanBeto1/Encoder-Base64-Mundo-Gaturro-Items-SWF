"""Las Piezas de un Look puestas en el anclaje de su Parte del cuerpo (ADR 0003).

Todavía sin el cuerpo del Gaturro: tiene que ser idéntico al del juego y no hay una fuente.

Cada Pieza es el primer cuadro de su símbolo exportado a SVG con FFDec, que deja el punto
de anclaje de la Pieza en el `<g transform>` de afuera. Se coloca en el anclaje de su Parte
del cuerpo, en el orden de capas del cuerpo.
"""

import re

from mgitems.iconos import IconosItems

# Punto de anclaje de cada Parte del cuerpo, en coordenadas del juego (el torso está en 0,0).
# Brazo, pierna y pie van dos veces: la segunda, reflejada.
ANCLAS: dict[str, list[tuple[float, float, bool]]] = {
    "clothBack": [(0, 0, False)],
    "leg": [(-7, 12, False), (7, 12, True)],
    "foot": [(-9, 27, False), (9, 27, True)],
    "cloth": [(0, 0, False)],
    "neck": [(0, -14, False)],
    "arm": [(-13, -10, False), (13, -10, True)],
    "grip": [(-15, 6, False)],
    "hairs": [(0, -48, False)],
    "mouths": [(0, -36, False)],
    "accesories": [(0, -50, False)],
    "accesories2": [(0, -50, False)],
    "hats": [(0, -70, False)],
    "gripFore": [(15, 6, False)],
}

# Orden de dibujo, de atrás hacia adelante.
ORDEN = ["clothBack", "leg", "foot", "cloth", "neck", "arm", "grip", "hairs", "mouths", "accesories", "accesories2",
         "hats", "gripFore"]

_ANCLAJE_FFDEC = re.compile(r'<g transform="matrix\(1\.0, 0\.0, 0\.0, 1\.0, -?[\d.]+, -?[\d.]+\)">(?P<contenido>.*?)</g>\s*<defs>', re.S)
_DEFS = re.compile(r"<defs>(?P<defs>.*)</defs>", re.S)
_ID = re.compile(r'\bid="([^"]+)"')
_REFERENCIA = re.compile(r'(href="#|url\(#)([^")]+)')


def _pieza(svg: str, prefijo: str) -> tuple[str, str] | None:
    """(contenido con el punto de anclaje en 0,0, defs), con ids únicos; None si no tiene la forma de FFDec."""
    svg = _ID.sub(lambda m: f'id="{prefijo}{m.group(1)}"', svg)
    svg = _REFERENCIA.sub(lambda m: f"{m.group(1)}{prefijo}{m.group(2)}", svg)
    contenido = _ANCLAJE_FFDEC.search(svg)
    if not contenido:
        return None
    defs = _DEFS.search(svg)
    return contenido.group("contenido"), defs.group("defs") if defs else ""


def componer(piezas: dict[str, str]) -> str:
    """El SVG del Gaturro con `piezas` (Parte del cuerpo → SVG exportado por FFDec) puestas."""
    capas, defs = [], []
    for n, capa in enumerate(ORDEN):
        pieza = _pieza(piezas[capa], f"p{n}_") if capa in piezas else None
        if pieza is None:
            continue
        contenido, definiciones = pieza
        defs.append(definiciones)
        for x, y, espejo in ANCLAS[capa]:
            escala = " scale(-1,1)" if espejo else ""
            capas.append(f'<g data-parte="{capa}" transform="translate({x},{y}){escala}">{contenido}</g>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns:ffdec="https://www.free-decompiler.com/flash" viewBox="-70 -105 140 145">'
            f'<defs>{"".join(defs)}</defs>{"".join(capas)}</svg>')


class ImagenesPiezas(IconosItems):
    """El primer cuadro de cada Pieza en SVG (con su punto de anclaje), una vez por versión de su SWF."""

    FORMATO = "svg"

    def svg(self, ruta_pieza: str) -> str | None:
        swf, _, clase = ruta_pieza.rpartition(".")
        try:
            return (self._carpeta_swf(swf) / f"{clase}.svg").read_text(encoding="utf-8")
        except OSError:
            return None

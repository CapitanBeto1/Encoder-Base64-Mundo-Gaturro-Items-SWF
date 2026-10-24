"""El Gaturro del editor de Looks: un cuerpo propio en SVG con las Piezas reales encima (ADR 0003).

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

COLOR_PELAJE = "#f7a731"
_PANZA = "#fff3d6"
_BORDE = "#6b3d0c"


def _cuerpo(color: str) -> dict[str, str]:
    """Las partes del cuerpo propio, para intercalar con las Piezas."""
    trazo = f'stroke="{_BORDE}" stroke-width="1.2"'
    return {
        "cola": f'<path d="M12 8 Q34 6 30 -14 Q28 -24 34 -26" fill="none" stroke="{_BORDE}" stroke-width="7" stroke-linecap="round"/>'
                f'<path d="M12 8 Q34 6 30 -14 Q28 -24 34 -26" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round"/>',
        "piernas": f'<rect x="-11" y="10" width="8" height="15" rx="3" fill="{color}" {trazo}/>'
                   f'<rect x="3" y="10" width="8" height="15" rx="3" fill="{color}" {trazo}/>',
        "pies": f'<ellipse cx="-10" cy="26" rx="8" ry="4.5" fill="{color}" {trazo}/>'
                f'<ellipse cx="10" cy="26" rx="8" ry="4.5" fill="{color}" {trazo}/>',
        "torso": f'<ellipse cx="0" cy="0" rx="15" ry="16" fill="{color}" stroke="{_BORDE}" stroke-width="1.4"/>'
                 f'<ellipse cx="0" cy="3" rx="9" ry="10" fill="{_PANZA}"/>',
        "brazos": f'<rect x="-19" y="-12" width="7" height="18" rx="3.5" fill="{color}" {trazo}/>'
                  f'<rect x="12" y="-12" width="7" height="18" rx="3.5" fill="{color}" {trazo}/>'
                  f'<circle cx="-15.5" cy="6" r="4" fill="{color}" {trazo}/>'
                  f'<circle cx="15.5" cy="6" r="4" fill="{color}" {trazo}/>',
        "cabeza": f'<path d="M-30 -66 L-26 -92 L-10 -76 Z M30 -66 L26 -92 L10 -76 Z" fill="{color}" stroke="{_BORDE}" stroke-width="1.4" stroke-linejoin="round"/>'
                  '<path d="M-25 -70 L-24 -85 L-15 -76 Z M25 -70 L24 -85 L15 -76 Z" fill="#f4b7a8"/>'
                  f'<ellipse cx="0" cy="-46" rx="34" ry="30" fill="{color}" stroke="{_BORDE}" stroke-width="1.6"/>'
                  f'<ellipse cx="0" cy="-34" rx="17" ry="11" fill="{_PANZA}"/>'
                  '<ellipse cx="-11" cy="-52" rx="7" ry="9" fill="#fff" stroke="#3a2208" stroke-width="1"/>'
                  '<ellipse cx="11" cy="-52" rx="7" ry="9" fill="#fff" stroke="#3a2208" stroke-width="1"/>'
                  '<circle cx="-9.5" cy="-50" r="3.4" fill="#2a1a08"/><circle cx="9.5" cy="-50" r="3.4" fill="#2a1a08"/>'
                  '<ellipse cx="0" cy="-40" rx="4" ry="2.8" fill="#c0533a"/>'
                  '<path d="M0 -37 Q-4 -31 -8 -33 M0 -37 Q4 -31 8 -33" fill="none" stroke="#3a2208" stroke-width="1.2" stroke-linecap="round"/>',
    }


# Orden de dibujo, de atrás hacia adelante: Partes del cuerpo intercaladas con el cuerpo propio.
ORDEN = ["clothBack", "cuerpo:cola", "cuerpo:piernas", "leg", "cuerpo:pies", "foot", "cuerpo:torso", "cloth",
         "neck", "cuerpo:brazos", "arm", "grip", "cuerpo:cabeza", "hairs", "mouths", "accesories", "accesories2",
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


def componer(piezas: dict[str, str], color: str = COLOR_PELAJE) -> str:
    """El SVG del Gaturro con `piezas` (Parte del cuerpo → SVG exportado por FFDec) puestas."""
    cuerpo = _cuerpo(color)
    capas, defs = [], []
    for n, capa in enumerate(ORDEN):
        if capa.startswith("cuerpo:"):
            capas.append(cuerpo[capa.removeprefix("cuerpo:")])
            continue
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

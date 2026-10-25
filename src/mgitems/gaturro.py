"""El Gaturro del editor de Looks: el Gaturro ORIGINAL del juego con las Piezas puestas como las pone el juego (ADR 0003).

El cuerpo es `assets.GaturroMC`, la misma clase que usa el cliente del juego, que también viene sin
cifrar en algunos SWF de assets del juego. Se exporta su primer cuadro (`standBy`, el Gaturro quieto)
a SVG con FFDec, que conserva el nombre de instancia de cada clip como `id`.

Las reglas son las del cliente (`Gaturro.attempt`, `setColor`, `lookForHideParts`):

- La Pieza de una Parte del cuerpo `P` va en cada clip vacío llamado `P`, `PFore` o `PBack`
  (salvo `clothBack` para el Torso), con la transformación del clip.
- Los clips `color1`, `color2` y `colorEye` (del cuerpo y de las Piezas) se pintan enteros del color
  del jugador (`ColorTransform.color`): el color reemplaza al dibujo y se conserva la transparencia.
- Una Pieza cuya clase contiene `hide_` o `invisible_` esconde los clips hermanos de su hueco que no
  son huecos de Partes del cuerpo.
"""

import re

from mgitems.iconos import IconosItems

CLASE_CUERPO = "assets.GaturroMC"
# SWF de assets del juego que traen `assets.GaturroMC` sin cifrar (el mismo dibujo en los dos).
# Son una versión anterior a la del cliente actual (ver `es_version_anterior`).
SWF_CUERPO = ("fashion_nuevo", "superHeroesTrajes")

# Un maniquí de 2025 armado con la plantilla del Gaturro (sus huecos coinciden con los del Gaturro al
# decimal), con un torso más nuevo: trae los clips `clothBack` (Espalda) y `clothFront`, que el
# Gaturro publicado no tiene. De ahí se toman su posición y su capa.
SWF_PLANTILLA, CLASE_PLANTILLA = "fashion2025", "maniqui_so"

# Las Partes del cuerpo en el orden en que el juego las pone (AvatarBodyEnum.getList): si dos van
# al mismo clip, queda la última (por ejemplo, `gripFore` gana sobre `grip` en el clip `gripFore`).
# `accesories2` existe en el juego actual (se ve), aunque no en la versión del cliente que se leyó.
PARTES = ["hats", "hairs", "mouths", "neck", "accesories", "accesories2", "cloth", "clothFront", "clothBack", "leg",
          "foot", "arm", "armFore", "armBack", "glove", "gloveFore", "gloveBack", "grip", "gripFore", "gripBack"]

# La versión actual no está publicada sin cifrar.
AVISO_VERSION_ANTERIOR = ("Gaturro de una versión anterior del juego: la nariz y «Accesorio 2» pueden verse distinto. "
                          "La Espalda va donde la pone la plantilla de 2025 del juego.")

# Colores de fábrica del juego (ColorPickerModal): pelaje, panza y ojos.
COLORES = {"color1": "#FFF200", "color2": "#DDB42D", "color3": "#FFFFFF"}
_CLIP_DE_COLOR = {"color1": "color1", "color2": "color2", "colorEye": "color3"}

_ANCLAJE_FFDEC = re.compile(r'<g transform="matrix\(1\.0, 0\.0, 0\.0, 1\.0, -?[\d.]+, -?[\d.]+\)">(?P<contenido>.*?)</g>\s*<defs>', re.S)
_DEFS = re.compile(r"<defs>(?P<defs>.*)</defs>", re.S)
_ID = re.compile(r'\bid="([^"]+)"')
_REFERENCIA = re.compile(r'(href="#|url\(#)([^")]+)')
_TRANSFORMACION = re.compile(r'transform="([^"]+)"')
_TAMANO = re.compile(r'height="(?P<alto>[\d.]+)px" width="(?P<ancho>[\d.]+)px"')
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_MARGEN = 15  # lugar alrededor del cuerpo para Piezas grandes (sombreros, alas)


def huecos_de(parte: str) -> list[str]:
    """Los clips donde el juego pone la Pieza de una Parte del cuerpo."""
    return [parte, parte + "Fore"] + ([parte + "Back"] if parte != "cloth" else [])


_TODOS_LOS_HUECOS = {h for p in PARTES for h in huecos_de(p)}


def tiene_lugar(cuerpo: str, parte: str) -> bool:
    """Si el cuerpo tiene algún clip donde poner la Pieza de esa Parte."""
    return parte in PARTES and any(_hueco(h).search(cuerpo) for h in huecos_de(parte))


def _torso(svg: str) -> re.Match | None:
    """El sprite del torso tal como lo exporta FFDec: el que tiene el clip `cloth`."""
    return next((m for m in re.finditer(r'<g id="sprite\d+">(?P<hijos>.*?)</g>', svg, re.S) if _hueco("cloth").search(m.group("hijos"))), None)


def completar_con_plantilla(cuerpo: str, plantilla: str) -> str:
    """El cuerpo con los huecos del torso de la plantilla de 2025 que le faltan (Espalda, `clothFront`).

    Cada hueco nuevo va con la transformación de la plantilla y en su misma capa: delante del hueco de
    la plantilla que lo precede y que el cuerpo también tiene, o al fondo si no hay ninguno antes
    (la Espalda va detrás del dibujo del torso).
    """
    torso, del_molde = _torso(cuerpo), _torso(plantilla)
    if not torso or not del_molde:
        return cuerpo
    vacio = re.search(r'xlink:href="(#[^"]+)"', _hueco("cloth").search(torso.group("hijos")).group(0)).group(1)
    hijos = torso.group("hijos")
    anterior = None  # el último hueco de la plantilla que el cuerpo también tiene
    for clip in re.findall(r"<use [^>]*/>", del_molde.group("hijos")):
        nombre = re.search(r'\bid="([^"]+)"', clip)
        if not nombre or not _hueco(nombre.group(1)).search(clip):
            continue  # el dibujo del maniquí no se copia
        nombre = nombre.group(1)
        if _hueco(nombre).search(hijos):
            anterior = nombre
            continue
        transformacion = _TRANSFORMACION.search(clip)
        atributo = f' transform="{transformacion.group(1)}"' if transformacion else ""
        nuevo = f'<use height="0.0" id="{nombre}"{atributo} width="0.0" xlink:href="{vacio}"/>'
        if anterior:
            existente = _hueco(anterior).search(hijos).group(0)
            hijos = hijos.replace(existente, existente + nuevo, 1)
        else:
            hijos = nuevo + hijos
        anterior = nombre
    return cuerpo.replace(torso.group(0), torso.group(0).replace(torso.group("hijos"), hijos, 1), 1)


def tiene_color_de_nariz(cuerpo: str) -> bool:
    """Si el cuerpo tiene una zona de color además de cara, cuerpo y ojos (la del Gaturro actual es la nariz).

    La versión publicada no la tiene; no se sabe cómo se llama en la actual, así que vale cualquier
    clip `color…` que no sea de los conocidos.
    """
    return any(nombre not in _CLIP_DE_COLOR for nombre in re.findall(r'\bid="(color[A-Za-z0-9]*)"', cuerpo))


def es_version_anterior(cuerpo: str) -> bool:
    """El Gaturro del juego actual tiene un lugar para «Accesorio 2»; el de las copias publicadas, no."""
    return not tiene_lugar(cuerpo, "accesories2")


def _pieza(svg: str, prefijo: str) -> tuple[str, str] | None:
    """(contenido con el punto de anclaje en 0,0, defs), con ids únicos; None si no tiene la forma de FFDec."""
    svg = _ID.sub(lambda m: f'id="{prefijo}{m.group(1)}"', svg)
    svg = _REFERENCIA.sub(lambda m: f"{m.group(1)}{prefijo}{m.group(2)}", svg)
    contenido = _ANCLAJE_FFDEC.search(svg)
    if not contenido:
        return None
    defs = _DEFS.search(svg)
    return contenido.group("contenido"), defs.group("defs") if defs else ""


def _hueco(nombre: str) -> re.Pattern:
    """El clip vacío `nombre` tal como lo exporta FFDec: `<use height="0.0" … id="nombre" … width="0.0" …/>`."""
    return re.compile(rf'<use (?=[^>]*\bheight="0\.0")(?=[^>]*\bwidth="0\.0")[^>]*\bid="{re.escape(nombre)}"[^>]*/>')


def _esconder_hermanos(svg: str, hueco: str) -> str:
    """Esconde los clips hermanos del hueco (en el mismo sprite) que no son huecos de Partes del cuerpo."""
    no_esconder = "|".join(map(re.escape, _TODOS_LOS_HUECOS))

    def esconder(sprite: re.Match) -> str:
        if not _hueco(hueco).search(sprite.group(0)):
            return sprite.group(0)
        return re.sub(rf'<use (?![^>]*\bid="(?:{no_esconder})")', '<use visibility="hidden" ', sprite.group(0))
    return re.sub(r'<g id="sprite\d+">.*?</g>', esconder, svg, flags=re.S)


def componer(cuerpo: str, piezas: dict[str, tuple[str, str]], colores: dict | None = None) -> str:
    """El SVG del Gaturro con `piezas` (Parte del cuerpo → (clase, SVG exportado por FFDec)) puestas."""
    elegidos = {k: c for k, c in (colores or {}).items() if k in COLORES and isinstance(c, str) and _COLOR.match(c)}
    colores = COLORES | elegidos

    # Qué Pieza va en cada clip, en el orden del juego (la última gana).
    en_hueco: dict[str, str] = {}
    for parte in PARTES:
        if parte in piezas:
            for hueco in huecos_de(parte):
                en_hueco[hueco] = parte

    svg, defs, preparadas = cuerpo, [], {}
    for hueco, parte in en_hueco.items():
        clase, svg_pieza = piezas[parte]
        if parte not in preparadas:
            preparadas[parte] = _pieza(svg_pieza, f"p{len(preparadas)}_")
            if preparadas[parte]:
                defs.append(preparadas[parte][1])
        if preparadas[parte] is None or not _hueco(hueco).search(svg):
            continue
        if "hide_" in clase or "invisible_" in clase:
            svg = _esconder_hermanos(svg, hueco)
        contenido = preparadas[parte][0]

        def poner(clip: re.Match, parte=parte, contenido=contenido) -> str:
            transformacion = _TRANSFORMACION.search(clip.group(0))
            atributo = f' transform="{transformacion.group(1)}"' if transformacion else ""
            return f'<g data-parte="{parte}"{atributo}>{contenido}</g>'
        svg = _hueco(hueco).sub(poner, svg)

    # Los clips de color, pintados enteros del color del jugador.
    filtros = "".join(
        f'<filter id="mg-{clip}" color-interpolation-filters="sRGB"><feFlood flood-color="{colores[clave]}"/>'
        f'<feComposite in2="SourceGraphic" operator="in"/></filter>'
        for clip, clave in _CLIP_DE_COLOR.items())
    svg = re.sub(r'<(use|g) ([^>]*\bid="(?:p\d+_)?(color1|color2|colorEye)")',
                 lambda m: f'<{m.group(1)} filter="url(#mg-{m.group(3)})" {m.group(2)}', svg)

    # Lugar alrededor del cuerpo para lo que sobresale.
    tamano = _TAMANO.search(svg)
    if tamano:
        ancho, alto = float(tamano.group("ancho")), float(tamano.group("alto"))
        svg = _TAMANO.sub(f'viewBox="{-_MARGEN} {-_MARGEN} {ancho + 2 * _MARGEN} {alto + 2 * _MARGEN}"', svg, count=1)
    return svg.replace("<defs>", "<defs>" + filtros + "".join(defs), 1)


class ImagenesPiezas(IconosItems):
    """El primer cuadro de cada Pieza (y del cuerpo) en SVG, con su punto de anclaje, una vez por versión de su SWF."""

    FORMATO = "svg"

    def svg(self, swf: str, clase: str) -> str | None:
        try:
            return (self._carpeta_swf(swf) / f"{clase}.svg").read_text(encoding="utf-8")
        except OSError:
            return None

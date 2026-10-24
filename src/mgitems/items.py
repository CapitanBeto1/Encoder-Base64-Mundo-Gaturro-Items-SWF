"""Items: rutas `<swf>.<Clase>` (el SWF puede incluir carpeta: `carpeta/swf.Clase`) y cómo reconocerlos en un SWF de assets."""

import re

_RUTA_ITEM = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*\.[A-Za-z_][A-Za-z0-9_]*$")

# Sufijos de clases que viven en un SWF de assets pero no son Items:
# `_on` son Piezas (incluye `_brazo_on`) y `_so` son objetos de escenario.
_SUFIJOS_NO_ITEM = ("_on", "_so")


def es_ruta_valida(ruta: str) -> bool:
    return bool(_RUTA_ITEM.match(ruta))


def separar_rutas(texto: str) -> list[str]:
    """Rutas escritas una por línea o separadas por coma, sin espacios sobrantes ni repetidas."""
    return _sin_repetidas(parte.strip() for parte in re.split(r"[,\r\n]+", texto))


def separar_prefijos(texto: str) -> list[str]:
    return _sin_repetidas(parte.strip() for parte in texto.split(","))


def items_del_swf(clases: list[str]) -> list[str]:
    """Las clases de un SWF de assets que son Items.

    Las clases dentro de un paquete (`costumes_fla.MainTimeline`, `assets.GaturroMC`)
    son internas del SWF o del juego, no Items.
    """
    return _sin_repetidas(c for c in clases if "." not in c and not c.endswith(_SUFIJOS_NO_ITEM))


def piezas_del_swf(clases: list[str]) -> list[str]:
    """Las clases de un SWF de assets que son Piezas (`_on`, incluidas las `_brazo_on`), en orden natural."""
    return sorted(_sin_repetidas(c for c in clases if "." not in c and c.endswith("_on")), key=orden_natural)


def filtrar_por_prefijos(items: list[str], prefijos: list[str]) -> list[str]:
    """Items cuyo nombre empieza con alguno de los prefijos, sin distinguir mayúsculas, en orden natural."""
    prefijos = tuple(p.lower() for p in prefijos)
    return sorted((i for i in items if i.lower().startswith(prefijos)), key=orden_natural)


def orden_natural(nombre: str) -> list:
    """Clave para ordenar `anteojo2` antes que `anteojo10`."""
    return [int(parte) if parte.isdigit() else parte for parte in re.split(r"(\d+)", nombre.lower())]


def _sin_repetidas(valores) -> list[str]:
    """Valores no vacíos, sin repetidos, en el orden en que aparecen."""
    return list(dict.fromkeys(v for v in valores if v))

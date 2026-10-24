"""Rutas de Items: `<swf>.<Clase>`, donde el SWF puede incluir carpeta (`carpeta/swf.Clase`)."""

import re

_RUTA_ITEM = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*\.[A-Za-z_][A-Za-z0-9_]*$")


def es_ruta_valida(ruta: str) -> bool:
    return bool(_RUTA_ITEM.match(ruta))


def separar_rutas(texto: str) -> list[str]:
    """Rutas escritas una por línea o separadas por coma, sin espacios sobrantes ni repetidas."""
    rutas = []
    for parte in re.split(r"[,\r\n]+", texto):
        ruta = parte.strip()
        if ruta and ruta not in rutas:
            rutas.append(ruta)
    return rutas

"""Catálogo de SWF de assets conocidos que viene con el programa.

Se arma con `scripts/armar_catalogo.py`: cada entrada es `{"swf": nombre, "items": cantidad}`,
donde el nombre puede incluir subcarpeta (`antro2017/wears`).
"""

import json
from pathlib import Path

ARCHIVO_CATALOGO = Path(__file__).parent / "datos" / "catalogo.json"


def cargar_catalogo() -> list[dict]:
    try:
        return json.loads(ARCHIVO_CATALOGO.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []


def buscar_en_catalogo(catalogo: list[dict], texto: str) -> list[dict]:
    """SWF cuyo nombre contiene el texto (sin distinguir mayúsculas); los que empiezan con él, primero."""
    texto = texto.strip().lower()
    if not texto:
        return list(catalogo)
    coinciden = [s for s in catalogo if texto in s["swf"].lower()]
    return sorted(coinciden, key=lambda s: not _empieza_con(s["swf"].lower(), texto))


def _empieza_con(nombre: str, texto: str) -> bool:
    """El nombre o su parte sin carpeta empieza con el texto."""
    return nombre.startswith(texto) or nombre.rsplit("/", 1)[-1].startswith(texto)

"""Categorías de las Piezas: en qué Parte(s) del cuerpo usa el juego cada Pieza.

El SWF no lo dice; los Items sí: si una Prenda pone `remera5_on` en `cloth`, esa Pieza es del
Torso, y lo mismo si un Item de mochila la agrega en `cloth` al usarlo. Un Item puede usar Piezas
de otro SWF (`costumes.coronaRey_on`), y eso cuenta para la Pieza de ese SWF. Las Piezas que ningún
Item viste no tienen Parte ("Otros"); para esas se anota, si se sabe, para qué las usa el juego
(un transporte, la animación de un Item de mochila, la casa, la mascota).

El programa trae un índice armado de antemano para todos los SWF del catálogo (`armar_indice.py`;
solo nombres). Ese índice ubica además las Piezas que ningún Item viste, cuando hay con qué: ver
`armar_indice.py`. Los SWF que no están o que cambiaron se analizan en la computadora del jugador,
solo con sus Items.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from mgitems.prendas import MOCHILA, PARTES_DEL_CUERPO, PRENDA, ItemBase, leer_item_base

ARCHIVO_INDICE = Path(__file__).parent / "datos" / "indice_piezas.json"
# Lo que un Item de mochila agrega y viste al Gaturro (el resto de `adds`, como `action`, no viste).
PARTES_QUE_VISTEN = set(PARTES_DEL_CUERPO) | {"clothFront", "armFore", "armBack", "gripBack", "glove", "gloveFore", "gloveBack"}
# Sube cuando cambia cómo se clasifica, para no usar lo analizado antes en la computadora del jugador.
FORMATO = 3

# Para qué usa el juego una Pieza que no viste al Gaturro.
TRANSPORTE, ACCION, CASA, MASCOTA = "transporte", "accion", "casa", "mascota"
# Items cuya Pieza `<Item>_on` es de la casa.
_PADRES_DE_LA_CASA = ("HouseMamboAsset", "HouseDecorationMamboAsset")
_CLASE = re.compile(r"\bclass\s+(\w+)\s+extends\s+(\w+)")
_VEHICULO = re.compile(r'\bvehicle\s*=\s*"([^"]+)"')
_PIEZA_EN_MAPA = re.compile(r'"\w+"\s*:\s*"([^"]+_on)"')


def usos_de_piezas(swf: str, items: dict[str, ItemBase]) -> dict[str, dict[str, set[str]]]:
    """SWF → Pieza → Partes donde la usan los Items de `swf` (las de otro SWF, bajo ese SWF)."""
    usos: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for item in items.values():
        for parte, valor in item.partes.items():
            if item.tipo != PRENDA and parte not in PARTES_QUE_VISTEN:
                continue
            otro, _, clase = valor.rpartition(".")
            usos[otro or swf][clase].add(parte)
    return usos


def otros_usos(swf: str, fuentes: dict[str, str]) -> dict[str, dict[str, str]]:
    """SWF → Pieza → para qué la usan los Items de `swf` sin vestir al Gaturro (TRANSPORTE, ACCION,
    CASA o MASCOTA). `fuentes`: clase → código AS3."""
    usos: dict[str, dict[str, str]] = defaultdict(dict)

    def anotar(valor: str, uso: str) -> None:
        partes = valor.split(".")  # "pieza", "swf.pieza" o "acción.swf.pieza"
        usos[partes[-2] if len(partes) > 1 else swf][partes[-1]] = uso

    for fuente in fuentes.values():
        clase = _CLASE.search(fuente)
        if not clase:
            continue
        nombre, padre = clase.groups()
        if padre in _PADRES_DE_LA_CASA:
            anotar(f"{nombre}_on", CASA)
        elif padre == "PetClothMamboAsset":  # su `clothes` viste a la mascota
            for pieza in _PIEZA_EN_MAPA.findall(fuente):
                anotar(pieza, MASCOTA)
        elif padre == "TransportMamboAsset":
            for vehiculo in _VEHICULO.findall(fuente):
                anotar(vehiculo, TRANSPORTE)
        elif (item := leer_item_base(fuente)) and item.tipo == MOCHILA:
            for parte, valor in item.partes.items():
                if parte not in PARTES_QUE_VISTEN and valor.endswith("_on"):
                    anotar(valor, ACCION)
    return usos


def categorias(piezas: list[str], usos: dict[str, set[str]]) -> dict[str, list[str]]:
    """Cada Pieza del SWF con sus Partes (ordenadas); [] si ningún Item la viste."""
    return {pieza: sorted(usos.get(pieza, ())) for pieza in piezas}


class IndicePiezas:
    """El índice que trae el programa: SWF → {"version", "piezas": {Pieza: [Partes]}, "otros_usos": {Pieza: uso}}."""

    def __init__(self, archivo: Path = ARCHIVO_INDICE):
        try:
            self._swfs = json.loads(archivo.read_text(encoding="utf-8")).get("swfs", {})
        except (OSError, ValueError):
            self._swfs = {}

    def swfs(self) -> list[str]:
        return list(self._swfs)

    def leer(self, swf: str) -> dict | None:
        return self._swfs.get(swf)


class CacheCategorias:
    """Las categorías analizadas en la computadora del jugador, por versión del SWF."""

    def __init__(self, carpeta: Path):
        self._carpeta = carpeta

    def _archivo(self, swf: str) -> Path:
        base = self._carpeta.joinpath(*swf.split("/"))
        return base.with_name(base.name + ".json")

    def leer(self, swf: str, version: str) -> dict | None:
        """{"piezas": {Pieza: [Partes]}, "otros_usos": {Pieza: uso}}, o None si no está o es de otra versión."""
        try:
            datos = json.loads(self._archivo(swf).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if datos.get("version") != version or datos.get("formato") != FORMATO:
            return None
        return {"piezas": datos.get("piezas", {}), "otros_usos": datos.get("otros_usos", {})}

    def guardar(self, swf: str, version: str, piezas: dict[str, list[str]], otros: dict[str, str]) -> None:
        archivo = self._archivo(swf)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        datos = {"formato": FORMATO, "version": version, "piezas": piezas, "otros_usos": otros}
        archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

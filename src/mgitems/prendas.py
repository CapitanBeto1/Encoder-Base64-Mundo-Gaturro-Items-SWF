"""Items base: lo que se truca para una Prenda trucada o para materializar un Look.

Un Item base puede ser:

- una **Prenda**: su clase AS3 extiende `ClothMamboAsset` y declara en `clothes` qué Pieza
  muestra en cada Parte del cuerpo al ponérsela (el juego lo copia a `wear_<parte>`, y el
  Item queda en el guardarropa):

      clothes = {"cloth":"remera5_on", "arm":"remera5_brazo_on"};

- un **Item de mochila**: su clase extiende `UsableMamboAsset` o `ConsumableMamboAsset`; lo
  que declara en `adds` se copia a `attr_<clave>` y se aplica al Gaturro al usarlo desde la
  mochila. Las Partes del cuerpo son atributos del Gaturro, así que `adds.hats = "…"` lo viste:

      adds.hats = "costumes.coronaRey_on";

Trucar es reescribir ese mapa en la clase y recompilar el SWF de assets con FFDec.
"""

import json
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from mgitems.ffdec import FFDec

# Partes del cuerpo con su nombre en el juego, en orden de arriba hacia abajo.
PARTES_DEL_CUERPO = {
    "hats": "Sombrero",
    "hairs": "Pelo",
    "accesories": "Accesorio",
    "accesories2": "Accesorio 2",
    "mouths": "Boca",
    "neck": "Cuello",
    "cloth": "Torso",
    "arm": "Brazos",
    "clothBack": "Espalda",
    "grip": "Mano",
    "gripFore": "Mano de adelante",
    "leg": "Piernas",
    "foot": "Pies",
}

PRENDA = "prenda"
MOCHILA = "mochila"
# Con 10000 usos o más, el juego no descuenta usos al usar un consumible (BagGuiModal).
USOS_ILIMITADOS = 10000

_CLASE = re.compile(r"\bclass\s+(\w+)\s+extends\s+(ClothMamboAsset|UsableMamboAsset|ConsumableMamboAsset)\b")
_CLOTHES = re.compile(r"clothes\s*=\s*\{(?P<cuerpo>[^{}]*)\}\s*;")
_PAR = re.compile(r'"(\w+)"\s*:\s*"([^"]*)"')
_ADDS_PUNTO = re.compile(r'^[ \t]*adds\.(\w+)\s*=\s*"([^"]*)"\s*;[ \t]*\r?\n', re.M)
_ADDS_OBJETO = re.compile(r"^[ \t]*adds\s*=\s*\{(?P<cuerpo>[^{}]*)\}\s*;[ \t]*\r?\n", re.M)
_ADDS_LINEA = re.compile(r"^[ \t]*adds(?:\.\w+)?\s*=.*;[ \t]*\r?\n", re.M)  # cualquier otra asignación a adds
_USOS = re.compile(r"^[ \t]*uses\s*=\s*(\d+)\s*;[ \t]*\r?\n", re.M)
_SESION = re.compile(r"^[ \t]*session\s*=\s*\w+\s*;[ \t]*\r?\n", re.M)
_FRAME1 = re.compile(r"internal function frame1\(\)\s*:\s*\*\s*\{[ \t]*\r?\n")
_SUPER = re.compile(r"super\(\);[ \t]*\r?\n")
_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Una Pieza del mismo SWF (`gorra1_on`) o de otro (`costumes.coronaRey_on`, `antro2017/wears.x_on`).
_PIEZA = re.compile(r"^(?:[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*\.)?[A-Za-z_][A-Za-z0-9_]*$")


class TruqueoFallido(Exception):
    """No se pudo generar o verificar el truco."""


@dataclass
class ItemBase:
    clase: str
    partes: dict[str, str]  # Parte del cuerpo → Pieza (en `clothes` o en `adds`)
    fuente: str  # código AS3 de la clase
    tipo: str = PRENDA  # PRENDA (guardarropa) o MOCHILA
    consumible: bool = False  # Item de mochila que se gasta al usarlo
    usos: int | None = None  # los declarados en la clase, si los declara


def leer_item_base(fuente: str) -> ItemBase | None:
    """El Item base que define este código AS3, o None si la clase no puede ser Item base."""
    clase = _CLASE.search(fuente)
    if not clase:
        return None
    nombre, padre = clase.groups()
    if padre == "ClothMamboAsset":
        clothes = _CLOTHES.search(fuente)
        partes = dict(_PAR.findall(clothes.group("cuerpo"))) if clothes else {}
        return ItemBase(nombre, partes, fuente)
    usos = _USOS.search(fuente)
    objeto = _ADDS_OBJETO.search(fuente)
    partes = (dict(_PAR.findall(objeto.group("cuerpo"))) if objeto else {}) | dict(_ADDS_PUNTO.findall(fuente))
    return ItemBase(
        nombre, partes, fuente, MOCHILA,
        consumible=padre == "ConsumableMamboAsset", usos=int(usos.group(1)) if usos else None,
    )


def reescribir_partes(item: ItemBase, partes: dict[str, str]) -> str:
    """El código AS3 del Item base mostrando `partes` (Parte del cuerpo → Pieza)."""
    for parte, pieza in partes.items():
        if not _IDENTIFICADOR.match(parte) or not _PIEZA.match(pieza):
            raise ValueError(f"Parte del cuerpo o Pieza inválida: {parte} → {pieza}")
    if item.tipo == PRENDA:
        return _reescribir_clothes(item.fuente, partes)
    return _reescribir_adds(item, partes)


def _reescribir_clothes(fuente: str, partes: dict[str, str]) -> str:
    pares = ",\n".join(f'            "{parte}":"{pieza}"' for parte, pieza in partes.items())
    literal = "clothes = {\n" + pares + "\n         };" if partes else "clothes = {};"
    if not _CLOTHES.search(fuente):
        raise TruqueoFallido("La Prenda no declara sus Piezas de la forma esperada")
    return _CLOTHES.sub(lambda _: literal, fuente, count=1)


def _reescribir_adds(item: ItemBase, partes: dict[str, str]) -> str:
    """Item de mochila: solo te viste al usarlo (sin su animación ni su efecto), con usos
    ilimitados si es consumible y sin `session` (para que no dure solo la sesión)."""
    fuente = _SESION.sub("", _USOS.sub("", _ADDS_LINEA.sub("", _ADDS_OBJETO.sub("", item.fuente))))
    lineas = [f'         adds.{parte} = "{pieza}";\n' for parte, pieza in partes.items()]
    if item.consumible:
        lineas.append(f"         uses = {USOS_ILIMITADOS};\n")
    insercion = "".join(lineas)
    lugar = _FRAME1.search(fuente) or _SUPER.search(fuente)
    if not lugar:
        raise TruqueoFallido("El Item de mochila no tiene código donde agregar las Piezas")
    return fuente[:lugar.end()] + insercion + fuente[lugar.end():]


class ItemsBaseFFDec:
    """Lee y truca Items base de un SWF de assets con FFDec."""

    def __init__(self, ffdec: FFDec | None = None):
        self._ffdec = ffdec or FFDec()

    def analizar(self, data: bytes, clases: list[str]) -> dict[str, ItemBase]:
        """Los Items base entre las `clases` del SWF (Prendas e Items de mochila)."""
        if not clases:
            return {}
        with tempfile.TemporaryDirectory(prefix="mgitems-") as temporal:
            swf = Path(temporal) / "assets.swf"
            swf.write_bytes(data)
            salida = Path(temporal) / "scripts"
            self._ffdec.ejecutar("-selectclass", ",".join(clases), "-export", "script", str(salida), str(swf))
            items = {}
            for archivo in salida.rglob("*.as"):
                item = leer_item_base(archivo.read_text(encoding="utf-8", errors="replace"))
                if item and item.clase in clases:
                    items[item.clase] = item
            return items

    def trucar(self, data: bytes, clase: str, fuente: str, partes: dict[str, str]) -> bytes:
        """El SWF con la clase reemplazada por `fuente`, verificado: la clase trucada declara `partes`."""
        with tempfile.TemporaryDirectory(prefix="mgitems-") as temporal:
            entrada = Path(temporal) / "original.swf"
            salida = Path(temporal) / "trucado.swf"
            scripts = Path(temporal) / "scripts"
            scripts.mkdir()
            entrada.write_bytes(data)
            (scripts / f"{clase}.as").write_text(fuente, encoding="utf-8")
            resultado = self._ffdec.ejecutar("-importScript", str(entrada), str(salida), str(scripts))
            if not salida.is_file():
                detalle = (resultado.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
                raise TruqueoFallido(f"FFDec no generó el SWF trucado. {detalle[0]}".strip())
            trucado = salida.read_bytes()

        verificado = self.analizar(trucado, [clase]).get(clase)
        if verificado is None or verificado.partes != partes:
            raise TruqueoFallido("El SWF trucado no quedó con las Piezas elegidas")
        if verificado.consumible and verificado.usos != USOS_ILIMITADOS:
            raise TruqueoFallido("El SWF trucado no quedó con usos ilimitados")
        return trucado


class CacheItemsBase:
    """Los Items base de cada SWF de assets, guardados por versión del SWF."""

    # Si cambia lo que se lee de cada SWF, lo guardado antes se vuelve a leer.
    ESQUEMA = 2  # 2: Prendas e Items de mochila

    def __init__(self, carpeta: Path):
        self._carpeta = carpeta

    def _archivo(self, swf: str) -> Path:
        base = self._carpeta.joinpath(*swf.split("/"))
        return base.with_name(base.name + ".json")

    def leer(self, swf: str, version: str) -> dict[str, ItemBase] | None:
        try:
            datos = json.loads(self._archivo(swf).read_text(encoding="utf-8"))
            if datos.get("version") != version or datos.get("esquema") != self.ESQUEMA:
                return None
            return {clase: ItemBase(**i) for clase, i in datos["items"].items()}
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def guardar(self, swf: str, version: str, items: dict[str, ItemBase]) -> None:
        archivo = self._archivo(swf)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        datos = {"version": version, "esquema": self.ESQUEMA, "items": {clase: asdict(i) for clase, i in items.items()}}
        archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

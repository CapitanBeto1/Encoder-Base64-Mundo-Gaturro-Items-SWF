"""Prendas y Prendas trucadas.

Una Prenda es un Item cuya clase AS3 extiende `ClothMamboAsset` y declara en `clothes`
qué Pieza muestra en cada Parte del cuerpo, por ejemplo:

    clothes = {"cloth":"remera5_on", "arm":"remera5_brazo_on"};

Trucar una Prenda es reescribir ese mapa y recompilar su SWF de assets con FFDec.
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

_CLASE_PRENDA = re.compile(r"\bclass\s+(\w+)\s+extends\s+ClothMamboAsset\b")
_CLOTHES = re.compile(r"clothes\s*=\s*\{(?P<cuerpo>[^{}]*)\}\s*;")
_PAR = re.compile(r'"(\w+)"\s*:\s*"([^"]*)"')
_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class TruqueoFallido(Exception):
    """No se pudo generar o verificar la Prenda trucada."""


@dataclass
class Prenda:
    clase: str
    partes: dict[str, str]  # Parte del cuerpo → Pieza
    fuente: str  # código AS3 de la clase


def leer_prenda(fuente: str) -> Prenda | None:
    """La Prenda que define este código AS3, o None si la clase no es una Prenda."""
    clase = _CLASE_PRENDA.search(fuente)
    if not clase:
        return None
    clothes = _CLOTHES.search(fuente)
    partes = dict(_PAR.findall(clothes.group("cuerpo"))) if clothes else {}
    return Prenda(clase.group(1), partes, fuente)


def reescribir_partes(fuente: str, partes: dict[str, str]) -> str:
    """El mismo código AS3 con `clothes` reemplazado por `partes`."""
    for parte, pieza in partes.items():
        if not _IDENTIFICADOR.match(parte) or not _IDENTIFICADOR.match(pieza):
            raise ValueError(f"Parte del cuerpo o Pieza inválida: {parte} → {pieza}")
    pares = ",\n".join(f'            "{parte}":"{pieza}"' for parte, pieza in partes.items())
    literal = "clothes = {\n" + pares + "\n         };" if partes else "clothes = {};"
    if not _CLOTHES.search(fuente):
        raise TruqueoFallido("La Prenda base no declara sus Piezas de la forma esperada")
    return _CLOTHES.sub(lambda _: literal, fuente, count=1)


class PrendasFFDec:
    """Lee y truca Prendas de un SWF de assets con FFDec."""

    def __init__(self, ffdec: FFDec | None = None):
        self._ffdec = ffdec or FFDec()

    def analizar(self, data: bytes, clases: list[str]) -> dict[str, Prenda]:
        """Las Prendas entre las `clases` del SWF (las demás clases no son Prendas)."""
        if not clases:
            return {}
        with tempfile.TemporaryDirectory(prefix="mgitems-") as temporal:
            swf = Path(temporal) / "assets.swf"
            swf.write_bytes(data)
            salida = Path(temporal) / "scripts"
            self._ffdec.ejecutar("-selectclass", ",".join(clases), "-export", "script", str(salida), str(swf))
            prendas = {}
            for archivo in salida.rglob("*.as"):
                prenda = leer_prenda(archivo.read_text(encoding="utf-8", errors="replace"))
                if prenda and prenda.clase in clases:
                    prendas[prenda.clase] = prenda
            return prendas

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

        verificada = self.analizar(trucado, [clase]).get(clase)
        if verificada is None or verificada.partes != partes:
            raise TruqueoFallido("El SWF trucado no quedó con las Piezas elegidas")
        return trucado


class CachePrendas:
    """Las Prendas de cada SWF de assets, guardadas por versión del SWF."""

    def __init__(self, carpeta: Path):
        self._carpeta = carpeta

    def _archivo(self, swf: str) -> Path:
        base = self._carpeta.joinpath(*swf.split("/"))
        return base.with_name(base.name + ".json")

    def leer(self, swf: str, version: str) -> dict[str, Prenda] | None:
        try:
            datos = json.loads(self._archivo(swf).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if datos.get("version") != version:
            return None
        return {clase: Prenda(**p) for clase, p in datos["prendas"].items()}

    def guardar(self, swf: str, version: str, prendas: dict[str, Prenda]) -> None:
        archivo = self._archivo(swf)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        datos = {"version": version, "prendas": {clase: asdict(p) for clase, p in prendas.items()}}
        archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

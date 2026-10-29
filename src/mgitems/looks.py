"""Looks: una Prenda base con una Pieza en cada una de varias Partes del cuerpo, guardados por el jugador.

Cada Pieza se guarda con su SWF (`costumes.coronaRey_on`), así un Look puede mezclar
Piezas de varios SWF. Se guardan en un archivo JSON de la carpeta del programa.

Las acciones de la pestaña Acciones se guardan igual, en su propio archivo: un Item de mochila con su
`animacion` y, como Partes, la Pieza de la acción (`action`) y la de la cabeza (`effect`).
"""

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

_RUTA = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*\.[A-Za-z_][A-Za-z0-9_]*$")
_PARTE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_CLAVES_COLOR = {"color1", "color2", "color3"}


class LookInvalido(ValueError):
    """El Look no tiene la forma esperada."""


@dataclass
class Look:
    nombre: str
    base: str | None  # ruta de la Prenda base: "clothes1.remera5"; None si todavía no se eligió
    partes: dict[str, str] = field(default_factory=dict)  # Parte del cuerpo → ruta de la Pieza
    id: str = ""
    # Colores del Gaturro con los que se ve el Look en el programa (cara, cuerpo, ojos: "#RRGGBB");
    # los que falten, los de fábrica. Solo para la vista previa: no cambian lo que se entrega al juego.
    colores: dict[str, str] = field(default_factory=dict)
    animacion: str | None = None  # solo las acciones: la animación del juego ("showObject", "dance"…)

    @classmethod
    def desde(cls, datos: dict) -> "Look":
        """Un Look a partir de lo que manda la interfaz (o de lo guardado), validado."""
        if not isinstance(datos, dict):
            raise LookInvalido("El Look no tiene la forma esperada.")
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre:
            raise LookInvalido("Poné un nombre al Look.")
        base = datos.get("base") or None
        if base is not None and not _RUTA.match(str(base)):
            raise LookInvalido(f"La Prenda base no es válida: {base}")
        partes = datos.get("partes") or {}
        if not isinstance(partes, dict):
            raise LookInvalido("Las Partes del cuerpo no tienen la forma esperada.")
        for parte, pieza in partes.items():
            if not _PARTE.match(str(parte)) or not _RUTA.match(str(pieza)):
                raise LookInvalido(f"Pieza no válida: {parte} → {pieza}")
        colores = datos.get("colores") or {}
        if not isinstance(colores, dict) or any(c not in _CLAVES_COLOR or not isinstance(v, str) or not _COLOR.match(v)
                                                for c, v in colores.items()):
            raise LookInvalido("Los colores del Look no tienen la forma esperada.")
        animacion = datos.get("animacion") or None
        if animacion is not None and not _PARTE.match(str(animacion)):
            raise LookInvalido(f"La animación no es válida: {animacion}")
        return cls(nombre, base, {str(p): str(v) for p, v in partes.items()}, str(datos.get("id") or ""), dict(colores),
                   animacion and str(animacion))


FORMATO = "mgitems-look"
FORMATO_ACCION = "mgitems-accion"
VERSION_FORMATO = 1


def archivo_de_look(look: Look, formato: str = FORMATO) -> str:
    """El contenido de un archivo de Look (o de acción): sin su id, que es de cada jugador."""
    datos = {"formato": formato, "version": VERSION_FORMATO, "nombre": look.nombre, "base": look.base, "partes": look.partes,
             "colores": look.colores}
    if look.animacion:
        datos["animacion"] = look.animacion
    return json.dumps(datos, ensure_ascii=False, indent=1)


def look_de_archivo(contenido: str, formato: str = FORMATO) -> Look:
    """El Look (o la acción) de un archivo, validado (sin id: es nuevo para quien lo importa)."""
    que = "Look" if formato == FORMATO else "acción"
    try:
        datos = json.loads(contenido)
    except ValueError:
        datos = None
    if not isinstance(datos, dict) or datos.get("formato") != formato:
        raise LookInvalido(f"Este archivo no es {'un Look' if formato == FORMATO else 'una acción'} de MG Items.")
    if not isinstance(datos.get("version"), int) or datos["version"] > VERSION_FORMATO:
        raise LookInvalido(f"{'Este Look es' if formato == FORMATO else 'Esta acción es'} de una versión más nueva de MG Items: actualizá el programa.")
    look = Look.desde({k: datos.get(k) for k in ("nombre", "base", "partes", "colores", "animacion")})
    if formato == FORMATO and not look.partes:
        raise LookInvalido("El Look del archivo no tiene Piezas.")
    if formato == FORMATO_ACCION and not look.animacion:
        raise LookInvalido(f"La {que} del archivo no tiene animación.")
    return look


class AlmacenLooks:
    def __init__(self, archivo: Path, clave: str = "looks"):
        self._archivo, self._clave = archivo, clave

    def todos(self) -> list[Look]:
        try:
            datos = json.loads(self._archivo.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as e:
            raise OSError(f"No se pudo leer {self._archivo.name}") from e
        looks = []
        for d in datos.get(self._clave, []):
            try:
                looks.append(Look.desde(d))
            except LookInvalido:
                continue  # uno dañado no impide usar los demás
        return looks

    def guardar(self, look: Look) -> Look:
        """Agrega el Look (si no tiene id) o reemplaza el que tiene su id."""
        looks = self.todos()
        if not look.id:
            look.id = uuid.uuid4().hex
        looks = [l for l in looks if l.id != look.id] + [look]
        self._escribir(looks)
        return look

    def borrar(self, id_look: str) -> bool:
        looks = self.todos()
        quedan = [l for l in looks if l.id != id_look]
        if len(quedan) == len(looks):
            return False
        self._escribir(quedan)
        return True

    def _escribir(self, looks: list[Look]) -> None:
        self._archivo.parent.mkdir(parents=True, exist_ok=True)
        temporal = self._archivo.with_suffix(".tmp")
        temporal.write_text(json.dumps({self._clave: [asdict(l) for l in looks]}, ensure_ascii=False, indent=1), encoding="utf-8")
        temporal.replace(self._archivo)  # sin dejar el archivo a medio escribir

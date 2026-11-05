"""Mis Looks, Mis acciones, Mis Prendas trucadas, Mis tiendas, Mis portales, Mis minijuegos y Mis fondos.

Todos son un `Look` (un nombre, un Item base y lo que cada pestaña necesita), se guardan igual (cada tipo en su
archivo de la carpeta del programa), se duplican, se borran, y se exportan e importan como archivo para pasárselos
a otra persona. Lo que cambia de un tipo a otro está en `TIPOS`: dónde se guarda, el formato del archivo y qué
tiene que tener para ser válido.
"""

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

from mgitems.acciones import ANIMACIONES
from mgitems.fondos import COMPORTAMIENTO as COMPORTAMIENTO_FONDO
from mgitems.items import orden_natural
from mgitems.looks import (
    FORMATO, FORMATO_ACCION, FORMATO_FONDO, FORMATO_MINIJUEGO, FORMATO_PORTAL, FORMATO_TIENDA, FORMATO_TRUCADA,
    AlmacenLooks, Look, LookInvalido, archivo_de_look, look_de_archivo,
)
from mgitems.prendas import ACCION, EFECTO


def _accion_valida(datos: dict) -> Look:
    """Una acción: con nombre, una animación del juego y, como Partes, solo la Pieza de la acción y la de la cabeza."""
    if not isinstance(datos, dict) or not str(datos.get("nombre") or "").strip():
        raise LookInvalido("Poné un nombre a la acción.")
    accion = Look.desde(datos)
    if accion.animacion not in ANIMACIONES:
        raise LookInvalido("Elegí una animación.")
    if set(accion.partes) - {ACCION, EFECTO}:
        raise LookInvalido("Una acción solo lleva la Pieza de la acción y la de la cabeza.")
    return accion


def _trucada_valida(datos: dict) -> Look:
    """Una Prenda trucada: con nombre, Item base y una sola Pieza en una Parte."""
    if not isinstance(datos, dict) or not str(datos.get("nombre") or "").strip():
        raise LookInvalido("Poné un nombre a la Prenda trucada.")
    trucada = Look.desde(datos)
    if not trucada.base:
        raise LookInvalido("Elegí el Item base de la Prenda trucada.")
    if len(trucada.partes) != 1:
        raise LookInvalido("Una Prenda trucada lleva una sola Pieza, en una Parte.")
    if trucada.animacion:
        raise LookInvalido("Una Prenda trucada no lleva animación.")
    return trucada


def _npc_valido(el: str, que: str, es_fondo: bool = False) -> Callable[[dict], Look]:
    """Cómo se valida una tienda, un portal, un minijuego o un fondo: con nombre, Item base y comportamiento (un
    fondo, además, `painting` y el cuadro que se ve)."""
    def validar(datos: dict) -> Look:
        if not isinstance(datos, dict) or not str(datos.get("nombre") or "").strip():
            raise LookInvalido(f"Poné un nombre a {el}.")
        npc = Look.desde(datos)
        if not npc.base:
            raise LookInvalido(f"Elegí el Item que se convierte en {que}.")
        if not npc.comportamiento:
            raise LookInvalido("Elegí el comportamiento.")
        if npc.partes or npc.animacion:
            raise LookInvalido(f"{el[0].upper()}{el[1:]} no lleva Piezas ni animación.")
        if es_fondo and (npc.comportamiento != COMPORTAMIENTO_FONDO or npc.cuadro is None):
            raise LookInvalido("Elegí el cuadro que se ve.")
        return npc
    return validar


@dataclass(frozen=True)
class TipoDeGuardado:
    archivo: str  # el archivo de la carpeta del programa (sin «.json») y su clave adentro
    formato: str  # el de los archivos que se exportan (`looks.archivo_de_look`)
    extension: str  # la de esos archivos
    nombre: str  # para el diálogo de archivos: «Look de MG Items (*.mglook)»
    el: str  # para los mensajes: «No se pudo guardar el Look»
    ese: str  # «Ese Look ya no existe.»
    validar: Callable[[dict], Look]


TIPOS: dict[str, TipoDeGuardado] = {
    "look": TipoDeGuardado("looks", FORMATO, "mglook", "Look", "el Look", "Ese Look", Look.desde),
    "accion": TipoDeGuardado("acciones", FORMATO_ACCION, "mgaccion", "Acción", "la acción", "Esa acción", _accion_valida),
    "trucada": TipoDeGuardado("trucadas", FORMATO_TRUCADA, "mgtrucada", "Prenda trucada", "la Prenda trucada",
                              "Esa Prenda trucada", _trucada_valida),
    "tienda": TipoDeGuardado("tiendas", FORMATO_TIENDA, "mgtienda", "Tienda", "la tienda", "Esa tienda",
                             _npc_valido("la tienda", "tienda")),
    "portal": TipoDeGuardado("portales", FORMATO_PORTAL, "mgportal", "Portal", "el portal", "Ese portal",
                             _npc_valido("el portal", "portal")),
    "minijuego": TipoDeGuardado("minijuegos", FORMATO_MINIJUEGO, "mgminijuego", "Minijuego", "el minijuego",
                                "Ese minijuego", _npc_valido("el minijuego", "minijuego")),
    "fondo": TipoDeGuardado("fondos", FORMATO_FONDO, "mgfondo", "Fondo", "el fondo", "Ese fondo",
                            _npc_valido("el fondo", "fondo", es_fondo=True)),
}


def _nombre_libre(nombre: str, usados: set[str], sufijo: str = "") -> str:
    """`nombre`, o "nombre (2)", "nombre (3)"… (con `sufijo` dentro del paréntesis) si ya está usado."""
    if nombre not in usados:
        return nombre
    raiz = nombre.removesuffix(f" ({sufijo.strip()})") if sufijo else nombre
    n = 2
    while f"{raiz} ({sufijo}{n})" in usados:
        n += 1
    return f"{raiz} ({sufijo}{n})"


class Guardados:
    """Los guardados de todos los tipos, en `carpeta` (la del programa). Cada operación devuelve `{"ok", …}` o
    `{"ok": False, "error"}`, como el resto del núcleo."""

    def __init__(self, carpeta: Callable[[], Path]):
        self._carpeta = carpeta  # se pide cada vez: la carpeta del programa se crea recién cuando hace falta

    def _tipo(self, tipo: str) -> TipoDeGuardado:
        if tipo not in TIPOS:
            raise KeyError(tipo)
        return TIPOS[tipo]

    def _almacen(self, t: TipoDeGuardado) -> AlmacenLooks:
        return AlmacenLooks(self._carpeta() / f"{t.archivo}.json", clave=t.archivo)

    def lista(self, tipo: str) -> dict:
        """Los guardados de un tipo, por nombre."""
        try:
            todos = self._almacen(self._tipo(tipo)).todos()
        except KeyError:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        except OSError as e:
            return {"ok": False, "error": f"No se pudieron leer los guardados: {e}"}
        return {"ok": True, "guardados": [asdict(d) for d in sorted(todos, key=lambda d: orden_natural(d.nombre))]}

    def guardar(self, tipo: str, documento: dict) -> dict:
        """Guarda uno nuevo (sin id) o los cambios de uno guardado."""
        try:
            t = self._tipo(tipo)
            guardado = self._almacen(t).guardar(t.validar(documento))
        except KeyError:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar {t.el}: {e}"}
        return {"ok": True, "documento": asdict(guardado)}

    def duplicar(self, tipo: str, id_documento: str) -> dict:
        """Una copia de uno guardado, con otro nombre."""
        try:
            t = self._tipo(tipo)
            almacen = self._almacen(t)
            todos = almacen.todos()
            original = next((d for d in todos if d.id == id_documento), None)
            if original is None:
                return {"ok": False, "error": f"{t.ese} ya no existe."}
            nombre = _nombre_libre(f"{original.nombre} (copia)", {d.nombre for d in todos}, "copia ")
            copia = almacen.guardar(replace(original, id="", nombre=nombre, partes=dict(original.partes),
                                            colores=dict(original.colores)))
        except KeyError:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo duplicar {t.el}: {e}"}
        return {"ok": True, "documento": asdict(copia)}

    def borrar(self, tipo: str, id_documento: str) -> dict:
        try:
            t = self._tipo(tipo)
            borrado = self._almacen(t).borrar(id_documento)
        except KeyError:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo borrar {t.el}: {e}"}
        return {"ok": True} if borrado else {"ok": False, "error": f"{t.ese} ya no existe."}

    def exportar(self, tipo: str, documento: dict, ruta: str) -> dict:
        """Lo guarda en un archivo para pasárselo a otra persona (sin su id, que es de cada uno)."""
        try:
            t = self._tipo(tipo)
            Path(ruta).write_text(archivo_de_look(t.validar(documento), t.formato), encoding="utf-8")
        except KeyError:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el archivo: {e.strerror or e}"}
        return {"ok": True, "ruta": ruta}

    def importar_de_archivo(self, tipo: str, ruta: str) -> dict:
        """Suma a los guardados el de un archivo (con otro nombre si ya hay uno igual)."""
        try:
            t = self._tipo(tipo)
        except KeyError:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        try:
            contenido = Path(ruta).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo abrir el archivo: {e.strerror or e}"}
        try:
            documento = t.validar(asdict(look_de_archivo(contenido, t.formato)))
            almacen = self._almacen(t)
            documento.nombre = _nombre_libre(documento.nombre, {d.nombre for d in almacen.todos()})
            guardado = almacen.guardar(documento)
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar {t.el}: {e}"}
        return {"ok": True, "documento": asdict(guardado)}

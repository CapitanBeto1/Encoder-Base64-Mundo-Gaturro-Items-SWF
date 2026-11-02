"""NPC: Items que, puestos en la casa, hacen lo mismo que un NPC del juego (abrir una tienda, llevar a una sala…).

Lo que hace un NPC lo dice su comportamiento (`behavior`): un archivo `npc/<comportamiento>.npc` del juego, en
base64, con el guion que corre al tocarlo (el mismo lenguaje que el Encode de Lola).

Cualquier Item de cualquier SWF puede ser un NPC (probado en el juego): su clase pasa a heredar de `MamboAsset`,
que traen todos los SWF de assets, y escribe el comportamiento directamente en sus `attributes`. Al recibirlo, el
juego manda esos atributos al servidor (`InventoryUtil.doAcquireObject`); sin `wear_*` ni `grabbable`, llega a la
casa, y con `behavior` el juego lo trata como NPC (`GaturroRoom.createUnknownSceneObject`). No se usa
`NpcMamboAsset` porque muchos SWF no la traen y FFDec no compila una clase que hereda de una que el SWF no tiene.
"""

import base64
import binascii
import json
import os
import re
from pathlib import Path

from mgitems.mambo import NoSePuedeConvertir, atributo_en_codigo, clase_mambo, texto  # noqa: F401 (NoSePuedeConvertir)

TIENDA = "tienda"
PORTAL = "portal"
MINIJUEGO = "minijuego"
TIPOS = (TIENDA, PORTAL, MINIJUEGO)

ARCHIVO_COMPORTAMIENTOS = Path(__file__).parent / "datos" / "comportamientos.json"

_COMPORTAMIENTO = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*$")
# Las órdenes del guion que hacen de un NPC una tienda, un portal o un minijuego (`NpcActionRunner`).
_ORDENES_TIENDA = ("catalog", "pepionCatalog", "reyesCatalog", "navidadCatalog", "feriaCatalog", "pascuasCatalog",
                   "mundialCatalog", "vipCatalog", "petCatalog", "open.shop", "carousel.open")
_FIN_DE_ORDEN = r"(?=[ \t]|$)"  # así una etiqueta de estado («openCatalog:») no cuenta como orden
_TIENDA = re.compile(r"^[ \t]*(?:" + "|".join(map(re.escape, _ORDENES_TIENDA)) + ")" + _FIN_DE_ORDEN + r"[ \t]*([^\s#]*)", re.M)
_PORTAL = re.compile(r"^[ \t]*room\.(?:change|random)" + _FIN_DE_ORDEN + r"[ \t]*([^\s#]*)", re.M)
_MINIJUEGO = re.compile(r"^[ \t]*(?:minigame|launch\.html5(?:_mmo)?)" + _FIN_DE_ORDEN + r"[ \t]*([^\s#]*)", re.M)


def es_comportamiento_valido(comportamiento) -> bool:
    return isinstance(comportamiento, str) and bool(_COMPORTAMIENTO.match(comportamiento))


def leer_npc(data: bytes) -> str:
    """El guion de un archivo `.npc` (viene en base64; alguno, en texto)."""
    try:
        return base64.b64decode(data, validate=True).decode("utf-8")
    except (binascii.Error, ValueError):
        return data.decode("utf-8", "replace")


def clasificar(guion: str) -> dict:
    """Qué hace un NPC según su guion: `{"tipo", "catalogos", "salas", "juegos"}`. `tipo` es la primera de
    tienda, portal o minijuego que haga (ningún NPC del juego hace dos), o None si no hace ninguna."""
    catalogos = list(dict.fromkeys(c for c in _TIENDA.findall(guion) if c))
    salas = list(dict.fromkeys(int(s) for s in _PORTAL.findall(guion) if s.isdigit()))  # "$(…)": según el momento
    portal = bool(_PORTAL.search(guion))
    juegos = list(dict.fromkeys(j for j in _MINIJUEGO.findall(guion) if j))
    tipo = TIENDA if _TIENDA.search(guion) else PORTAL if portal else MINIJUEGO if _MINIJUEGO.search(guion) else None
    return {"tipo": tipo, "catalogos": catalogos, "salas": salas, "juegos": juegos}


def describir(info: dict, nombres_salas: dict[str, str] | None = None) -> str:
    """Qué hace el NPC, para la interfaz: «Abre el catálogo potions2024», «Te lleva a la sala 51687540»…"""
    nombres_salas = nombres_salas or {}
    if info["tipo"] == TIENDA:
        catalogos = info["catalogos"]
        if len(catalogos) == 1:
            return f"Abre el catálogo {catalogos[0]}"
        return f"Abre {len(catalogos)} catálogos: {', '.join(catalogos)}" if catalogos else "Abre una tienda"
    if info["tipo"] == PORTAL:
        salas = info["salas"]
        if len(salas) == 1:
            nombre = nombres_salas.get(str(salas[0]))
            return f"Te lleva a la sala {salas[0]}" + (f" ({nombre})" if nombre else "")
        return f"Te lleva a {len(salas)} salas" if salas else "Te lleva a otra sala"
    if info["tipo"] == MINIJUEGO:
        juegos = info["juegos"]
        if len(juegos) == 1:
            return f"Abre el minijuego {juegos[0]}"
        return f"Abre {len(juegos)} minijuegos: {', '.join(juegos)}" if juegos else "Abre un minijuego"
    return "No es una tienda, ni un portal, ni un minijuego"


def comportamiento_en_codigo(fuente: str) -> str | None:
    """El comportamiento que el código AS3 de un Item convertido escribe en sus atributos, o None."""
    return atributo_en_codigo(fuente, "behavior")


def clase_npc(fuente: str, clase: str, comportamiento: str) -> str:
    """El código AS3 de `clase` convertida en NPC con `comportamiento`, con el mismo dibujo (`fuente`: su código)."""
    if not es_comportamiento_valido(comportamiento):
        raise NoSePuedeConvertir(f"comportamiento no válido: {comportamiento}")
    return clase_mambo(fuente, clase, [f"attributes.behavior = {texto(comportamiento)};", "attributes.monitorAttributes = false;"])


class Comportamientos:
    """Los comportamientos conocidos que trae el programa (`scripts/armar_comportamientos.py`):
    `{"comportamientos": {nombre: {"tipo", "catalogos", "salas", "juegos", "objetos"}}, "salas": {id: nombre}}`.
    `objetos`: los objetos del juego que lo usan ("swf.clase"), para mostrar su imagen."""

    def __init__(self, archivo: Path = ARCHIVO_COMPORTAMIENTOS):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        self._comportamientos = datos.get("comportamientos", {})
        self.salas: dict[str, str] = datos.get("salas", {})

    def todos(self) -> dict[str, dict]:
        return self._comportamientos

    def leer(self, nombre: str) -> dict | None:
        return self._comportamientos.get(nombre)


# Las direcciones de los guiones que bajó el juego quedan en su caché HTTP (Chromium): en los archivos de bloques
# `data_*` están las claves (las direcciones); en los `f_*`, el contenido, que no hace falta leer.
_NPC_EN_CACHE = re.compile(rb"/juego/npc/([A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*)\.npc")


def comportamientos_en_cache(cache: Path) -> set[str]:
    """Los comportamientos cuyo guion bajó el juego (al entrar a una sala baja el de cada NPC). Solo lee nombres.
    Sirve con el juego abierto (ver `_leer_compartido`). OSError si no se pudo leer ningún archivo del caché."""
    nombres: set[str] = set()
    archivos = sorted(cache.glob("data_*"))
    leidos = 0
    for archivo in archivos:
        try:
            nombres |= {n.decode() for n in _NPC_EN_CACHE.findall(_leer_compartido(archivo))}
            leidos += 1
        except OSError:
            continue  # uno borrado mientras se leía: se sigue con los demás
    if archivos and not leidos:
        raise OSError("No se pudo leer el caché del juego")
    return nombres


def _leer_compartido(archivo: Path) -> bytes:
    """Lee un archivo que otro programa tiene abierto. Con el juego abierto, su caché solo se puede abrir si se le
    permite a él leerlo, escribirlo y borrarlo mientras tanto (`FILE_SHARE_DELETE`); `open` de Python no lo permite
    y Windows le niega el acceso."""
    if os.name != "nt":
        return archivo.read_bytes()
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                     wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    leer, compartir_todo, existente = 0x80000000, 0x1 | 0x2 | 0x4, 3
    manejador = kernel32.CreateFileW(str(archivo), leer, compartir_todo, None, existente, 0, None)
    if manejador == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    with os.fdopen(msvcrt.open_osfhandle(manejador, os.O_RDONLY | os.O_BINARY), "rb") as f:
        return f.read()


class ComportamientosEncontrados:
    """Los comportamientos encontrados en el caché del juego, en la carpeta del programa:
    `{"comportamientos": {nombre: {"tipo", "catalogos", "salas", "juegos", "objetos"}}, "pendientes": [nombres]}`.
    Se guardan también los que no son de ningún tipo (`tipo` None), para no volver a bajarlos. `pendientes`: los
    anotados sin bajar (por ejemplo, justo antes de que una entrega borre el caché)."""

    def __init__(self, archivo: Path):
        self._archivo = archivo

    def leer(self) -> dict:
        try:
            datos = json.loads(self._archivo.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"comportamientos": {}, "pendientes": []}
        except (OSError, ValueError) as e:
            raise OSError(f"No se pudo leer {self._archivo.name}") from e
        return {"comportamientos": dict(datos.get("comportamientos", {})), "pendientes": list(datos.get("pendientes", []))}

    def guardar(self, datos: dict) -> None:
        self._archivo.parent.mkdir(parents=True, exist_ok=True)
        temporal = self._archivo.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        temporal.replace(self._archivo)

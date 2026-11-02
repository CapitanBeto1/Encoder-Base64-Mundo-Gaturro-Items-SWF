"""Lo que bajó el juego, según su caché HTTP (Chromium, en `<perfil del juego>/Cache`).

En los archivos de bloques `data_*` están las claves, que son las direcciones de lo bajado; en los `f_*`, el contenido,
que no hace falta leer. Al entrar a una sala, el juego baja el guion de cada NPC (`npc/<comportamiento>.npc`). Solo se leen nombres; no se toca nada.
"""

import os
import re
from pathlib import Path

_NPC = re.compile(rb"/juego/npc/([A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*)\.npc")


def comportamientos_en_cache(cache: Path) -> set[str]:
    """Los comportamientos cuyo guion bajó el juego (al entrar a una sala baja el de cada NPC)."""
    return _nombres(cache, _NPC)


def _nombres(cache: Path, patron: re.Pattern) -> set[str]:
    """Lo que encuentra `patron` en las direcciones del caché. Sirve con el juego abierto (ver `_leer_compartido`).
    OSError si no se pudo leer ningún archivo del caché."""
    nombres: set[str] = set()
    archivos = sorted(cache.glob("data_*"))
    leidos = 0
    for archivo in archivos:
        try:
            nombres |= {n.decode() for n in patron.findall(_leer_compartido(archivo))}
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

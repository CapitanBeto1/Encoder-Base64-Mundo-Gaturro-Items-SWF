"""API del núcleo: lo único que usa la interfaz y lo único que prueban los tests.

Todas las operaciones devuelven diccionarios simples (serializables a JSON) con
`ok` y, si algo falla, un `error` en español listo para mostrar al jugador.
"""

from pathlib import Path

from mgitems.items import (
    es_ruta_valida,
    filtrar_por_prefijos,
    items_del_swf,
    separar_prefijos,
    separar_rutas,
)
from mgitems.script import codificar, generar_script
from mgitems.swf import SwfInvalido, leer_clases


class Nucleo:
    def __init__(self):
        self._swf_abierto: str | None = None
        self._items_del_swf: list[str] = []

    def abrir_swf(self, ruta: str) -> dict:
        """Abre un SWF de assets de la computadora para buscar sus Items."""
        archivo = Path(ruta)
        try:
            clases = leer_clases(archivo.read_bytes())
        except OSError as e:
            return {"ok": False, "error": f"No se pudo abrir el archivo: {e.strerror or e}"}
        except SwfInvalido as e:
            return {"ok": False, "error": f"{e}: {archivo.name}"}

        self._swf_abierto = archivo.stem
        self._items_del_swf = items_del_swf(clases)
        return {"ok": True, "swf": self._swf_abierto, "cantidad_items": len(self._items_del_swf)}

    def buscar_items(self, texto_prefijos: str) -> dict:
        """Items del SWF abierto cuyo nombre empieza con alguno de los prefijos (separados por coma)."""
        if self._swf_abierto is None:
            return {"ok": False, "error": "Primero abrí un SWF."}
        prefijos = separar_prefijos(texto_prefijos)
        if not prefijos:
            return {"ok": False, "error": "Escribí al menos el comienzo de un nombre, por ejemplo: remera"}

        encontrados = filtrar_por_prefijos(self._items_del_swf, prefijos)
        return {"ok": True, "items": [f"{self._swf_abierto}.{i}" for i in encontrados]}

    def interpretar_items(self, texto: str) -> dict:
        """Rutas de Items escritas a mano (una por línea o separadas por coma), validadas."""
        rutas = separar_rutas(texto)
        if not rutas:
            return {"ok": False, "error": "Escribí al menos un Item, por ejemplo: clothes1.remera5"}

        invalidas = [r for r in rutas if not es_ruta_valida(r)]
        if invalidas:
            return {
                "ok": False,
                "error": "Estos Items no tienen el formato <swf>.<Clase>: " + ", ".join(invalidas),
                "invalidas": invalidas,
            }
        return {"ok": True, "items": rutas}

    def generar_encode(self, items: str | list[str]) -> dict:
        """Encode que agrega los Items: una lista de rutas, o texto como el de `interpretar_items`."""
        texto = items if isinstance(items, str) else "\n".join(items)
        interpretados = self.interpretar_items(texto)
        if not interpretados["ok"]:
            return interpretados

        rutas = interpretados["items"]
        script = generar_script(rutas)
        return {"ok": True, "items": rutas, "script": script, "encode": codificar(script)}

    def guardar_encode(self, encode: str, ruta: str) -> dict:
        try:
            Path(ruta).write_text(encode, encoding="ascii")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el archivo: {e.strerror or e}"}
        return {"ok": True, "ruta": ruta}

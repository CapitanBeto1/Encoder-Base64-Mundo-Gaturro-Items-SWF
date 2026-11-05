"""Agregar Items: los Encodes que agregan Items, armarlos, leerlos y guardarlos."""

from pathlib import Path

from mgitems.destinos import DESCARTADO, descarte_por_nombre
from mgitems.items import es_ruta_valida, filtrar_por_prefijos, separar_prefijos, separar_rutas
from mgitems.nucleo._comun import _cantidad
from mgitems.script import EncodeInvalido, codificar, decodificar, generar_script, leer_script


class Encodes:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

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

    def generar_encode(self, items: str | list[str | dict]) -> dict:
        """Encode que agrega los Items en su cantidad.

        `items` es texto como el de `interpretar_items` (cantidad 1 cada uno) o una
        lista donde cada elemento es una ruta (cantidad 1) o `{"ruta", "cantidad"}`.
        """
        if isinstance(items, str):
            interpretados = self.interpretar_items(items)
            if not interpretados["ok"]:
                return interpretados
            items = interpretados["items"]

        pedidos = [(i, 1) if isinstance(i, str) else (i.get("ruta", ""), i.get("cantidad", 1)) for i in items]
        if not pedidos:
            return {"ok": False, "error": "Agregá al menos un Item a la lista."}

        invalidas = [ruta for ruta, _ in pedidos if not es_ruta_valida(ruta)]
        if invalidas:
            return {
                "ok": False,
                "error": "Estos Items no tienen el formato <swf>.<Clase>: " + ", ".join(invalidas),
                "invalidas": invalidas,
            }
        cantidades_invalidas = [ruta for ruta, cantidad in pedidos if _cantidad(cantidad) is None]
        if cantidades_invalidas:
            return {
                "ok": False,
                "error": "La cantidad tiene que ser un número entero mayor que 0: " + ", ".join(cantidades_invalidas),
            }

        pedidos = [(ruta, _cantidad(cantidad)) for ruta, cantidad in pedidos]
        script = generar_script(pedidos)
        avisos = [{"ruta": ruta, **aviso} for ruta, _ in pedidos if (aviso := self._aviso_de_destino(ruta))]
        return {"ok": True, "items": _como_items(pedidos), "script": script, "encode": codificar(script), "avisos": avisos}

    def _aviso_de_destino(self, ruta: str) -> dict | None:
        """{"destino", "motivo"} si el Item no va a llegar bien al juego (según el índice o su nombre), o None."""
        swf, _, clase = ruta.rpartition(".")
        item = ((self._indice.leer(swf) or {}).get("items") or {}).get(clase)
        if item:
            return {"destino": item["destino"], "motivo": item["motivo"]} if item.get("motivo") else None
        motivo = descarte_por_nombre(ruta)
        return {"destino": DESCARTADO, "motivo": motivo} if motivo else None

    def importar_encode(self, encode: str) -> dict:
        """Items y cantidades que agrega un Encode existente."""
        try:
            script = decodificar(encode)
        except EncodeInvalido as e:
            return {"ok": False, "error": f"{e}."}

        pedidos, otros_comandos = leer_script(script)
        validos = [(ruta, cantidad) for ruta, cantidad in pedidos if es_ruta_valida(ruta) and cantidad > 0]
        if not validos:
            return {"ok": False, "error": "Este Encode no agrega ningún Item."}
        return {
            "ok": True,
            "items": _como_items(validos),
            "ignorados": [ruta for ruta, cantidad in pedidos if (ruta, cantidad) not in validos],
            "otros_comandos": otros_comandos,
            "script": script,
        }

    def importar_encode_de_archivo(self, ruta: str) -> dict:
        try:
            contenido = Path(ruta).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo abrir el archivo: {e.strerror or e}"}
        return self.importar_encode(contenido)

    def guardar_encode(self, encode: str, ruta: str) -> dict:
        try:
            Path(ruta).write_text(encode, encoding="ascii")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el archivo: {e.strerror or e}"}
        return {"ok": True, "ruta": ruta}


def _como_items(pedidos: list[tuple[str, int]]) -> list[dict]:
    return [{"ruta": ruta, "cantidad": cantidad} for ruta, cantidad in pedidos]

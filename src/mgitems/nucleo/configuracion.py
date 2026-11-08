"""Configuración del juego: terminator (objetos y atributos bloqueados por el juego).

El juego carga `cfgs/settings.json` al arrancar. `terminator.noUserObject` lista los objetos
que el cliente oculta y elimina del inventario del usuario. Interceptando ese archivo con Fiddler
se puede quitar entradas de la lista y hacer que el cliente los muestre.
"""

import json
from dataclasses import asdict

from mgitems.entrega import PasoFallido, QUE_HACER_EN_EL_JUEGO
from mgitems.fuente import URL_SETTINGS, SinConexion


class Configuracion:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def terminator(self) -> dict:
        """Descarga settings.json y devuelve las listas del terminator."""
        try:
            data = self._fuente.descargar_url(URL_SETTINGS)
        except SinConexion as e:
            return {"ok": False, "error": f"Sin conexión al CDN: {e}"}
        except OSError as e:
            return {"ok": False, "error": str(e)}
        try:
            settings = json.loads(data)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"No se pudo leer el config: {e}"}
        t = settings.get("terminator", {})
        return {
            "ok": True,
            "objetos": t.get("noUserObject", []),
            "atributos": t.get("noUserAttributes", []),
        }

    def aplicar_config(self, ignorar_objetos: list) -> dict:
        """Genera un settings.json sin los objetos bloqueados indicados y lo entrega via Fiddler."""
        if not isinstance(ignorar_objetos, list) or not ignorar_objetos:
            return {"ok": False, "error": "Elegí al menos un objeto para desbloquear."}
        try:
            data = self._fuente.descargar_url(URL_SETTINGS)
        except SinConexion as e:
            return {"ok": False, "error": f"Sin conexión al CDN: {e}"}
        except OSError as e:
            return {"ok": False, "error": str(e)}
        try:
            settings = json.loads(data)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"No se pudo leer el config: {e}"}
        ignorar = set(ignorar_objetos)
        t = settings.setdefault("terminator", {})
        t["noUserObject"] = [o for o in t.get("noUserObject", []) if o not in ignorar]
        modificado = json.dumps(settings, ensure_ascii=False).encode("utf-8")
        entrega, error = self._preparar_entrega(necesita=("fiddler", "reglas"))
        if error:
            return error
        try:
            entrega.entregar_json(URL_SETTINGS, modificado, "settings.json")
        except PasoFallido as e:
            return self._resultado_fallido(entrega, e)
        return {"ok": True, "pasos": [asdict(p) for p in entrega.pasos], "que_hacer": QUE_HACER_EN_EL_JUEGO}

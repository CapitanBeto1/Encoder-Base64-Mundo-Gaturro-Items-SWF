"""Configuración del juego: terminator (settings.json) y gameplay (gameplay.json).

El juego carga estos archivos al arrancar. Interceptándolos con Fiddler se pueden modificar
restricciones y listas que el cliente aplica localmente.
"""

import json
import re
from dataclasses import asdict

from mgitems.entrega import PasoFallido, QUE_HACER_EN_EL_JUEGO
from mgitems.fuente import URL_GAMEPLAY, URL_SETTINGS, SinConexion


def _jsonc_a_dict(texto: str) -> dict:
    """Parsea JSON con comentarios de línea (//) y de bloque (/* */)."""
    sin_comentarios = re.sub(r"//[^\n]*", "", texto)
    sin_comentarios = re.sub(r"/\*.*?\*/", "", sin_comentarios, flags=re.DOTALL)
    return json.loads(sin_comentarios)


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

    def gameplay(self) -> dict:
        """Descarga gameplay.json y devuelve las restricciones de ítems (troublesomeItems)."""
        try:
            data = self._fuente.descargar_url(URL_GAMEPLAY)
        except SinConexion as e:
            return {"ok": False, "error": f"Sin conexión al CDN: {e}"}
        except OSError as e:
            return {"ok": False, "error": str(e)}
        try:
            g = _jsonc_a_dict(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"ok": False, "error": f"No se pudo leer el config: {e}"}
        items_restringidos = [
            {"ruta": ruta, "attr": v.get("attr", "")}
            for ruta, v in g.get("troublesomeItems", {}).items()
        ]
        return {"ok": True, "items_restringidos": items_restringidos}

    def aplicar_gameplay(self, desbloquear: list) -> dict:
        """Genera un gameplay.json sin las restricciones indicadas y lo entrega via Fiddler."""
        if not isinstance(desbloquear, list) or not desbloquear:
            return {"ok": False, "error": "Elegí al menos un ítem para desbloquear."}
        try:
            data = self._fuente.descargar_url(URL_GAMEPLAY)
        except SinConexion as e:
            return {"ok": False, "error": f"Sin conexión al CDN: {e}"}
        except OSError as e:
            return {"ok": False, "error": str(e)}
        try:
            texto = data.decode("utf-8")
            g = _jsonc_a_dict(texto)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"ok": False, "error": f"No se pudo leer el config: {e}"}
        ignorar = set(desbloquear)
        ti = g.get("troublesomeItems", {})
        for ruta in ignorar:
            ti.pop(ruta, None)
        modificado = json.dumps(g, ensure_ascii=False).encode("utf-8")
        entrega, error = self._preparar_entrega(necesita=("fiddler", "reglas"))
        if error:
            return error
        try:
            entrega.entregar_json(URL_GAMEPLAY, modificado, "gameplay.json")
        except PasoFallido as e:
            return self._resultado_fallido(entrega, e)
        return {"ok": True, "pasos": [asdict(p) for p in entrega.pasos], "que_hacer": QUE_HACER_EN_EL_JUEGO}

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

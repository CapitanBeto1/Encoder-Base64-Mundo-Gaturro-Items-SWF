"""Ventana del programa: muestra la interfaz web y le expone el núcleo."""

import inspect
import re
from pathlib import Path

import webview

from mgitems.guardados import TIPOS as TIPOS_DE_GUARDADO, Guardados
from mgitems.nucleo import Nucleo
from mgitems.servidor_preview import ServidorPreview

TITULO = "MG Items"
UI = Path(__file__).parent / "ui" / "index.html"
_NO_VALE_EN_ARCHIVOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class _GuardadosConDialogos:
    """Mis Looks, Mis acciones, Mis Prendas trucadas, Mis tiendas…: `window.pywebview.api.guardados.<método>(tipo, …)`.

    Lo de `Nucleo.guardados`, salvo exportar e importar, que piden el archivo con un diálogo: la interfaz no elige
    rutas."""

    def __init__(self, guardados: Guardados):
        self._guardados = guardados
        for nombre in ("lista", "guardar", "duplicar", "borrar"):  # tal cual; exportar e importar, con diálogo
            setattr(self, nombre, getattr(guardados, nombre))

    def exportar(self, tipo: str, documento: dict) -> dict:
        t = TIPOS_DE_GUARDADO.get(tipo)
        if t is None:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        nombre = _NO_VALE_EN_ARCHIVOS.sub("_", str(documento.get("nombre") or "").strip()) or t.nombre
        ruta = _dialogo(webview.FileDialog.SAVE, save_filename=f"{nombre}.{t.extension}", file_types=_tipos_de_archivo(t))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._guardados.exportar(tipo, documento, ruta)

    def importar(self, tipo: str) -> dict:
        t = TIPOS_DE_GUARDADO.get(tipo)
        if t is None:
            return {"ok": False, "error": f"Tipo desconocido: {tipo}"}
        ruta = _dialogo(webview.FileDialog.OPEN, file_types=_tipos_de_archivo(t))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._guardados.importar_de_archivo(tipo, ruta)


_PARAMETROS_DE_RUTA = {"ruta", "carpeta"}


def _recibe_una_ruta(metodo) -> bool:
    return bool(_PARAMETROS_DE_RUTA & set(inspect.signature(metodo).parameters))


def _tipos_de_archivo(t) -> tuple[str, str]:
    return (f"{t.nombre} de MG Items (*.{t.extension})", "Todos los archivos (*.*)")


class Puente:
    """Lo que la interfaz puede llamar como `window.pywebview.api.<método>`.

    Es el núcleo, más lo que necesita una ventana (diálogos para elegir archivos).
    Los atributos empiezan con `_` para que pywebview no los exponga a la interfaz.
    """

    def __init__(self, nucleo: Nucleo):
        self._nucleo = nucleo
        self.guardados = _GuardadosConDialogos(nucleo.guardados)
        # Lo demás del núcleo, tal cual: pywebview expone los métodos de este objeto (también estos, que son del
        # núcleo). Acá solo se escribe lo que agrega la ventana. Lo que recibe una ruta no se expone: la elige el
        # usuario en un diálogo (los métodos de acá), no la interfaz.
        for nombre in dir(nucleo):
            metodo = getattr(nucleo, nombre)
            if not nombre.startswith("_") and not hasattr(type(self), nombre) and callable(metodo) and not _recibe_una_ruta(metodo):
                setattr(self, nombre, metodo)

    def abrir_swf(self) -> dict:
        ruta = _dialogo(webview.FileDialog.OPEN, file_types=("SWF (*.swf)", "Todos los archivos (*.*)"))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.abrir_swf(ruta)

    def importar_encode_de_archivo(self) -> dict:
        ruta = _dialogo(webview.FileDialog.OPEN, file_types=("Texto (*.txt)", "Todos los archivos (*.*)"))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.importar_encode_de_archivo(ruta)

    def elegir_ruta(self, id_componente: str, tipo: str) -> dict:
        """Diálogo para elegir a mano dónde está un componente (`tipo`: "archivo" o "carpeta")."""
        if tipo == "carpeta":
            ruta = _dialogo(webview.FileDialog.FOLDER)
        else:
            ruta = _dialogo(webview.FileDialog.OPEN, file_types=("Programas (*.exe)", "Todos los archivos (*.*)"))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.corregir_ruta(id_componente, ruta)

    def guardar_encode(self, encode: str) -> dict:
        if self._nucleo.tiene_swf_trucado(encode):
            # Una Prenda trucada necesita también su SWF: se guarda todo en una carpeta.
            carpeta = _dialogo(webview.FileDialog.FOLDER)
            if not carpeta:
                return {"ok": False, "cancelado": True}
            return self._nucleo.exportar_truco(encode, str(Path(carpeta) / "MG Items - Prenda trucada"))
        ruta = _dialogo(
            webview.FileDialog.SAVE,
            save_filename="items.txt",
            file_types=("Texto (*.txt)", "Todos los archivos (*.*)"),
        )
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.guardar_encode(encode, ruta)


def _dialogo(tipo, **opciones) -> str | None:
    """Ruta elegida en un diálogo de archivos, o None si se canceló."""
    ruta = webview.windows[0].create_file_dialog(tipo, **opciones)
    if isinstance(ruta, (list, tuple)):
        ruta = ruta[0] if ruta else None
    return ruta or None


def main() -> None:
    # La interfaz se sirve por http (no file://) para que Ruffle pueda cargar el preview del Gaturro.
    servidor = ServidorPreview()
    url = servidor.iniciar()
    webview.create_window(
        TITULO,
        url=url,
        js_api=Puente(Nucleo()),
        width=1100,
        height=720,
        # Más chica, la grilla y el Gaturro no entran (la barra lateral ya se achica a íconos: css/estructura.css).
        min_size=(960, 640),
        background_color="#f6d610",
    )
    webview.start()
    servidor.detener()


if __name__ == "__main__":
    main()

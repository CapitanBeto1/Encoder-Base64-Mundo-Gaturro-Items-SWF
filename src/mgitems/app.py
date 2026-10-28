"""Ventana del programa: muestra la interfaz web y le expone el núcleo."""

import re
from pathlib import Path

import webview

from mgitems.nucleo import Nucleo

TITULO = "MG Items"
UI = Path(__file__).parent / "ui" / "index.html"
_TIPOS_LOOK = ("Look de MG Items (*.mglook)", "Todos los archivos (*.*)")
_NO_VALE_EN_ARCHIVOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class Puente:
    """Lo que la interfaz puede llamar como `window.pywebview.api.<método>`.

    Delega todo en el núcleo y solo agrega lo que necesita una ventana (diálogos).
    Los atributos empiezan con `_` para que pywebview no los exponga a la interfaz.
    """

    def __init__(self, nucleo: Nucleo):
        self._nucleo = nucleo

    def abrir_swf(self) -> dict:
        ruta = _dialogo(webview.FileDialog.OPEN, file_types=("SWF (*.swf)", "Todos los archivos (*.*)"))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.abrir_swf(ruta)

    def buscar_en_catalogo(self, texto: str) -> dict:
        return self._nucleo.buscar_en_catalogo(texto)

    def abrir_swf_del_cdn(self, nombre: str) -> dict:
        return self._nucleo.abrir_swf_del_cdn(nombre)

    def prendas(self) -> dict:
        return self._nucleo.prendas()

    def items_base(self, swf: str) -> dict:
        return self._nucleo.items_base(swf)

    def piezas_de_swfs(self, swfs: list | None = None) -> dict:
        return self._nucleo.piezas_de_swfs(swfs)

    def items_de_swfs(self, swfs: list | None = None) -> dict:
        return self._nucleo.items_de_swfs(swfs)

    def piezas(self, swf: str | None = None) -> dict:
        return self._nucleo.piezas(swf)

    def trucar_prenda(self, base: str, parte: str, pieza: str) -> dict:
        return self._nucleo.trucar_prenda(base, parte, pieza)

    def partes_del_cuerpo(self) -> dict:
        return self._nucleo.partes_del_cuerpo()

    def looks(self) -> dict:
        return self._nucleo.looks()

    def guardar_look(self, look: dict) -> dict:
        return self._nucleo.guardar_look(look)

    def duplicar_look(self, id_look: str) -> dict:
        return self._nucleo.duplicar_look(id_look)

    def borrar_look(self, id_look: str) -> dict:
        return self._nucleo.borrar_look(id_look)

    def aplicar_look(self, look: dict) -> dict:
        return self._nucleo.aplicar_look(look)

    def animaciones(self) -> dict:
        return self._nucleo.animaciones()

    def aplicar_accion(self, accion: dict) -> dict:
        return self._nucleo.aplicar_accion(accion)

    def exportar_look(self, look: dict) -> dict:
        nombre = _NO_VALE_EN_ARCHIVOS.sub("_", str(look.get("nombre") or "").strip()) or "Look"
        ruta = _dialogo(webview.FileDialog.SAVE, save_filename=f"{nombre}.mglook", file_types=_TIPOS_LOOK)
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.exportar_look(look, ruta)

    def importar_look(self) -> dict:
        ruta = _dialogo(webview.FileDialog.OPEN, file_types=_TIPOS_LOOK)
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.importar_look_de_archivo(ruta)

    def gaturro(self, partes: dict, colores: dict | None = None) -> dict:
        return self._nucleo.gaturro(partes, colores)

    def preparar_iconos(self, swf: str | None = None) -> dict:
        return self._nucleo.preparar_iconos(swf)

    def iconos(self, rutas_items: list[str]) -> dict:
        return self._nucleo.iconos(rutas_items)

    def sugerir_items(self, texto: str) -> dict:
        return self._nucleo.sugerir_items(texto)

    def buscar_items(self, texto_prefijos: str) -> dict:
        return self._nucleo.buscar_items(texto_prefijos)

    def interpretar_items(self, texto: str) -> dict:
        return self._nucleo.interpretar_items(texto)

    def generar_encode(self, items: list[dict]) -> dict:
        return self._nucleo.generar_encode(items)

    def importar_encode(self, encode: str) -> dict:
        return self._nucleo.importar_encode(encode)

    def importar_encode_de_archivo(self) -> dict:
        ruta = _dialogo(webview.FileDialog.OPEN, file_types=("Texto (*.txt)", "Todos los archivos (*.*)"))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.importar_encode_de_archivo(ruta)

    def juego_abierto(self) -> bool:
        return self._nucleo.juego_abierto()

    def entregar_encode(self, encode: str) -> dict:
        return self._nucleo.entregar_encode(encode)

    def desactivar_reglas(self) -> dict:
        return self._nucleo.desactivar_reglas()

    def estado_entorno(self) -> dict:
        return self._nucleo.estado_entorno()

    def elegir_ruta(self, id_componente: str, tipo: str) -> dict:
        """Diálogo para elegir a mano dónde está un componente (`tipo`: "archivo" o "carpeta")."""
        if tipo == "carpeta":
            ruta = _dialogo(webview.FileDialog.FOLDER)
        else:
            ruta = _dialogo(webview.FileDialog.OPEN, file_types=("Programas (*.exe)", "Todos los archivos (*.*)"))
        if not ruta:
            return {"ok": False, "cancelado": True}
        return self._nucleo.corregir_ruta(id_componente, ruta)

    def restablecer_ruta(self, id_componente: str) -> dict:
        return self._nucleo.restablecer_ruta(id_componente)

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
    webview.create_window(
        TITULO,
        url=str(UI),
        js_api=Puente(Nucleo()),
        width=1100,
        height=720,
        min_size=(720, 520),
        background_color="#f6d610",
    )
    webview.start()


if __name__ == "__main__":
    main()

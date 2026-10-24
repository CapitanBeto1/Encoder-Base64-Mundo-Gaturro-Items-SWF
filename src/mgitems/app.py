"""Ventana del programa: muestra la interfaz web y le expone el núcleo."""

from pathlib import Path

import webview

from mgitems.nucleo import Nucleo

TITULO = "MG Items"
UI = Path(__file__).parent / "ui" / "index.html"


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

    def trucar_prenda(self, base: str, partes: dict) -> dict:
        return self._nucleo.trucar_prenda(base, partes)

    def preparar_iconos(self) -> dict:
        return self._nucleo.preparar_iconos()

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
        width=960,
        height=680,
        min_size=(720, 520),
        background_color="#f6d610",
    )
    webview.start()


if __name__ == "__main__":
    main()

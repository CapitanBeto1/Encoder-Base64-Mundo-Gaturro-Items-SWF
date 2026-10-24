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

    def generar_encode(self, texto: str) -> dict:
        return self._nucleo.generar_encode(texto)

    def guardar_encode(self, encode: str) -> dict:
        ruta = webview.windows[0].create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename="items.txt",
            file_types=("Texto (*.txt)", "Todos los archivos (*.*)"),
        )
        if not ruta:
            return {"ok": False, "cancelado": True}
        if isinstance(ruta, (list, tuple)):
            ruta = ruta[0]
        return self._nucleo.guardar_encode(encode, ruta)


def main() -> None:
    webview.create_window(
        TITULO,
        url=str(UI),
        js_api=Puente(Nucleo()),
        width=960,
        height=680,
        min_size=(720, 520),
        background_color="#14161c",
    )
    webview.start()


if __name__ == "__main__":
    main()

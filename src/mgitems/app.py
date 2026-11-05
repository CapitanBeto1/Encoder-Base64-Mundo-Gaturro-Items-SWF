"""Ventana del programa: muestra la interfaz web y le expone el núcleo."""

import re
from pathlib import Path

import webview

from mgitems.guardados import TIPOS as TIPOS_DE_GUARDADO, Guardados
from mgitems.nucleo import Nucleo

TITULO = "MG Items"
UI = Path(__file__).parent / "ui" / "index.html"
_NO_VALE_EN_ARCHIVOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class _GuardadosConDialogos:
    """Mis Looks, Mis acciones, Mis Prendas trucadas, Mis tiendas…: `window.pywebview.api.guardados.<método>(tipo, …)`.

    Lo de `Nucleo.guardados`, salvo exportar e importar, que piden el archivo con un diálogo: la interfaz no elige
    rutas."""

    def __init__(self, guardados: Guardados):
        self._guardados = guardados

    def lista(self, tipo: str) -> dict:
        return self._guardados.lista(tipo)

    def guardar(self, tipo: str, documento: dict) -> dict:
        return self._guardados.guardar(tipo, documento)

    def duplicar(self, tipo: str, id_documento: str) -> dict:
        return self._guardados.duplicar(tipo, id_documento)

    def borrar(self, tipo: str, id_documento: str) -> dict:
        return self._guardados.borrar(tipo, id_documento)

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


def _tipos_de_archivo(t) -> tuple[str, str]:
    return (f"{t.nombre} de MG Items (*.{t.extension})", "Todos los archivos (*.*)")


class Puente:
    """Lo que la interfaz puede llamar como `window.pywebview.api.<método>`.

    Delega todo en el núcleo y solo agrega lo que necesita una ventana (diálogos).
    Los atributos empiezan con `_` para que pywebview no los exponga a la interfaz.
    """

    def __init__(self, nucleo: Nucleo):
        self._nucleo = nucleo
        self.guardados = _GuardadosConDialogos(nucleo.guardados)

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

    def decoracion_de_swfs(self, swfs: list | None = None) -> dict:
        return self._nucleo.decoracion_de_swfs(swfs)

    def items_de_swfs(self, swfs: list | None = None) -> dict:
        return self._nucleo.items_de_swfs(swfs)

    def piezas(self, swf: str | None = None) -> dict:
        return self._nucleo.piezas(swf)

    def trucar_prenda(self, base: str, parte: str, pieza: str) -> dict:
        return self._nucleo.trucar_prenda(base, parte, pieza)

    def partes_del_cuerpo(self) -> dict:
        return self._nucleo.partes_del_cuerpo()

    def aplicar_look(self, look: dict) -> dict:
        return self._nucleo.aplicar_look(look)

    def trucar_varias(self, trucadas: list) -> dict:
        return self._nucleo.trucar_varias(trucadas)

    def animaciones(self) -> dict:
        return self._nucleo.animaciones()

    def aplicar_accion(self, accion: dict) -> dict:
        return self._nucleo.aplicar_accion(accion)

    def animacion_de_accion(self, accion: dict, colores: dict | None = None) -> dict:
        return self._nucleo.animacion_de_accion(accion, colores)

    def dibujos_de_la_interfaz(self) -> dict:
        return self._nucleo.dibujos_de_la_interfaz()

    def estado_busqueda(self) -> dict:
        return self._nucleo.estado_busqueda()

    def preparar_busqueda(self) -> dict:
        return self._nucleo.preparar_busqueda()

    def progreso_busqueda(self) -> dict:
        return self._nucleo.progreso_busqueda()

    def opciones_que_es(self) -> dict:
        return self._nucleo.opciones_que_es()

    def buscar_por_imagen(self, imagen: str, recorte: list | None = None, que: str | None = None,
                          se_parece: list | None = None, descartados: list | None = None) -> dict:
        return self._nucleo.buscar_por_imagen(imagen, recorte, que, se_parece, descartados)

    def comportamientos(self, tipo: str) -> dict:
        return self._nucleo.comportamientos(tipo)

    def buscar_comportamientos_en_el_juego(self) -> dict:
        return self._nucleo.buscar_comportamientos_en_el_juego()

    def comportamiento(self, nombre: str) -> dict:
        return self._nucleo.comportamiento(nombre)

    def convertir_en_npcs(self, pedidos: list) -> dict:
        return self._nucleo.convertir_en_npcs(pedidos)

    def fondos(self) -> dict:
        return self._nucleo.fondos()

    def cuadros_de_fondo(self, ruta: str) -> dict:
        return self._nucleo.cuadros_de_fondo(ruta)

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

"""Entrega al juego automatizando Fiddler (ver ADR 0002).

El AutoResponder de Fiddler responde el pedido de `lola.npc` con el Encode. Como
Fiddler guarda sus reglas al cerrarse, primero se lo cierra, después se escriben
las reglas y por último se lo vuelve a abrir. Las reglas del programa se reconocen
porque apuntan a archivos dentro de su propia carpeta de entregas.
"""

import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from mgitems.fuente import URL_ASSETS

URL_LOLA = "https://cdn-ar.mundogaturro.com/juego/npc/lola.npc?cache=no%20cache"
ARCHIVO_REGLAS = "AutoResponder.xml"
ARCHIVO_RESPALDO = "AutoResponder.mgitems.bak"
PUERTO_FIDDLER_POR_DEFECTO = 8888

QUE_HACER_EN_EL_JUEGO = (
    "Cuando cargue Mundo Gaturro, andá hasta Lola y hacé clic en ella para recibir los Items. "
    "Mientras la regla esté activa, Lola entrega este Encode; podés quitarla desde Configuración."
)


class ReglasIlegibles(Exception):
    """El archivo de reglas de Fiddler existe pero no se puede interpretar."""


class Procesos:
    """Abrir y cerrar programas de Windows."""

    _SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def corriendo(self, ejecutable: Path) -> bool:
        salida = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {ejecutable.name}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, creationflags=self._SIN_VENTANA,
        ).stdout
        return f'"{ejecutable.name.lower()}"' in salida.lower()

    def cerrar(self, ejecutable: Path, espera: float) -> bool:
        """Cierra el programa como si se tocara la X; si no responde, lo fuerza. True si quedó cerrado."""
        for forzar in (False, True):
            if not self.corriendo(ejecutable):
                return True
            comando = ["taskkill", "/IM", ejecutable.name, "/T"] + (["/F"] if forzar else [])
            subprocess.run(comando, capture_output=True, creationflags=self._SIN_VENTANA)
            if self._esperar(lambda: not self.corriendo(ejecutable), espera):
                return True
        return not self.corriendo(ejecutable)

    def abrir(self, ejecutable: Path) -> None:
        subprocess.Popen(
            [str(ejecutable)], cwd=ejecutable.parent, close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def esperar_puerto(self, puerto: int, espera: float) -> bool:
        """Espera a que un programa local escuche en el puerto (Fiddler listo para capturar)."""
        import socket

        def escucha():
            with socket.socket() as s:
                s.settimeout(0.5)
                return s.connect_ex(("127.0.0.1", puerto)) == 0

        return self._esperar(escucha, espera)

    @staticmethod
    def _esperar(condicion, espera: float) -> bool:
        limite = time.monotonic() + espera
        while time.monotonic() < limite:
            if condicion():
                return True
            time.sleep(0.5)
        return condicion()


# --- Reglas del AutoResponder ---

def _leer_reglas(archivo: Path) -> ET.ElementTree:
    if not archivo.exists():
        raiz = ET.Element("AutoResponder")
        ET.SubElement(raiz, "State", {"Enabled": "true", "Fallthrough": "true", "UseLatency": "false"})
        return ET.ElementTree(raiz)
    try:
        arbol = ET.parse(archivo)
    except ET.ParseError as e:
        raise ReglasIlegibles(f"No se pudo leer {archivo.name}") from e
    if arbol.getroot().tag != "AutoResponder" or arbol.getroot().find("State") is None:
        raise ReglasIlegibles(f"{archivo.name} no tiene el formato esperado")
    return arbol


def _guardar_reglas(arbol: ET.ElementTree, archivo: Path) -> None:
    ET.indent(arbol, space="  ")
    contenido = ET.tostring(arbol.getroot(), encoding="unicode")
    archivo.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + contenido, encoding="utf-8-sig")


def _es_propia(regla: ET.Element, carpeta_propia: Path) -> bool:
    return PureWindowsPath(regla.get("Action", "")).is_relative_to(PureWindowsPath(carpeta_propia))


def poner_reglas(archivo: Path, reglas: list[tuple[str, Path]], carpeta_propia: Path) -> None:
    """Deja `reglas` (match → archivo) primeras y activas, reemplazando las anteriores del programa.

    Las reglas del jugador se conservan tal cual. Se activa el AutoResponder y el
    paso de los pedidos que no coinciden con ninguna regla.
    """
    arbol = _leer_reglas(archivo)
    estado = arbol.getroot().find("State")
    for regla in [r for r in estado.findall("ResponseRule") if _es_propia(r, carpeta_propia)]:
        estado.remove(regla)
    for posicion, (match, accion) in enumerate(reglas):
        nueva = ET.Element("ResponseRule", {"Match": match, "Action": str(accion), "Enabled": "true"})
        estado.insert(posicion, nueva)
    estado.set("Enabled", "true")
    estado.set("Fallthrough", "true")
    _guardar_reglas(arbol, archivo)


def quitar_reglas(archivo: Path, carpeta_propia: Path) -> int:
    """Quita las reglas del programa y devuelve cuántas había."""
    if not archivo.exists():
        return 0
    arbol = _leer_reglas(archivo)
    estado = arbol.getroot().find("State")
    propias = [r for r in estado.findall("ResponseRule") if _es_propia(r, carpeta_propia)]
    for regla in propias:
        estado.remove(regla)
    if propias:
        _guardar_reglas(arbol, archivo)
    return len(propias)


def respaldar(archivo: Path) -> Path | None:
    if not archivo.exists():
        return None
    respaldo = archivo.with_name(ARCHIVO_RESPALDO)
    shutil.copy2(archivo, respaldo)
    return respaldo


def vaciar_cache(perfil_juego: Path) -> None:
    """Borra solo el caché HTTP del juego (la carpeta `Cache`); cuentas, cookies y datos quedan."""
    cache = perfil_juego / "Cache"
    if cache.exists():
        shutil.rmtree(cache)


@dataclass
class Paso:
    nombre: str
    ok: bool
    detalle: str = ""


@dataclass
class SwfTrucado:
    nombre: str  # como en el CDN, con subcarpeta si la tiene: "clothes1", "antro2017/wears"
    data: bytes
    tamano_original: int  # el del SWF original en el CDN: el juego lo pide con ese número


class PasoFallido(Exception):
    def __init__(self, detalle: str, que_hacer: str):
        super().__init__(detalle)
        self.detalle = detalle
        self.que_hacer = que_hacer


class Entrega:
    """La secuencia completa de entregar un Encode al juego, paso a paso."""

    ESPERA_CIERRE = 15.0
    ESPERA_FIDDLER = 30.0

    def __init__(self, juego: Path, perfil: Path, fiddler: Path, carpeta_reglas: Path,
                 carpeta_entregas: Path, puerto_fiddler: int, procesos: Procesos):
        self.juego = juego
        self.perfil = perfil
        self.fiddler = fiddler
        self.reglas = carpeta_reglas / ARCHIVO_REGLAS
        self.carpeta_entregas = carpeta_entregas
        self.puerto_fiddler = puerto_fiddler
        self.procesos = procesos
        self.pasos: list[Paso] = []

    def entregar(self, encode: str, swfs_trucados: list["SwfTrucado"] = ()) -> None:
        """Lanza PasoFallido en el primer paso que falla; `self.pasos` dice hasta dónde se llegó.

        Cada SWF trucado se responde en lugar del original: el juego lo pide con su
        tamaño en bytes como parámetro (`<swf>.swf?<bytes>`).
        """
        self._paso("Cerrar Mundo Gaturro", self._cerrar_juego)
        self._paso("Cerrar Fiddler", self._cerrar_fiddler)
        destino = self.carpeta_entregas / "lola.txt"
        self._paso("Guardar el Encode", lambda: self._guardar_encode(destino, encode))
        reglas = [("EXACT:" + URL_LOLA, destino)]
        for trucado in swfs_trucados:
            archivo = self.carpeta_entregas.joinpath("swf", *trucado.nombre.split("/")).with_suffix(".swf")
            self._paso(f"Guardar el SWF trucado ({trucado.nombre})", lambda t=trucado, a=archivo: self._guardar_swf(a, t.data))
            reglas.append((f"EXACT:{URL_ASSETS}{trucado.nombre}.swf?{trucado.tamano_original}", archivo))
        self._paso("Respaldar las reglas de Fiddler", self._respaldar)
        nombre_paso = "Escribir las reglas de Lola y del SWF trucado" if swfs_trucados else "Escribir la regla de Lola"
        self._paso(nombre_paso, lambda: self._escribir(reglas))
        self._paso("Borrar el caché del juego", self._vaciar_cache)
        self._paso("Abrir Fiddler", self._abrir_fiddler)
        self._paso("Abrir Mundo Gaturro", self._abrir_juego)

    def desactivar(self) -> int:
        """Quita las reglas del programa. Devuelve cuántas había."""
        estaba_abierto = self.procesos.corriendo(self.fiddler)
        self._paso("Cerrar Fiddler", self._cerrar_fiddler)
        quitadas = []
        self._paso("Respaldar las reglas de Fiddler", self._respaldar)
        self._paso("Quitar las reglas de MG Items", lambda: quitadas.append(self._quitar()))
        if estaba_abierto:
            self._paso("Abrir Fiddler", self._abrir_fiddler)
        return quitadas[0]

    def _paso(self, nombre: str, accion) -> None:
        try:
            detalle = accion() or ""
        except PasoFallido as e:
            self.pasos.append(Paso(nombre, False, e.detalle))
            raise
        self.pasos.append(Paso(nombre, True, detalle if isinstance(detalle, str) else ""))

    def _cerrar_juego(self) -> str:
        if not self.procesos.corriendo(self.juego):
            return "No estaba abierto."
        if not self.procesos.cerrar(self.juego, self.ESPERA_CIERRE):
            raise PasoFallido("Mundo Gaturro no se cerró.", "Cerralo a mano y tocá «Agregar al juego» de nuevo.")
        return ""

    def _cerrar_fiddler(self) -> str:
        if not self.procesos.corriendo(self.fiddler):
            return "No estaba abierto."
        if not self.procesos.cerrar(self.fiddler, self.ESPERA_CIERRE):
            raise PasoFallido("Fiddler no se cerró.", "Cerralo a mano y probá de nuevo.")
        return ""

    def _guardar_encode(self, destino: Path, encode: str) -> None:
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(encode, encoding="ascii")
        except OSError as e:
            raise PasoFallido(f"No se pudo guardar el Encode: {e.strerror or e}.", "Probá de nuevo.") from e

    def _guardar_swf(self, destino: Path, data: bytes) -> None:
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(data)
        except OSError as e:
            raise PasoFallido(f"No se pudo guardar el SWF trucado: {e.strerror or e}.", "Probá de nuevo.") from e

    def _respaldar(self) -> str:
        try:
            respaldo = respaldar(self.reglas)
        except OSError as e:
            raise PasoFallido(f"No se pudo copiar {self.reglas.name}: {e.strerror or e}.", "Probá de nuevo.") from e
        return f"Copia en {respaldo.name}." if respaldo else "Todavía no había reglas."

    def _escribir(self, reglas: list[tuple[str, Path]]) -> None:
        try:
            poner_reglas(self.reglas, reglas, self.carpeta_entregas)
        except ReglasIlegibles as e:
            raise PasoFallido(
                f"{e}.",
                f"Abrí Fiddler, revisá la pestaña AutoResponder y cerralo. Si sigue fallando, borrá {self.reglas.name} "
                f"de la carpeta de reglas (hay una copia en {ARCHIVO_RESPALDO}).",
            ) from e
        except OSError as e:
            raise PasoFallido(f"No se pudieron guardar las reglas: {e.strerror or e}.", "Probá de nuevo.") from e

    def _quitar(self) -> int:
        try:
            return quitar_reglas(self.reglas, self.carpeta_entregas)
        except ReglasIlegibles as e:
            raise PasoFallido(f"{e}.", "Abrí Fiddler y quitá la regla a mano desde la pestaña AutoResponder.") from e
        except OSError as e:
            raise PasoFallido(f"No se pudieron guardar las reglas: {e.strerror or e}.", "Probá de nuevo.") from e

    def _vaciar_cache(self) -> None:
        try:
            vaciar_cache(self.perfil)
        except OSError as e:
            raise PasoFallido(
                "El caché del juego está en uso.",
                "Asegurate de que Mundo Gaturro esté cerrado (también en la bandeja del sistema) y probá de nuevo.",
            ) from e

    def _abrir_juego(self) -> None:
        try:
            self.procesos.abrir(self.juego)
        except OSError as e:
            raise PasoFallido(f"No se pudo abrir Mundo Gaturro: {e.strerror or e}.", "Abrilo a mano.") from e

    def _abrir_fiddler(self) -> None:
        try:
            self.procesos.abrir(self.fiddler)
        except OSError as e:
            raise PasoFallido(f"No se pudo abrir Fiddler: {e.strerror or e}.", "Abrilo a mano.") from e
        if not self.procesos.esperar_puerto(self.puerto_fiddler, self.ESPERA_FIDDLER):
            raise PasoFallido(
                "Fiddler se abrió pero no empezó a capturar.",
                "Fijate que en Fiddler esté activado File → Capture Traffic y abrí Mundo Gaturro a mano.",
            )

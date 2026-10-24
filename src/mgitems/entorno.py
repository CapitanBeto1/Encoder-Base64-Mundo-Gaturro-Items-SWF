"""Entorno del jugador: Mundo Gaturro Desktop, Fiddler Classic y su configuración.

Todo lo que se lee de Windows pasa por `Sistema`, para que las pruebas lo
reemplacen por carpetas temporales y valores simulados.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

CERTIFICADO_FIDDLER = "DO_NOT_TRUST_FiddlerRoot"


class Sistema:
    """Lo que el entorno necesita de Windows."""

    def variable(self, nombre: str) -> str | None:
        import os

        return os.environ.get(nombre)

    def carpeta_documentos(self) -> Path | None:
        """La carpeta Documentos real del usuario (puede estar redirigida, por ejemplo a OneDrive)."""
        import ctypes
        import uuid

        class GUID(ctypes.Structure):
            _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort), ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]

        guid = GUID()
        ctypes.memmove(ctypes.byref(guid), uuid.UUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}").bytes_le, 16)
        ruta = ctypes.c_wchar_p()
        try:
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(ruta)) != 0:
                return None
            return Path(ruta.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(ruta)

    def programas_instalados(self) -> list[dict]:
        """Entradas de "Agregar o quitar programas": `DisplayName`, `InstallLocation`, `DisplayIcon`."""
        import winreg

        claves = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        programas = []
        for raiz, ruta in claves:
            try:
                clave = winreg.OpenKey(raiz, ruta)
            except OSError:
                continue
            with clave:
                for i in range(winreg.QueryInfoKey(clave)[0]):
                    try:
                        with winreg.OpenKey(clave, winreg.EnumKey(clave, i)) as programa:
                            programas.append({
                                nombre: _valor_registro(programa, nombre)
                                for nombre in ("DisplayName", "InstallLocation", "DisplayIcon")
                            })
                    except OSError:
                        continue
        return programas

    def ajuste_fiddler(self, nombre: str) -> str | None:
        """Un ajuste de Fiddler Classic (los guarda en el registro al cerrarse)."""
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Fiddler2") as clave:
                return _valor_registro(clave, nombre)
        except OSError:
            return None

    def certificado_raiz_instalado(self, nombre: str) -> bool:
        import ssl

        marca = nombre.encode("ascii")
        return any(marca in certificado for certificado, _, _ in ssl.enum_certificates("ROOT"))


def _valor_registro(clave, nombre: str) -> str | None:
    import winreg

    try:
        valor, _ = winreg.QueryValueEx(clave, nombre)
    except OSError:
        return None
    return str(valor)


@dataclass
class Componente:
    """Algo que tiene que estar presente para entregar Items al juego."""

    id: str
    nombre: str
    ok: bool
    detalle: str
    ruta: str | None = None
    # Qué se puede elegir a mano: "archivo" (un .exe), "carpeta", o None si no aplica.
    corregible: str | None = None
    corregida: bool = False
    instrucciones: list[str] = field(default_factory=list)


class Entorno:
    def __init__(self, sistema: Sistema):
        self._sistema = sistema

    def carpeta_programa(self) -> Path:
        """Donde el programa guarda su configuración y sus entregas."""
        appdata = self._sistema.variable("APPDATA")
        if not appdata:
            raise OSError("No se encontró la carpeta APPDATA")
        return Path(appdata) / "MGItems"

    def puerto_fiddler(self, por_defecto: int) -> int:
        valor = self._sistema.ajuste_fiddler("ListenPort")
        return int(valor) if valor and valor.isdigit() else por_defecto

    # --- Rutas elegidas a mano ---

    def _archivo_config(self) -> Path | None:
        try:
            return self.carpeta_programa() / "config.json"
        except OSError:
            return None

    def _config(self) -> dict:
        archivo = self._archivo_config()
        try:
            return json.loads(archivo.read_text(encoding="utf-8")) if archivo else {}
        except (OSError, ValueError):
            return {}

    def _guardar_config(self, config: dict) -> None:
        archivo = self._archivo_config()
        if archivo is None:
            raise OSError("No se encontró la carpeta de configuración (APPDATA)")
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    def _ruta_corregida(self, id_componente: str) -> Path | None:
        ruta = self._config().get("rutas", {}).get(id_componente)
        return Path(ruta) if ruta else None

    def corregir_ruta(self, id_componente: str, ruta: str) -> None:
        """Guarda una ruta elegida a mano. Lanza ValueError si no corresponde al componente."""
        tipo = _CORREGIBLES.get(id_componente)
        if tipo is None:
            raise ValueError("Ese componente no se puede elegir a mano.")
        candidata = Path(ruta)
        if tipo == "archivo" and not candidata.is_file():
            raise ValueError(f"No existe el archivo {candidata}.")
        if tipo == "carpeta" and not candidata.is_dir():
            raise ValueError(f"No existe la carpeta {candidata}.")
        nombre_esperado = _EJECUTABLES.get(id_componente)
        if nombre_esperado and candidata.name.lower() != nombre_esperado.lower():
            raise ValueError(f"Elegí el archivo {nombre_esperado}.")

        config = self._config()
        config.setdefault("rutas", {})[id_componente] = str(candidata)
        self._guardar_config(config)

    def restablecer_ruta(self, id_componente: str) -> None:
        """Vuelve a detectar la ruta automáticamente."""
        config = self._config()
        if config.get("rutas", {}).pop(id_componente, None) is not None:
            self._guardar_config(config)

    # --- Detección ---

    def componentes(self) -> list[Componente]:
        juego = self._detectar_juego()
        fiddler = self._detectar_fiddler()
        return [
            juego,
            self._detectar_perfil(juego.ok),
            fiddler,
            self._detectar_carpeta_reglas(fiddler.ok),
            self._detectar_https(fiddler.ok),
            self._detectar_certificado(fiddler.ok),
        ]

    def ruta(self, id_componente: str) -> Path | None:
        """La ruta de un componente presente (juego, perfil, fiddler, reglas), o None."""
        for componente in self.componentes():
            if componente.id == id_componente and componente.ok and componente.ruta:
                return Path(componente.ruta)
        return None

    def _ubicar(self, id_componente: str, candidatas: list[Path | None], es_valida) -> tuple[Path | None, bool]:
        """(ruta encontrada, si viene de una corrección a mano)."""
        corregida = self._ruta_corregida(id_componente)
        if corregida is not None:
            return (corregida if es_valida(corregida) else None), True
        for candidata in candidatas:
            if candidata is not None and es_valida(candidata):
                return candidata, False
        return None, False

    def _programa(self, nombre_mostrado: str) -> dict | None:
        for programa in self._sistema.programas_instalados():
            if (programa.get("DisplayName") or "").strip().lower() == nombre_mostrado.lower():
                return programa
        return None

    def _carpeta_de_variable(self, variable: str, *partes: str) -> Path | None:
        base = self._sistema.variable(variable)
        return Path(base, *partes) if base else None

    def _detectar_juego(self) -> Componente:
        candidatas = []
        if programa := self._programa("MundoGaturro"):
            candidatas.append(_ruta_de_icono(programa.get("DisplayIcon")))
        candidatas.append(self._carpeta_de_variable("LOCALAPPDATA", "Programs", "gaturro-desktop", "MundoGaturro.exe"))
        ruta, corregida = self._ubicar("juego", candidatas, Path.is_file)
        if ruta:
            return Componente("juego", "Mundo Gaturro Desktop", True, "Instalado.", str(ruta), "archivo", corregida)
        return Componente(
            "juego", "Mundo Gaturro Desktop", False,
            "La ruta elegida ya no existe." if corregida else "No se encontró Mundo Gaturro Desktop.",
            corregible="archivo", corregida=corregida,
            instrucciones=[
                "Descargá Mundo Gaturro Desktop desde la página oficial de Mundo Gaturro.",
                "Instalalo y abrilo una vez.",
                "Volvé acá y tocá «Revisar de nuevo».",
                "Si ya está instalado en otro lugar, tocá «Elegir…» y buscá el archivo MundoGaturro.exe.",
            ],
        )

    def _detectar_perfil(self, hay_juego: bool) -> Componente:
        candidatas = [self._carpeta_de_variable("APPDATA", "MundoGaturro")]
        ruta, corregida = self._ubicar("perfil", candidatas, Path.is_dir)
        if ruta:
            return Componente("perfil", "Datos del juego", True, "Encontrados (ahí está el caché del juego).", str(ruta), "carpeta", corregida)
        pasos = [
            "Abrí Mundo Gaturro Desktop e iniciá sesión al menos una vez: eso crea su carpeta de datos.",
            "Volvé acá y tocá «Revisar de nuevo».",
        ]
        if not hay_juego:
            pasos.insert(0, "Primero instalá Mundo Gaturro Desktop (ver arriba).")
        return Componente(
            "perfil", "Datos del juego", False,
            "La carpeta elegida ya no existe." if corregida else "No se encontró la carpeta de datos del juego.",
            corregible="carpeta", corregida=corregida, instrucciones=pasos,
        )

    def _detectar_fiddler(self) -> Componente:
        candidatas = []
        if (programa := self._programa("Progress Telerik Fiddler Classic")) and programa.get("InstallLocation"):
            candidatas.append(Path(programa["InstallLocation"].strip('"'), "Fiddler.exe"))
        candidatas += [
            self._carpeta_de_variable("LOCALAPPDATA", "Programs", "Fiddler", "Fiddler.exe"),
            self._carpeta_de_variable("ProgramFiles(x86)", "Fiddler2", "Fiddler.exe"),
            self._carpeta_de_variable("ProgramFiles", "Fiddler2", "Fiddler.exe"),
        ]
        ruta, corregida = self._ubicar("fiddler", candidatas, Path.is_file)
        if ruta:
            return Componente("fiddler", "Fiddler Classic", True, "Instalado.", str(ruta), "archivo", corregida)
        return Componente(
            "fiddler", "Fiddler Classic", False,
            "La ruta elegida ya no existe." if corregida else "No se encontró Fiddler Classic.",
            corregible="archivo", corregida=corregida,
            instrucciones=[
                "Descargá Fiddler Classic (es gratis) desde la página de Telerik: telerik.com/fiddler/fiddler-classic.",
                "Instalalo con las opciones que vienen marcadas.",
                "Abrilo una vez y cerralo.",
                "Volvé acá y tocá «Revisar de nuevo».",
                "Si ya está instalado en otro lugar, tocá «Elegir…» y buscá el archivo Fiddler.exe.",
            ],
        )

    def _detectar_carpeta_reglas(self, hay_fiddler: bool) -> Componente:
        documentos = self._sistema.carpeta_documentos()
        candidatas = [documentos / "Fiddler2" if documentos else None]
        ruta, corregida = self._ubicar("reglas", candidatas, Path.is_dir)
        if ruta:
            return Componente("reglas", "Carpeta de reglas de Fiddler", True, "Encontrada.", str(ruta), "carpeta", corregida)
        pasos = [
            "Abrí Fiddler Classic una vez y cerralo: eso crea la carpeta Fiddler2 dentro de Documentos.",
            "Volvé acá y tocá «Revisar de nuevo».",
        ]
        if not hay_fiddler:
            pasos.insert(0, "Primero instalá Fiddler Classic (ver arriba).")
        return Componente(
            "reglas", "Carpeta de reglas de Fiddler", False,
            "La carpeta elegida ya no existe." if corregida else "No se encontró la carpeta Fiddler2 en Documentos.",
            corregible="carpeta", corregida=corregida, instrucciones=pasos,
        )

    def _detectar_https(self, hay_fiddler: bool) -> Componente:
        activo = all(
            (self._sistema.ajuste_fiddler(ajuste) or "").lower() == "true"
            for ajuste in ("CaptureCONNECT", "CaptureHTTPS")
        )
        if activo:
            return Componente("https", "Descifrado HTTPS en Fiddler", True, "Activado.")
        pasos = [
            "Abrí Fiddler Classic.",
            "Entrá a Tools → Options… y elegí la pestaña HTTPS.",
            "Marcá «Capture HTTPS CONNECTs» y «Decrypt HTTPS traffic».",
            "Si Fiddler pregunta si confiar en su certificado, respondé Yes, y en la advertencia de Windows respondé Sí.",
            "Tocá OK y cerrá Fiddler para que guarde la configuración.",
            "Volvé acá y tocá «Revisar de nuevo».",
        ]
        if not hay_fiddler:
            pasos.insert(0, "Primero instalá Fiddler Classic (ver arriba).")
        return Componente("https", "Descifrado HTTPS en Fiddler", False, "Está desactivado.", instrucciones=pasos)

    def _detectar_certificado(self, hay_fiddler: bool) -> Componente:
        if self._sistema.certificado_raiz_instalado(CERTIFICADO_FIDDLER):
            return Componente("certificado", "Certificado de Fiddler", True, "Instalado.")
        pasos = [
            "Abrí Fiddler Classic.",
            "Entrá a Tools → Options… → pestaña HTTPS → botón Actions → «Trust Root Certificate».",
            "En la advertencia de Windows respondé Sí.",
            "Volvé acá y tocá «Revisar de nuevo».",
        ]
        if not hay_fiddler:
            pasos.insert(0, "Primero instalá Fiddler Classic (ver arriba).")
        return Componente("certificado", "Certificado de Fiddler", False, "No está instalado.", instrucciones=pasos)


_CORREGIBLES = {"juego": "archivo", "perfil": "carpeta", "fiddler": "archivo", "reglas": "carpeta"}
_EJECUTABLES = {"juego": "MundoGaturro.exe", "fiddler": "Fiddler.exe"}


def _ruta_de_icono(icono: str | None) -> Path | None:
    """`DisplayIcon` del registro (`"C:\\…\\X.exe",0`) como ruta del ejecutable."""
    if not icono:
        return None
    ruta, _, indice = icono.rpartition(",")
    if not ruta or not indice.strip().lstrip("-").isdigit():
        ruta = icono
    return Path(ruta.strip().strip('"'))

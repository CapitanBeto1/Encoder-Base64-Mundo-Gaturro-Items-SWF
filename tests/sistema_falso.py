"""Un Windows simulado sobre una carpeta temporal, para probar la detección del entorno."""

from pathlib import Path

from mgitems.entorno import CERTIFICADO_FIDDLER, Sistema


class SistemaFalso(Sistema):
    def __init__(self, base: Path):
        self.base = base
        self.variables = {
            "LOCALAPPDATA": str(base / "Local"),
            "APPDATA": str(base / "Roaming"),
            "ProgramFiles": str(base / "Program Files"),
            "ProgramFiles(x86)": str(base / "Program Files (x86)"),
        }
        self.documentos = base / "Documentos"
        self.programas: list[dict] = []
        self.ajustes: dict[str, str] = {}
        self.certificados: set[str] = set()

    def variable(self, nombre):
        return self.variables.get(nombre)

    def carpeta_documentos(self):
        return self.documentos

    def programas_instalados(self):
        return self.programas

    def ajuste_fiddler(self, nombre):
        return self.ajustes.get(nombre)

    def certificado_raiz_instalado(self, nombre):
        return nombre in self.certificados

    # --- Armado de escenarios ---

    def instalar_juego(self, carpeta: Path | None = None) -> Path:
        exe = crear_archivo((carpeta or self.base / "Local" / "Programs" / "gaturro-desktop") / "MundoGaturro.exe")
        self.programas.append({"DisplayName": "MundoGaturro", "InstallLocation": "", "DisplayIcon": f"{exe},0"})
        (self.base / "Roaming" / "MundoGaturro" / "Cache").mkdir(parents=True)
        return exe

    def instalar_fiddler(self, carpeta: Path | None = None, https: bool = True, certificado: bool = True) -> Path:
        carpeta = carpeta or self.base / "Local" / "Programs" / "Fiddler"
        exe = crear_archivo(carpeta / "Fiddler.exe")
        self.programas.append({
            "DisplayName": "Progress Telerik Fiddler Classic",
            "InstallLocation": str(carpeta),
            "DisplayIcon": f'"{carpeta / "App.ico"}"',
        })
        (self.documentos / "Fiddler2").mkdir(parents=True)
        self.ajustes = {"CaptureCONNECT": "True", "CaptureHTTPS": "True" if https else "False", "ListenPort": "8888"}
        if certificado:
            self.certificados.add(CERTIFICADO_FIDDLER)
        return exe


def crear_archivo(ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"")
    return ruta

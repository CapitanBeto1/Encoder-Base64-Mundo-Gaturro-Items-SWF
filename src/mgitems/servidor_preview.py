"""Servidor local que sirve la interfaz por http para que Ruffle (emulador de Flash) pueda correr.

La ventana carga la interfaz desde `http://127.0.0.1:<puerto>/` en vez de `file://`, porque Ruffle necesita un
origen http para cargar el `preview.swf` (el avatar del juego) y los SWF de los Items. Además de los archivos de
la interfaz (`ui/`), expone:
  - `/ruffle/<archivo>`      los archivos de Ruffle y el `preview.swf` (de `vendor/ruffle/`, no versionado)
  - `/preview.swf`           el avatar envuelto que se viste con `changeAttr`
  - `/assets/<pack>.swf`     el SWF de un pack, del caché local o del CDN (lo que Ruffle pide para vestir)
"""

import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mgitems.fuente import FuenteCDN, SwfNoEncontrado

RAIZ = Path(__file__).resolve().parent.parent.parent
UI = Path(__file__).resolve().parent / "ui"
RUFFLE = RAIZ / "vendor" / "ruffle"


def _carpeta_cache() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    destino = (Path(local) / "MGItems" / "swf") if local else (RAIZ / "vendor" / "swf_cache")
    destino.mkdir(parents=True, exist_ok=True)
    return destino


class _Handler(SimpleHTTPRequestHandler):
    """Sirve `ui/` como raíz, con rutas extra para Ruffle y los assets."""

    def __init__(self, *args, fuente: FuenteCDN, cache: Path, **kwargs):
        self._fuente = fuente
        self._cache = cache
        super().__init__(*args, directory=str(UI), **kwargs)

    def log_message(self, *args):
        pass  # sin ruido en la consola

    def _enviar(self, data: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _swf_de_pack(self, pack: str) -> bytes | None:
        local = self._cache / f"{pack}.swf"
        if local.exists():
            return local.read_bytes()
        try:
            data = self._fuente.descargar(pack)
        except (SwfNoEncontrado, OSError):
            return None
        try:
            local.write_bytes(data)
        except OSError:
            pass
        return data

    def do_GET(self):
        ruta = self.path.split("?", 1)[0]
        if ruta.startswith("/assets/") and ruta.endswith(".swf"):
            pack = ruta[len("/assets/"):-len(".swf")]
            data = self._swf_de_pack(pack)
            if data is None:
                self.send_error(404)
            else:
                self._enviar(data, "application/x-shockwave-flash")
            return
        if ruta == "/preview.swf":
            self._servir_ruffle("preview.swf")
            return
        if ruta.startswith("/ruffle/"):
            self._servir_ruffle(ruta[len("/ruffle/"):])
            return
        super().do_GET()

    def _servir_ruffle(self, nombre: str):
        archivo = (RUFFLE / nombre).resolve()
        if not str(archivo).startswith(str(RUFFLE.resolve())) or not archivo.is_file():
            self.send_error(404)
            return
        ctype = {".js": "application/javascript", ".wasm": "application/wasm",
                 ".swf": "application/x-shockwave-flash"}.get(archivo.suffix, "application/octet-stream")
        self._enviar(archivo.read_bytes(), ctype)


class ServidorPreview:
    """Servidor local en un hilo. `iniciar()` devuelve la URL de la interfaz."""

    def __init__(self):
        self._servidor: ThreadingHTTPServer | None = None

    def iniciar(self) -> str:
        handler = partial(_Handler, fuente=FuenteCDN(), cache=_carpeta_cache())
        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        hilo.start()
        puerto = self._servidor.server_address[1]
        return f"http://127.0.0.1:{puerto}/index.html"

    def detener(self):
        if self._servidor:
            self._servidor.shutdown()
            self._servidor = None

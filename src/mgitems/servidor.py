"""El servidor local del Gaturro en vivo (ADR 0003).

El Gaturro en vivo corre en Ruffle (un reproductor de Flash) dentro de un marco de la interfaz, y Ruffle necesita
bajar sus archivos por http. Este servidor, que solo atiende a esta computadora, le da:

- `/gaturro_vivo.html`   la página del marco (de `ui/`)
- `/ruffle/<archivo>`    Ruffle (de `vendor/ruffle`)
- `/gaturro.swf`         el Gaturro (de `vendor/gaturro`)
- `/assets/<swf>.swf`    el SWF de donde sale cada Pieza, que el Gaturro pide al vestirse
- `/banners/<nombre>.swf` el banner del editor de Piezas del juego (con su arte), sin tocar
"""

import re
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mgitems.ffdec import carpeta_vendor

PAGINA = Path(__file__).parent / "ui" / "gaturro_vivo.html"
_TIPOS = {".html": "text/html; charset=utf-8", ".js": "application/javascript", ".wasm": "application/wasm",
          ".swf": "application/x-shockwave-flash"}
_DE_RUFFLE = re.compile(r"^/ruffle/([\w.\-]+\.(?:js|wasm))$")
_ASSET = re.compile(r"^/assets/([A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*)\.swf$")
_BANNER = re.compile(r"^/banners/([A-Za-z0-9_]+)\.swf$")


class ServidorDelGaturro:
    """`iniciar()` lo deja atendiendo en un hilo y devuelve la dirección de la página del Gaturro.

    `swf(nombre)` da el SWF del juego con ese nombre, o None si no se consiguió; `banner(nombre)`, lo mismo para un
    banner."""

    def __init__(self, swf: Callable[[str], bytes | None], banner: Callable[[str], bytes | None] = lambda nombre: None):
        self._swf = swf
        self._banner = banner
        self._servidor: ThreadingHTTPServer | None = None

    def iniciar(self) -> str:
        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), self._atender())
        threading.Thread(target=self._servidor.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self._servidor.server_address[1]}/{PAGINA.name}"

    def detener(self) -> None:
        if self._servidor:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None

    def _contenido(self, ruta: str) -> tuple[bytes, str] | None:
        """(contenido, tipo) de lo que se pide, o None si no existe."""
        vendor = carpeta_vendor()
        if ruta == f"/{PAGINA.name}":
            archivo = PAGINA
        elif ruta == "/gaturro.swf":
            archivo = vendor / "gaturro" / "gaturro.swf"
        elif pedido := _DE_RUFFLE.match(ruta):
            archivo = vendor / "ruffle" / pedido[1]
        elif pedido := _ASSET.match(ruta):
            data = self._swf(pedido[1])
            return (data, _TIPOS[".swf"]) if data else None
        elif pedido := _BANNER.match(ruta):
            data = self._banner(pedido[1])
            return (data, _TIPOS[".swf"]) if data else None
        else:
            return None
        try:
            return archivo.read_bytes(), _TIPOS[archivo.suffix]
        except OSError:
            return None

    def _atender(self) -> type[BaseHTTPRequestHandler]:
        contenido = self._contenido

        class Atender(BaseHTTPRequestHandler):
            def do_GET(self):
                encontrado = contenido(self.path.split("?", 1)[0])
                if encontrado is None:
                    self.send_error(404)
                    return
                data, tipo = encontrado
                self.send_response(200)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass  # sin ruido en la consola

        return Atender

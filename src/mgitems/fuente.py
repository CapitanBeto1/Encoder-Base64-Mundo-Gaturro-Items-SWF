"""Fuente de SWF de assets: el CDN del juego."""

import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

URL_ASSETS = "https://cdn-ar.mundogaturro.com/juego/assets/"


class SwfNoEncontrado(Exception):
    """El SWF no existe en el CDN."""


class SinConexion(OSError):
    """No se pudo llegar al CDN (sin internet, DNS, tiempo de espera)."""


@dataclass
class Version:
    """Lo que identifica la versión de un SWF en el CDN."""

    tamano: int
    etag: str | None


class FuenteCDN:
    TIEMPO_ESPERA = 30

    def __init__(self):
        self._tls: ssl.SSLContext | None = None

    def url(self, nombre: str) -> str:
        return URL_ASSETS + urllib.parse.quote(nombre) + ".swf"

    def version(self, nombre: str) -> Version:
        with self._pedir(nombre, "HEAD") as respuesta:
            return Version(int(respuesta.headers.get("Content-Length") or 0), respuesta.headers.get("ETag"))

    def descargar(self, nombre: str) -> bytes:
        with self._pedir(nombre, "GET") as respuesta:
            return respuesta.read()

    def _pedir(self, nombre: str, metodo: str):
        pedido = urllib.request.Request(self.url(nombre), method=metodo, headers={"User-Agent": "MGItems"})
        if self._tls is None:
            self._tls = ssl.create_default_context()  # verifica certificados
        try:
            return urllib.request.urlopen(pedido, timeout=self.TIEMPO_ESPERA, context=self._tls)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise SwfNoEncontrado(nombre) from e
            raise OSError(f"el servidor respondió {e.code}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise SinConexion(str(getattr(e, "reason", e))) from e

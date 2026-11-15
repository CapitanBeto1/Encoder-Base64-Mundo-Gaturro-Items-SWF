"""Las fotos del Gaturro en vivo (las miniaturas de los guardados), guardadas para la próxima vez.

Sacarlas cuesta: un Gaturro en vivo que no se ve las saca de a una (ADR 0009), y con muchos guardados tarda y ocupa
memoria. Una foto guardada se usa solo si es de lo mismo: la clave la arma `mgitems.nucleo.fotos` con los atributos del
Gaturro, cómo se sacó y las versiones de lo que se dibuja (Ruffle, el Gaturro, el SWF de cada Pieza). Igual vencen a
los `EDAD_MAXIMA`, por si el juego cambió una Pieza y el programa todavía no se enteró.
"""

import base64
import re
import time
from pathlib import Path

EDAD_MAXIMA = 7 * 24 * 3600  # segundos
MAXIMO = 2000  # fotos guardadas; al pasarse, se borran las más viejas
_CLAVE = re.compile(r"^[0-9a-f]{64}$")
_PREFIJO = "data:image/png;base64,"
_PNG = b"\x89PNG\r\n\x1a\n"
_TAMANO_MAXIMO = 4 * 1024 * 1024


class FotoInvalida(ValueError):
    pass


class FotosGuardadas:
    def __init__(self, carpeta: Path):
        self._carpeta = carpeta

    def _archivo(self, clave: str) -> Path:
        if not _CLAVE.match(clave):
            raise FotoInvalida("Clave de foto inválida.")
        return self._carpeta / f"{clave}.png"

    def leer(self, clave: str) -> str | None:
        """La foto (data:image/png…) guardada con esa clave, o None si no está o ya venció."""
        archivo = self._archivo(clave)
        try:
            if time.time() - archivo.stat().st_mtime > EDAD_MAXIMA:
                return None
            return _PREFIJO + base64.b64encode(archivo.read_bytes()).decode("ascii")
        except OSError:
            return None

    def guardar(self, clave: str, imagen: str) -> None:
        """Guarda la foto (data:image/png…). Lanza FotoInvalida si no es un PNG."""
        archivo = self._archivo(clave)
        if not isinstance(imagen, str) or not imagen.startswith(_PREFIJO) or len(imagen) > _TAMANO_MAXIMO:
            raise FotoInvalida("La foto no es una imagen PNG.")
        try:
            png = base64.b64decode(imagen[len(_PREFIJO):], validate=True)
        except ValueError as e:
            raise FotoInvalida("La foto no es una imagen PNG.") from e
        if not png.startswith(_PNG):
            raise FotoInvalida("La foto no es una imagen PNG.")
        self._carpeta.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(png)
        self._podar()

    def _podar(self) -> None:
        fotos = list(self._carpeta.glob("*.png"))
        if len(fotos) <= MAXIMO:
            return
        fotos.sort(key=lambda f: f.stat().st_mtime)
        for vieja in fotos[: len(fotos) - MAXIMO * 3 // 4]:
            vieja.unlink(missing_ok=True)

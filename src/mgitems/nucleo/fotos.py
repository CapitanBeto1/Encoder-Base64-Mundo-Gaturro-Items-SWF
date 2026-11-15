"""Las fotos del Gaturro en vivo (las miniaturas de los guardados), guardadas para la próxima vez (`mgitems.fotos`)."""

import hashlib
import json
import re

from mgitems.cache_swf import CacheSwf
from mgitems.ffdec import carpeta_vendor
from mgitems.fotos import FotoInvalida, FotosGuardadas
from mgitems.gaturro import PARTES
from mgitems.iconos import version_de
from mgitems.nucleo._comun import _NOMBRE_SWF
from mgitems.personalizar import ruta_limpia
from mgitems.prendas import ACCION, EFECTO, PREFIJO_EFECTO

_FORMATO = re.compile(r"^[\w.\-]{1,40}$")


class Fotos:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def foto_guardada(self, atributos: dict, formato: str) -> dict:
        """La foto (data:image/png…) del Gaturro con esos atributos (los de `gaturro_en_vivo`), sacada de la forma
        `formato` (la elige la interfaz), si ya se sacó y sigue sirviendo; si no, `imagen` es None."""
        try:
            return {"ok": True, "imagen": self._fotos().leer(self._clave_de_foto(atributos, formato))}
        except (FotoInvalida, OSError) as e:
            return {"ok": False, "error": str(e)}

    def guardar_foto(self, atributos: dict, formato: str, imagen: str) -> dict:
        """Guarda la foto que la interfaz le sacó al Gaturro con esos atributos, para la próxima vez."""
        try:
            self._fotos().guardar(self._clave_de_foto(atributos, formato), imagen)
        except (FotoInvalida, OSError) as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    def _fotos(self) -> FotosGuardadas:
        return FotosGuardadas(self._entorno.carpeta_cache() / "fotos")

    def _clave_de_foto(self, atributos: dict, formato: str) -> str:
        """De qué es la foto: los atributos, cómo se sacó y las versiones de lo que se dibuja (Ruffle, el Gaturro y el
        SWF de cada Pieza, como están en esta computadora). Si cambia algo, la clave también."""
        if not isinstance(atributos, dict) or not isinstance(formato, str) or not _FORMATO.match(formato):
            raise FotoInvalida("La foto no tiene la forma esperada.")
        swfs = sorted({swf for parte, valor in atributos.items() if (swf := _swf_de(parte, valor))})
        vendor = carpeta_vendor()
        de_que_es = {
            "atributos": atributos, "formato": formato, "swfs": {swf: self._version_para_foto(swf) for swf in swfs},
            "ruffle": _version_incluida(vendor / "ruffle"), "gaturro": _version_incluida(vendor / "gaturro"),
        }
        try:
            texto = json.dumps(de_que_es, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise FotoInvalida("La foto no tiene la forma esperada.") from e
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    def _version_para_foto(self, swf: str) -> list | str | None:
        if swf == self._swf_abierto:
            return version_de(self._data_swf)
        version = CacheSwf(self._entorno.carpeta_cache() / "swf").version(swf)
        return [version.tamano, version.etag] if version else None


def _swf_de(parte: str, valor) -> str | None:
    """El SWF de la Pieza que lleva el atributo `parte`, o None si no es una Pieza."""
    if not isinstance(valor, str):
        return None
    if parte == EFECTO:
        valor = valor.removeprefix(PREFIJO_EFECTO)
    elif parte == ACCION:
        valor = valor.partition(".")[2]  # «<animación>.<swf>.<Pieza>»
    elif parte not in PARTES:
        return None
    swf = ruta_limpia(valor).rpartition(".")[0]
    return swf if _NOMBRE_SWF.match(swf) else None


def _version_incluida(carpeta) -> str:
    """La versión de un programa de `vendor/` (la que anota `scripts/obtener_binarios.py`)."""
    try:
        return (carpeta / "VERSION.mgitems").read_text(encoding="utf-8").strip()
    except OSError:
        return ""

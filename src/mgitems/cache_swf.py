"""Copias locales de los SWF descargados del CDN, con la versión de cada una."""

import json
from pathlib import Path

from mgitems.fuente import Version


class CacheSwf:
    def __init__(self, carpeta: Path):
        self._carpeta = carpeta

    def _rutas(self, nombre: str) -> tuple[Path, Path]:
        base = self._carpeta.joinpath(*nombre.split("/"))
        return base.with_name(base.name + ".swf"), base.with_name(base.name + ".version.json")

    def leer(self, nombre: str) -> tuple[bytes, Version] | None:
        swf, version = self._rutas(nombre)
        try:
            datos = json.loads(version.read_text(encoding="utf-8"))
            return swf.read_bytes(), Version(datos["tamano"], datos.get("etag"))
        except (OSError, ValueError, KeyError):
            return None

    def guardar(self, nombre: str, data: bytes, version: Version) -> None:
        swf, archivo_version = self._rutas(nombre)
        swf.parent.mkdir(parents=True, exist_ok=True)
        swf.write_bytes(data)
        archivo_version.write_text(json.dumps({"tamano": version.tamano, "etag": version.etag}), encoding="utf-8")

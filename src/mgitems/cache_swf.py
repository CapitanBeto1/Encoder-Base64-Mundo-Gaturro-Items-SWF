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
        version = self.version(nombre)
        if version is None:
            return None
        try:
            return self._rutas(nombre)[0].read_bytes(), version
        except OSError:
            return None

    def version(self, nombre: str) -> Version | None:
        """La versión de la copia guardada (sin leer el SWF), o None si no hay."""
        try:
            datos = json.loads(self._rutas(nombre)[1].read_text(encoding="utf-8"))
            return Version(datos["tamano"], datos.get("etag"))
        except (OSError, ValueError, KeyError):
            return None

    def guardar(self, nombre: str, data: bytes, version: Version) -> None:
        swf, archivo_version = self._rutas(nombre)
        swf.parent.mkdir(parents=True, exist_ok=True)
        swf.write_bytes(data)
        archivo_version.write_text(json.dumps({"tamano": version.tamano, "etag": version.etag}), encoding="utf-8")

"""Descarga los programas de terceros que el programa incluye, verificando su hash.

- FFDec (JPEXS Free Flash Decompiler): lee y exporta SWF. Queda en vendor/ffdec.
- Java (Eclipse Temurin JRE): lo necesita FFDec. Queda en vendor/java.
- Ruffle (reproductor de Flash para la web): muestra al Gaturro en vivo. Queda en vendor/ruffle.
- El Gaturro en vivo (`preview.swf` de naw-trucador, el Gaturro de pantalla del juego): queda en vendor/gaturro,
  con lo que le agrega `parchear_preview.py` (necesita FFDec).

No se versionan en git: se obtienen con este script para desarrollar y al armar
el instalador. Para desarrollar alcanza con FFDec si ya hay Java instalado.

Uso:
    python scripts/obtener_binarios.py            # todos
    python scripts/obtener_binarios.py ffdec      # solo FFDec
"""

import hashlib
import io
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import parchear_preview

VENDOR = Path(__file__).resolve().parent.parent / "vendor"


@dataclass
class Binario:
    nombre: str
    version: str
    url: str
    sha256: str
    # Carpeta dentro del zip (o del .tgz) cuyo contenido se copia (None: entero).
    carpeta_en_zip: str | None = None
    # Lo único que se copia de ahí (None: todo).
    solo: tuple[str, ...] | None = None
    # Qué hacer con la carpeta ya instalada (falla con una excepción: no queda instalado).
    despues: Callable[[Path], None] | None = None


BINARIOS = {
    "ffdec": Binario(
        "ffdec", "26.3.0",
        "https://github.com/jindrapetrik/jpexs-decompiler/releases/download/version26.3.0/ffdec_26.3.0.zip",
        "35f4930eb7c380afe66f2117f90b006deac0631473ad7500bb39c78f68645ecd",
    ),
    "java": Binario(
        "java", "21.0.12.1+1",
        "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/"
        "OpenJDK21U-jre_x64_windows_hotspot_21.0.12.1_1.zip",
        "d35f31e712f0fcf6ac5a093edc90204fbff22f720ba3950bd09d331d5e621636",
        carpeta_en_zip="jdk-21.0.12.1+1-jre",
    ),
    # El paquete de npm es el mismo armado que el «web-selfhosted» de GitHub, y no se borra con el tiempo.
    "ruffle": Binario(
        "ruffle", "0.8.0-nightly.2026.11.10",
        "https://registry.npmjs.org/@ruffle-rs/ruffle/-/ruffle-0.8.0-nightly.2026.11.10.tgz",
        "c629fd24ae3fce239ca679ba732c8b59e799115c60e1d8a3b3c44a212a8ede52",
        carpeta_en_zip="package",
        solo=("ruffle.js", "*.wasm", "LICENSE_*"),
    ),
    "gaturro": Binario(
        "gaturro", "c2e07e7+mg1",
        "https://raw.githubusercontent.com/novendotrap/naw-trucador/c2e07e71385568818f51076404a7b247ee9b2674/"
        "app/static/ruffle/preview.swf",
        "1965f0ef10a3c526f4a364396aec4f9d4d90ebca5197450932e77ecc3f2a8c7a",
        despues=parchear_preview.parchear,
    ),
}


def _archivos(binario: Binario, datos: bytes) -> Iterator[tuple[str, bytes]]:
    """(ruta dentro del archivo bajado, contenido) de cada archivo; lo que no es zip ni .tgz es un solo archivo."""
    if binario.url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(datos)) as archivo_zip:
            for miembro in archivo_zip.infolist():
                if not miembro.is_dir():
                    yield miembro.filename, archivo_zip.read(miembro)
    elif binario.url.endswith(".tgz"):
        with tarfile.open(fileobj=io.BytesIO(datos), mode="r:gz") as archivo_tar:
            for miembro in archivo_tar:
                if miembro.isfile():
                    yield miembro.name, archivo_tar.extractfile(miembro).read()
    else:
        yield binario.url.rsplit("/", 1)[-1], datos


def obtener(binario: Binario) -> None:
    destino = VENDOR / binario.nombre
    marca = destino / "VERSION.mgitems"
    if marca.exists() and marca.read_text(encoding="utf-8").strip() == binario.version:
        print(f"{binario.nombre} {binario.version} ya está en {destino}")
        return

    print(f"Descargando {binario.nombre} {binario.version}…")
    with urllib.request.urlopen(binario.url, timeout=300) as respuesta:
        datos = respuesta.read()
    obtenido = hashlib.sha256(datos).hexdigest()
    if obtenido != binario.sha256:
        sys.exit(f"El hash de {binario.nombre} no coincide (esperado {binario.sha256}, obtenido {obtenido}). No se instala.")

    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    prefijo = f"{binario.carpeta_en_zip}/" if binario.carpeta_en_zip else ""
    for nombre, contenido in _archivos(binario, datos):
        if Path(nombre).is_absolute() or ".." in Path(nombre).parts:
            sys.exit(f"Ruta sospechosa en lo bajado de {binario.nombre}: {nombre}")
        if not nombre.startswith(prefijo) or not (relativo := nombre[len(prefijo):]):
            continue
        if binario.solo and not any(Path(relativo).match(patron) for patron in binario.solo):
            continue
        salida = destino / relativo
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(contenido)
    if binario.despues:
        binario.despues(destino)
    marca.write_text(binario.version, encoding="utf-8")
    print(f"{binario.nombre} {binario.version} instalado en {destino}")


def main() -> None:
    pedidos = sys.argv[1:] or list(BINARIOS)
    desconocidos = [p for p in pedidos if p not in BINARIOS]
    if desconocidos:
        sys.exit(f"No conozco: {', '.join(desconocidos)}. Opciones: {', '.join(BINARIOS)}")
    for nombre in pedidos:
        obtener(BINARIOS[nombre])


if __name__ == "__main__":
    main()

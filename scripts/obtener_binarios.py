"""Descarga los programas de terceros que el programa incluye, verificando su hash.

- FFDec (JPEXS Free Flash Decompiler): lee y exporta SWF. Queda en vendor/ffdec.
- Java (Eclipse Temurin JRE): lo necesita FFDec. Queda en vendor/java.

No se versionan en git: se obtienen con este script para desarrollar y al armar
el instalador. Para desarrollar alcanza con FFDec si ya hay Java instalado.

Uso:
    python scripts/obtener_binarios.py            # FFDec y Java
    python scripts/obtener_binarios.py ffdec      # solo FFDec
"""

import hashlib
import io
import shutil
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / "vendor"


@dataclass
class Binario:
    nombre: str
    version: str
    url: str
    sha256: str
    # Carpeta dentro del zip cuyo contenido se copia (None: el zip entero).
    carpeta_en_zip: str | None = None


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
}


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
    with zipfile.ZipFile(io.BytesIO(datos)) as archivo_zip:
        for miembro in archivo_zip.infolist():
            partes = Path(miembro.filename).parts
            if Path(miembro.filename).is_absolute() or ".." in partes:
                sys.exit(f"Ruta sospechosa en el zip de {binario.nombre}: {miembro.filename}")
            if not miembro.filename.startswith(prefijo) or miembro.is_dir():
                continue
            relativo = miembro.filename[len(prefijo):]
            if not relativo:
                continue
            salida = destino / relativo
            salida.parent.mkdir(parents=True, exist_ok=True)
            with archivo_zip.open(miembro) as origen, open(salida, "wb") as copia:
                shutil.copyfileobj(origen, copia)
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

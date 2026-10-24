"""Descarga JPEXS FFDec (decompilador de SWF) en vendor/ffdec, verificando su hash.

FFDec no se versiona en git: se obtiene con este script para desarrollar y al
armar el instalador. Necesita Java 8 o más nuevo.

Uso:
    python scripts/obtener_ffdec.py
"""

import hashlib
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "26.3.0"
URL = f"https://github.com/jindrapetrik/jpexs-decompiler/releases/download/version{VERSION}/ffdec_{VERSION}.zip"
SHA256 = "35f4930eb7c380afe66f2117f90b006deac0631473ad7500bb39c78f68645ecd"

DESTINO = Path(__file__).resolve().parent.parent / "vendor" / "ffdec"


def main() -> None:
    marca = DESTINO / "VERSION"
    if marca.exists() and marca.read_text(encoding="utf-8").strip() == VERSION:
        print(f"FFDec {VERSION} ya está en {DESTINO}")
        return

    print(f"Descargando FFDec {VERSION}…")
    with urllib.request.urlopen(URL, timeout=120) as respuesta:
        datos = respuesta.read()
    obtenido = hashlib.sha256(datos).hexdigest()
    if obtenido != SHA256:
        sys.exit(f"El hash no coincide (esperado {SHA256}, obtenido {obtenido}). No se instala.")

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(datos)) as zip_ffdec:
        for miembro in zip_ffdec.infolist():
            # Solo rutas relativas dentro del destino.
            if Path(miembro.filename).is_absolute() or ".." in Path(miembro.filename).parts:
                sys.exit(f"Ruta sospechosa en el zip: {miembro.filename}")
        zip_ffdec.extractall(DESTINO)
    marca.write_text(VERSION, encoding="utf-8")
    print(f"FFDec {VERSION} instalado en {DESTINO}")


if __name__ == "__main__":
    main()

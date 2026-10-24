"""Arma el catálogo de SWF de assets que viene incluido en el programa.

Toma los nombres del catálogo actual más los de los archivos de texto que se
pasen (un nombre por línea, sin `.swf`, con subcarpeta si la tiene: `antro2017/wears`),
descarga cada uno del CDN del juego, cuenta sus Items y escribe el catálogo con
los que tienen al menos uno.

Uso:
    python scripts/armar_catalogo.py [nombres.txt ...] [--descargas CARPETA]
"""

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from mgitems.catalogo import ARCHIVO_CATALOGO, cargar_catalogo  # noqa: E402
from mgitems.fuente import FuenteCDN, SwfNoEncontrado  # noqa: E402
from mgitems.items import items_del_swf  # noqa: E402
from mgitems.swf import SwfInvalido, leer_clases  # noqa: E402


def contar_items(fuente: FuenteCDN, nombre: str, descargas: Path | None) -> tuple[str, int | None, str]:
    try:
        data = fuente.descargar(nombre)
    except SwfNoEncontrado:
        return nombre, None, "no existe en el CDN"
    except OSError as e:
        return nombre, None, f"error: {e}"
    if descargas:
        destino = descargas / f"{nombre}.swf"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(data)
    try:
        return nombre, len(items_del_swf(leer_clases(data))), ""
    except SwfInvalido as e:
        return nombre, None, str(e)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("nombres", nargs="*", type=Path, help="archivos con nombres de SWF a agregar")
    parser.add_argument("--descargas", type=Path, help="carpeta donde guardar los SWF descargados")
    parser.add_argument("--hilos", type=int, default=6)
    args = parser.parse_args()

    nombres = {s["swf"] for s in cargar_catalogo()}
    for archivo in args.nombres:
        nombres |= {l.strip() for l in archivo.read_text(encoding="utf-8").splitlines() if l.strip()}

    fuente = FuenteCDN()
    catalogo, descartados = [], []
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as hilos:
        for nombre, cantidad, motivo in hilos.map(lambda n: contar_items(fuente, n, args.descargas), sorted(nombres)):
            if cantidad:
                catalogo.append({"swf": nombre, "items": cantidad})
            else:
                descartados.append(f"{nombre}: {motivo or 'sin Items'}")

    catalogo.sort(key=lambda s: s["swf"].lower())
    ARCHIVO_CATALOGO.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Catálogo: {len(catalogo)} SWF con Items ({sum(s['items'] for s in catalogo)} Items en total).")
    print(f"Descartados: {len(descartados)}")
    for d in descartados:
        print("  " + d)


if __name__ == "__main__":
    main()

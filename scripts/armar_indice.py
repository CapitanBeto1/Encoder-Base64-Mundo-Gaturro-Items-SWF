"""Arma el índice de categorías de Piezas que viene incluido en el programa.

Para cada SWF del catálogo: lo descarga del CDN del juego, lee sus Prendas con FFDec y anota en
qué Parte(s) del cuerpo usa cada Pieza (también las de otros SWF que usan sus Prendas). Escribe
`src/mgitems/datos/indice_piezas.json` (solo nombres de clases, nada de arte del juego).

Tarda: FFDec analiza cada SWF (unos segundos cada uno). Necesita Java y FFDec en `vendor/`.

El análisis de cada SWF se guarda en una carpeta de trabajo (`--trabajo`, por defecto en la carpeta
temporal): si se corta (por ejemplo, sin internet), al volver a correrlo solo se analiza lo que falta
o lo que cambió en el CDN.

Uso:
    python scripts/armar_indice.py [--hilos 4] [--solo swf1,swf2] [--trabajo CARPETA]
"""

import argparse
import concurrent.futures
import json
import sys
import tempfile
import time
from collections import defaultdict

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from mgitems.catalogo import cargar_catalogo  # noqa: E402
from mgitems.categorias import ARCHIVO_INDICE, categorias, usos_de_piezas  # noqa: E402
from mgitems.fuente import FuenteCDN, SwfNoEncontrado  # noqa: E402
from mgitems.iconos import version_de  # noqa: E402
from mgitems.items import items_del_swf, piezas_del_swf  # noqa: E402
from mgitems.prendas import ItemsBaseFFDec  # noqa: E402
from mgitems.swf import SwfInvalido, leer_clases  # noqa: E402


def descargar(fuente: FuenteCDN, swf: str, intentos: int = 4) -> bytes:
    for intento in range(intentos):
        try:
            return fuente.descargar(swf)
        except SwfNoEncontrado:
            raise
        except OSError:
            if intento == intentos - 1:
                raise
            time.sleep(5 * (intento + 1))


def analizar(fuente: FuenteCDN, ffdec: ItemsBaseFFDec, trabajo: Path, swf: str) -> tuple[str, dict | None, str]:
    """(swf, {"version", "piezas", "usos"}, error). Reusa el análisis guardado si el SWF no cambió."""
    try:
        data = descargar(fuente, swf)
    except SwfNoEncontrado:
        return swf, None, "no existe en el CDN"
    except OSError as e:
        return swf, None, str(e)
    guardado = trabajo / (swf.replace("/", "__") + ".json")
    try:
        datos = json.loads(guardado.read_text(encoding="utf-8"))
        if datos["version"] == version_de(data):
            return swf, datos, ""
    except (OSError, ValueError, KeyError):
        pass
    try:
        clases = leer_clases(data)
        items = ffdec.analizar(data, items_del_swf(clases))
    except SwfInvalido as e:
        return swf, None, str(e)
    except Exception as e:  # FFDec puede fallar con un SWF raro: se sigue con los demás
        return swf, None, f"FFDec: {e}"
    usos = {destino: {pieza: sorted(partes) for pieza, partes in piezas.items()} for destino, piezas in usos_de_piezas(swf, items).items()}
    datos = {"version": version_de(data), "piezas": piezas_del_swf(clases), "usos": usos}
    guardado.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return swf, datos, ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hilos", type=int, default=4)
    parser.add_argument("--solo", help="SWF separados por coma (para probar)")
    parser.add_argument("--trabajo", type=Path, default=Path(tempfile.gettempdir()) / "mgitems-indice")
    args = parser.parse_args()

    nombres = args.solo.split(",") if args.solo else [s["swf"] for s in cargar_catalogo()]
    fuente, ffdec = FuenteCDN(), ItemsBaseFFDec()
    args.trabajo.mkdir(parents=True, exist_ok=True)
    analizados, errores = {}, []
    usos: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as hilos:
        for n, (swf, datos, error) in enumerate(hilos.map(lambda s: analizar(fuente, ffdec, args.trabajo, s), nombres), 1):
            if datos is None:
                errores.append(f"{swf}: {error}")
            else:
                analizados[swf] = datos
                for destino, piezas in datos["usos"].items():
                    for pieza, partes in piezas.items():
                        usos[destino][pieza] |= set(partes)
            print(f"\r{n}/{len(nombres)} {swf:40}", end="", flush=True)
    print()

    indice = {"swfs": {
        swf: {"version": datos["version"], "piezas": categorias(datos["piezas"], usos.get(swf, {}))}
        for swf, datos in sorted(analizados.items(), key=lambda s: s[0].lower())
    }}
    ARCHIVO_INDICE.write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    con_parte = sum(1 for d in indice["swfs"].values() for p in d["piezas"].values() if p)
    total = sum(len(d["piezas"]) for d in indice["swfs"].values())
    print(f"Índice: {len(indice['swfs'])} SWF, {total} Piezas ({con_parte} con Parte).")
    print(f"Con error: {len(errores)}")
    for e in errores:
        print("  " + e)


if __name__ == "__main__":
    main()

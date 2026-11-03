"""Arma la lista de objetos que sirven de fondo, la que viene incluida en el programa (pestaña Fondos).

Un fondo es un objeto cuyo dibujo tiene varios cuadros y se queda quieto en el primero (`stop()`), como
`socialNetBackgrounds.SocialNetBackgrounds` (23 fondos). Con el comportamiento `painting` del juego, cada cuadro
es un fondo para elegir (ver ADR 0007). Los que no frenan en el primer cuadro son animaciones: no sirven.

1. Cuenta los cuadros del dibujo de cada Item de los SWF del índice (del SWF, sin FFDec).
2. De los que tienen entre 2 y `MAXIMO` cuadros, que el juego no descarta y sirven de Item base, lee su código
   con FFDec y se queda con los que frenan en el primer cuadro y no tienen comportamiento propio (salvo
   `painting`, que ya es eso).

Escribe `src/mgitems/datos/fondos.json` (solo nombres y cantidades de cuadros, nada de arte del juego). Necesita
Java y FFDec en `vendor/`. Tarda unos minutos.

Uso:
    python scripts/armar_fondos.py [--hilos 6]
"""

import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from mgitems.categorias import ARCHIVO_INDICE  # noqa: E402
from mgitems.destinos import DESCARTADO  # noqa: E402
from mgitems.fondos import ARCHIVO_FONDOS, COMPORTAMIENTO, MAXIMO_CUADROS, frena_en_el_primer_cuadro  # noqa: E402
from mgitems.fuente import FuenteCDN  # noqa: E402
from mgitems.items import orden_natural  # noqa: E402
from mgitems.npcs import comportamiento_en_codigo  # noqa: E402
from mgitems.prendas import ItemsBaseFFDec, no_sirve_de_base  # noqa: E402
from mgitems.swf import cuadros_de_clases  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hilos", type=int, default=6)
    args = parser.parse_args()

    indice = json.loads(ARCHIVO_INDICE.read_text(encoding="utf-8"))["swfs"]
    fuente, ffdec = FuenteCDN(), ItemsBaseFFDec()

    def leer(swf):
        items = indice[swf]["items"]
        try:
            data = fuente.descargar(swf)
            cuadros = cuadros_de_clases(data)
            candidatos = [c for c, item in items.items()
                          if 2 <= cuadros.get(c, 1) <= MAXIMO_CUADROS and item.get("destino") != DESCARTADO
                          and not no_sirve_de_base(f"{swf}.{c}", item["tipo"])]
            if not candidatos:
                return swf, {}
            codigos = ffdec.fuentes(data, candidatos)
        except Exception as e:  # FFDec o la red pueden fallar con un SWF: se sigue con los demás
            print(f"\n{swf}: {e}", file=sys.stderr)
            return swf, {}
        return swf, {c: cuadros[c] for c in candidatos
                     if frena_en_el_primer_cuadro(codigos.get(c, ""))
                     and comportamiento_en_codigo(codigos.get(c, "")) in (None, COMPORTAMIENTO)}

    fondos: dict[str, int] = {}
    swfs = [s for s, datos in indice.items() if datos.get("items")]
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as ejecutor:
        for n, (swf, encontrados) in enumerate(ejecutor.map(leer, swfs), 1):
            fondos |= {f"{swf}.{c}": cuadros for c, cuadros in encontrados.items()}
            print(f"\r{n}/{len(swfs)} {swf:40} ({len(fondos)} fondos)", end="", flush=True)
    print()
    ARCHIVO_FONDOS.write_text(
        json.dumps({"fondos": dict(sorted(fondos.items(), key=lambda f: orden_natural(f[0])))}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{len(fondos)} fondos en {ARCHIVO_FONDOS.name}.")


if __name__ == "__main__":
    main()

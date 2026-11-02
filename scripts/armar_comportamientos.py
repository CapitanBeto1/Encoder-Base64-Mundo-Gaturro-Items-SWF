"""Arma la lista de comportamientos de NPC que viene incluida en el programa (pestañas Tiendas y Portales).

1. Lee el comportamiento (`behavior = "…"`) de cada objeto de la casa de los SWF del índice, con FFDec.
2. Le suma los comportamientos de NPC de las salas de `comportamientos_de_salas.txt`, que no están en ningún
   objeto.
3. Baja el guion `npc/<comportamiento>.npc` de cada uno y se queda con los que abren una tienda, llevan a otra
   sala o abren un minijuego (`npcs.clasificar`).
4. Le suma los nombres de las salas que publica el juego (`cfgs/map/games.json`, solo las de eventos).

Escribe `src/mgitems/datos/comportamientos.json` (solo nombres, nada de arte del juego). Necesita Java y FFDec
en `vendor/` (paso 1). Tarda unos minutos.

Uso:
    python scripts/armar_comportamientos.py [--hilos 6]
"""

import argparse
import concurrent.futures
import json
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from mgitems.categorias import ARCHIVO_INDICE, CASA  # noqa: E402
from mgitems.fuente import URL_JUEGO, FuenteCDN, SwfNoEncontrado  # noqa: E402
from mgitems.items import orden_natural  # noqa: E402
from mgitems.npcs import ARCHIVO_COMPORTAMIENTOS, TIPOS, clasificar, es_comportamiento_valido, leer_npc  # noqa: E402
from mgitems.prendas import ItemsBaseFFDec  # noqa: E402

DE_SALAS = Path(__file__).parent / "comportamientos_de_salas.txt"
_BEHAVIOR = re.compile(r'\bbehavior\s*=\s*"([^"]+)"')


def comportamientos_de_objetos(hilos: int) -> dict[str, list[str]]:
    """Comportamiento → los objetos de la casa que lo usan ("swf.clase")."""
    indice = json.loads(ARCHIVO_INDICE.read_text(encoding="utf-8"))["swfs"]
    con_casa = {swf: [c for c, i in datos["items"].items() if i.get("tipo") == CASA] for swf, datos in indice.items()}
    con_casa = {swf: clases for swf, clases in con_casa.items() if clases}
    fuente, ffdec = FuenteCDN(), ItemsBaseFFDec()

    def leer(swf):
        try:
            return swf, ffdec.fuentes(fuente.descargar(swf), con_casa[swf])
        except Exception as e:  # FFDec o la red pueden fallar con un SWF: se sigue con los demás
            print(f"\n{swf}: {e}", file=sys.stderr)
            return swf, {}

    objetos: dict[str, list[str]] = {}
    with concurrent.futures.ThreadPoolExecutor(hilos) as ejecutor:
        for n, (swf, fuentes) in enumerate(ejecutor.map(leer, con_casa), 1):
            for clase, codigo in fuentes.items():
                if clase in con_casa[swf] and (encontrado := _BEHAVIOR.search(codigo)):
                    objetos.setdefault(encontrado.group(1), []).append(f"{swf}.{clase}")
            print(f"\r1. objetos de la casa: {n}/{len(con_casa)} {swf:40}", end="", flush=True)
    print()
    return objetos


def nombres_de_salas() -> dict[str, str]:
    """Sala → nombre, de las salas de eventos que publica el juego."""
    pedido = urllib.request.Request(URL_JUEGO + "cfgs/map/games.json", headers={"User-Agent": "MGItems"})
    with urllib.request.urlopen(pedido, timeout=30) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8")).get("data", {})
    salas: dict[str, str] = {}
    for evento in datos.values():
        nombre = str(evento.get("name") or "").strip()
        if isinstance(evento.get("id"), int) and nombre and "..." not in nombre:
            salas.setdefault(str(evento["id"]), nombre)
    return salas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hilos", type=int, default=6)
    args = parser.parse_args()

    objetos = comportamientos_de_objetos(args.hilos)
    de_salas = [l.strip() for l in DE_SALAS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    nombres = sorted({n for n in [*objetos, *de_salas] if es_comportamiento_valido(n)}, key=orden_natural)

    fuente = FuenteCDN()

    def clasificar_uno(nombre):
        try:
            return nombre, clasificar(leer_npc(fuente.npc(nombre)))
        except SwfNoEncontrado:
            return nombre, None

    comportamientos = {}
    with concurrent.futures.ThreadPoolExecutor(args.hilos * 2) as ejecutor:
        for n, (nombre, info) in enumerate(ejecutor.map(clasificar_uno, nombres), 1):
            if info and info["tipo"] in TIPOS:
                comportamientos[nombre] = info | {"objetos": sorted(objetos.get(nombre, []), key=orden_natural)}
            print(f"\r2. guiones: {n}/{len(nombres)}", end="", flush=True)
    print()

    salas = nombres_de_salas()
    ARCHIVO_COMPORTAMIENTOS.write_text(
        json.dumps({"comportamientos": comportamientos, "salas": salas}, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    por_tipo = {t: sum(1 for c in comportamientos.values() if c["tipo"] == t) for t in TIPOS}
    print(f"{len(comportamientos)} comportamientos ({por_tipo}) de {len(nombres)}; {len(salas)} nombres de salas.")


if __name__ == "__main__":
    main()

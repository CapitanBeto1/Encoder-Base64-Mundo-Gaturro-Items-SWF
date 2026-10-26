"""Arma el índice de categorías de Piezas que viene incluido en el programa.

Para cada SWF del catálogo: lo descarga del CDN del juego, lee sus Items con FFDec y anota en qué
Parte(s) del cuerpo viste cada Pieza. Escribe `src/mgitems/datos/indice_piezas.json` (solo nombres
de clases, nada de arte del juego).

Cada Pieza se ubica con lo primero que corresponda:

1. Lo que la viste en el juego: una Prenda (`clothes`) o un Item de mochila (`adds`), de cualquier SWF.
2. Si el juego la usa para otra cosa (vehículo de un transporte, animación de un Item de mochila,
   decoración de la casa, ropa de la mascota), no es ropa: queda en "Otros".
3. Si otro SWF tiene una Pieza con el mismo nombre y el mismo dibujo, y esa Pieza tiene Parte, es
   la misma Pieza: toma esa Parte.
4. Si ningún Item la usa: dónde está dibujada respecto del punto donde el juego la pega al Gaturro
   (un sombrero queda arriba, un zapato abajo), más las palabras de su nombre, comparadas con las
   Piezas ya ubicadas. Solo se usa si la comparación está muy segura; si no, queda en "Otros".

Tarda: FFDec analiza cada SWF (unos segundos cada uno). Necesita Java y FFDec en `vendor/`, y
scikit-learn para el paso 4 (`pip install -e ".[indice]"`).

El análisis de cada SWF se guarda en una carpeta de trabajo (`--trabajo`, por defecto en la carpeta
temporal): si se corta (por ejemplo, sin internet), al volver a correrlo solo se analiza lo que falta
o lo que cambió en el CDN.

Uso:
    python scripts/armar_indice.py [--hilos 4] [--solo swf1,swf2] [--trabajo CARPETA]
"""

import argparse
import concurrent.futures
import json
import re
import sys
import tempfile
import time
from collections import Counter, defaultdict

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from mgitems.catalogo import cargar_catalogo  # noqa: E402
from mgitems.categorias import ARCHIVO_INDICE, PARTES_QUE_VISTEN, categorias, usos_de_piezas  # noqa: E402
from mgitems.fuente import FuenteCDN, SwfNoEncontrado  # noqa: E402
from mgitems.iconos import version_de  # noqa: E402
from mgitems.items import items_del_swf, piezas_del_swf  # noqa: E402
from mgitems.prendas import MOCHILA, ItemsBaseFFDec, leer_item_base  # noqa: E402
from mgitems.swf import SwfInvalido, leer_clases, limites_de_simbolos  # noqa: E402

# Sube cuando cambia lo que se guarda de cada SWF en la carpeta de trabajo.
FORMATO_TRABAJO = 3
# Seguridad mínima para ubicar una Pieza por su dibujo (paso 4). Con 0.7, al probarlo con las
# Piezas que el juego ya ubica, acertó el 99 %.
SEGURIDAD_MINIMA = 0.7
# Items cuya Pieza `<Item>_on` no es ropa del Gaturro.
PADRES_QUE_NO_VISTEN = {"HouseMamboAsset": "casa", "HouseDecorationMamboAsset": "casa"}
_CLASE = re.compile(r"\bclass\s+(\w+)\s+extends\s+(\w+)")
_VEHICULO = re.compile(r'\bvehicle\s*=\s*"([^"]+)"')
_PIEZA_EN_MAPA = re.compile(r'"\w+"\s*:\s*"([^"]+_on)"')


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


def no_ropa(swf: str, fuentes: dict[str, str]) -> dict[str, dict[str, str]]:
    """SWF → Pieza → para qué la usa el juego, de las Piezas que los Items de `swf` usan sin vestir."""
    usos: dict[str, dict[str, str]] = defaultdict(dict)

    def anotar(valor: str, motivo: str) -> None:
        partes = valor.split(".")  # "pieza", "swf.pieza" o "acción.swf.pieza"
        usos[partes[-2] if len(partes) > 1 else swf][partes[-1]] = motivo

    for fuente in fuentes.values():
        clase = _CLASE.search(fuente)
        if not clase:
            continue
        nombre, padre = clase.groups()
        if padre in PADRES_QUE_NO_VISTEN:
            anotar(f"{nombre}_on", PADRES_QUE_NO_VISTEN[padre])
        elif padre == "PetClothMamboAsset":  # su `clothes` viste a la mascota
            for pieza in _PIEZA_EN_MAPA.findall(fuente):
                anotar(pieza, "mascota")
        elif padre == "TransportMamboAsset":
            for vehiculo in _VEHICULO.findall(fuente):
                anotar(vehiculo, "transporte")
        elif (item := leer_item_base(fuente)) and item.tipo == MOCHILA:
            for parte, valor in item.partes.items():
                if parte not in PARTES_QUE_VISTEN and valor.endswith("_on"):
                    anotar(valor, "acción")
    return usos


def analizar(fuente: FuenteCDN, ffdec: ItemsBaseFFDec, trabajo: Path, swf: str) -> tuple[str, dict | None, str]:
    """(swf, {"version", "piezas", "usos", "no_ropa", "limites"}, error). Reusa el análisis guardado si
    el SWF no cambió."""
    try:
        data = descargar(fuente, swf)
    except SwfNoEncontrado:
        return swf, None, "no existe en el CDN"
    except OSError as e:
        return swf, None, str(e)
    guardado = trabajo / (swf.replace("/", "__") + ".json")
    try:
        datos = json.loads(guardado.read_text(encoding="utf-8"))
        if datos["version"] == version_de(data) and datos.get("formato") == FORMATO_TRABAJO:
            return swf, datos, ""
    except (OSError, ValueError, KeyError):
        pass
    try:
        clases = leer_clases(data)
        items = items_del_swf(clases)
        fuentes = ffdec.fuentes(data, items)
        piezas = piezas_del_swf(clases)
        limites = limites_de_simbolos(data)
    except SwfInvalido as e:
        return swf, None, str(e)
    except Exception as e:  # FFDec puede fallar con un SWF raro: se sigue con los demás
        return swf, None, f"FFDec: {e}"
    items_base = {i.clase: i for i in map(leer_item_base, fuentes.values()) if i and i.clase in items}
    usos = {destino: {pieza: sorted(partes) for pieza, partes in piezas.items()}
            for destino, piezas in usos_de_piezas(swf, items_base).items()}
    datos = {
        "formato": FORMATO_TRABAJO, "version": version_de(data), "piezas": piezas, "usos": usos,
        "no_ropa": no_ropa(swf, fuentes), "limites": {p: limites[p] for p in piezas if p in limites},
    }
    guardado.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return swf, datos, ""


def palabras(pieza: str) -> str:
    """`remeraRugbyPumas_brazo_on` → "remera rugby pumas brazo"."""
    return " ".join(p.lower() for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", pieza.removesuffix("_on")))


def ubicar_por_dibujo(partes: dict, sin_ropa: set, limites: dict) -> dict[tuple[str, str], tuple[str, float]]:
    """(SWF, Pieza) → (Parte, seguridad) de las Piezas sin Parte que no se sabe si son ropa (paso 4).

    Aprende de las Piezas que el juego ubica en una sola Parte y de las que usa para otra cosa ("otros").
    """
    from scipy.sparse import csr_matrix, hstack
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import CountVectorizer

    def numeros(claves):
        filas = []
        for clave in claves:
            x0, y0, x1, y1 = limites[clave]
            filas.append([x0, y0, x1, y1, x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2])
        return csr_matrix(filas)

    ejemplos = [(clave, ps[0]) for clave, ps in partes.items() if len(ps) == 1 and clave in limites]
    ejemplos += [(clave, "otros") for clave in sin_ropa if clave in limites]
    a_ubicar = [clave for clave, ps in partes.items() if not ps and clave not in sin_ropa and clave in limites]
    if not ejemplos or not a_ubicar:
        return {}
    vocabulario = CountVectorizer(token_pattern=r"\S+", binary=True)
    x = hstack([numeros(c for c, _ in ejemplos), vocabulario.fit_transform(palabras(p) for (_, p), _ in ejemplos)]).tocsr()
    modelo = RandomForestClassifier(500, n_jobs=-1, random_state=0).fit(x, [parte for _, parte in ejemplos])
    x = hstack([numeros(a_ubicar), vocabulario.transform(palabras(p) for _, p in a_ubicar)]).tocsr()
    ubicadas = {}
    for clave, probabilidades in zip(a_ubicar, modelo.predict_proba(x)):
        mejor = probabilidades.argmax()
        ubicadas[clave] = (modelo.classes_[mejor], float(probabilidades[mejor]))
    return ubicadas


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
    sin_ropa = set()
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as hilos:
        for n, (swf, datos, error) in enumerate(hilos.map(lambda s: analizar(fuente, ffdec, args.trabajo, s), nombres), 1):
            if datos is None:
                errores.append(f"{swf}: {error}")
            else:
                analizados[swf] = datos
                for destino, piezas in datos["usos"].items():
                    for pieza, partes in piezas.items():
                        usos[destino][pieza] |= set(partes)
                sin_ropa |= {(destino, pieza) for destino, piezas in datos["no_ropa"].items() for pieza in piezas}
            print(f"\r{n}/{len(nombres)} {swf:40}", end="", flush=True)
    print()

    # 1. Lo que el juego viste.
    partes = {(swf, pieza): ps for swf, datos in analizados.items()
              for pieza, ps in categorias(datos["piezas"], usos.get(swf, {})).items()}
    limites = {(swf, pieza): tuple(r) for swf, datos in analizados.items() for pieza, r in datos["limites"].items()}
    sin_ropa = {clave for clave in sin_ropa if clave in partes and not partes[clave]}  # 2. Lo que no es ropa.
    motivos = Counter({"vestida por un Item": sum(1 for ps in partes.values() if ps), "usada para otra cosa": len(sin_ropa)})

    # 3. La misma Pieza (mismo nombre y mismo dibujo) en otro SWF.
    con_parte = defaultdict(list)
    for (swf, pieza), ps in partes.items():
        if ps:
            con_parte[pieza].append((swf, ps))
    for (swf, pieza), ps in partes.items():
        if ps or (swf, pieza) in sin_ropa or (swf, pieza) not in limites:
            continue
        iguales = [ps2 for swf2, ps2 in con_parte.get(pieza, []) if limites.get((swf2, pieza)) == limites[(swf, pieza)]]
        if iguales:
            partes[(swf, pieza)] = iguales[0]
            motivos["misma Pieza en otro SWF"] += 1

    # 4. Dónde está dibujada.
    for clave, (parte, seguridad) in ubicar_por_dibujo(partes, sin_ropa, limites).items():
        if parte != "otros" and seguridad >= SEGURIDAD_MINIMA:
            partes[clave] = [parte]
            motivos["por su dibujo"] += 1
        else:
            motivos["sin pista segura"] += 1

    indice = {"swfs": {
        swf: {"version": datos["version"], "piezas": {pieza: partes[(swf, pieza)] for pieza in datos["piezas"]}}
        for swf, datos in sorted(analizados.items(), key=lambda s: s[0].lower())
    }}
    ARCHIVO_INDICE.write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    con = sum(1 for ps in partes.values() if ps)
    print(f"Índice: {len(indice['swfs'])} SWF, {len(partes)} Piezas ({con} con Parte).")
    for motivo, cantidad in motivos.items():
        print(f"  {motivo}: {cantidad}")
    print(f"Con error: {len(errores)}")
    for e in errores:
        print("  " + e)


if __name__ == "__main__":
    main()

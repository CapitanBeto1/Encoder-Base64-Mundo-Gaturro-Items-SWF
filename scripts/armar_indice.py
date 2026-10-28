"""Arma el índice de categorías de Piezas y tipos de Items que viene incluido en el programa.

Para cada SWF del catálogo: lo descarga del CDN del juego, lee sus Items con FFDec y anota de qué
tipo es cada Item y en qué Parte(s) del cuerpo viste cada Pieza. Escribe
`src/mgitems/datos/indice_piezas.json` (solo nombres de clases, nada de arte del juego).

Cada Pieza se ubica con lo primero que corresponda:

1. Lo que la viste en el juego: una Prenda (`clothes`) o un Item de mochila (`adds`), de cualquier SWF.
2. Si el juego la usa para otra cosa (vehículo de un transporte, animación de un Item de mochila,
   decoración de la casa, ropa de la mascota), no es ropa: queda en "Otros" con ese uso. También la
   ropa de mascota de otro SWF, que empieza como la de la mascota (`mono_`, `dragon_`).
3. Si otro SWF tiene una Pieza con el mismo nombre y el mismo dibujo, y esa Pieza tiene Parte, es
   la misma Pieza: toma esa Parte.
4. Si ningún Item la usa: dónde está dibujada respecto del punto donde el juego la pega al Gaturro
   (un sombrero queda arriba, un zapato abajo), más las palabras de su nombre, comparadas con las
   Piezas ya ubicadas, si la comparación está muy segura.
5. Las que quedan (dibujadas para otro cuerpo, como los trajes de los duendes): la Parte más
   probable entre la que sugiere su dibujo y la que sugiere su nombre leído por partes (`zapatos`
   como `zapato`, `torsoDuende` con `torso`). Queda en "Otros" solo si el dibujo y el nombre, cada
   uno por su lado, dicen que no es ropa...
6. ...salvo que la primera palabra de su nombre casi siempre vaya en la misma Parte en el juego
   (`remeraGranjero` → Torso, `remeraGranjero_brazo` → Brazos).

Tarda: FFDec analiza cada SWF (unos segundos cada uno). Necesita Java y FFDec en `vendor/`, y
scikit-learn para los pasos 4 y 5 (`pip install -e ".[indice]"`).

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
from mgitems.categorias import (  # noqa: E402
    ARCHIVO_INDICE, MASCOTA, categorias, donde_se_ven, otros_usos, tipos_de_items, usos_de_piezas,
)
from mgitems.fuente import FuenteCDN, SwfNoEncontrado  # noqa: E402
from mgitems.iconos import version_de  # noqa: E402
from mgitems.items import items_del_swf, piezas_del_swf  # noqa: E402
from mgitems.destinos import PARTES_DEL_GATURRO  # noqa: E402
from mgitems.prendas import PRENDA, ItemsBaseFFDec, leer_item_base  # noqa: E402
from mgitems.swf import SwfInvalido, leer_clases, limites_de_simbolos  # noqa: E402

# Sube cuando cambia lo que se guarda de cada SWF en la carpeta de trabajo.
FORMATO_TRABAJO = 13
# Seguridad mínima para ubicar una Pieza en el paso 4. Con 0.7, al probarlo con las Piezas que el
# juego ya ubica, acertó el 98-99 %.
SEGURIDAD_MINIMA = 0.7
NO_ES_ROPA = "otros"


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
    """(swf, {"version", "piezas", "usos", "otros_usos", "limites", "items"}, error). Reusa el análisis guardado
    si el SWF no cambió."""
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
        fuentes = ffdec.fuentes(data, items + piezas_del_swf(clases))
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
        "otros_usos": otros_usos(swf, fuentes), "limites": {p: limites[p] for p in piezas if p in limites},
        "items": {clase: tipo for clase, tipo in tipos_de_items(swf, fuentes).items() if clase in items},
        "se_ve": donde_se_ven(swf, piezas, fuentes, limites),
    }
    guardado.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return swf, datos, ""


def palabras(pieza: str) -> str:
    """`remeraRugbyPumas_brazo_on` → "remera rugby pumas brazo"."""
    return " ".join(p.lower() for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", pieza.removesuffix("_on")))


def primera_palabra(pieza: str) -> tuple[str, bool] | None:
    """`remeraGranjero_brazo_on` → ("remera", True): la primera palabra y si es una manga."""
    palabra = re.match(r"[a-z]+", pieza)
    return (palabra.group(0), "_brazo" in pieza) if palabra else None


def partes_por_primera_palabra(partes: dict, minimo: int = 10, proporcion: float = 0.8) -> dict:
    """Primera palabra → Parte, de las palabras que en el juego casi siempre van en la misma Parte
    (`pantalon` → leg, `remera` con `_brazo` → arm)."""
    cuentas = defaultdict(Counter)
    for (_, pieza), ps in partes.items():
        if len(ps) == 1:
            cuentas[primera_palabra(pieza)][ps[0]] += 1
    reglas = {}
    for palabra, cuenta in cuentas.items():
        parte, veces = cuenta.most_common(1)[0]
        if palabra and veces >= minimo and veces / cuenta.total() >= proporcion:
            reglas[palabra] = parte
    return reglas


def nombre_sin_numeros(pieza: str) -> str:
    return re.sub(r"\d+", "", pieza.removesuffix("_on")).lower()


def ubicar_por_dibujo(partes: dict, usos: dict, limites: dict) -> dict[tuple[str, str], str]:
    """(SWF, Pieza) → Parte (o NO_ES_ROPA) de las Piezas sin Parte ni uso (pasos 4 y 5).

    Aprende de las Piezas que el juego ubica en una sola Parte y de las que usa para otra cosa.
    """
    from scipy.sparse import csr_matrix, hstack
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    def dibujo(claves):
        filas = []
        for clave in claves:
            x0, y0, x1, y1 = limites[clave]
            filas.append([x0, y0, x1, y1, x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2])
        return csr_matrix(filas)

    ejemplos = [(clave, ps[0]) for clave, ps in partes.items() if len(ps) == 1 and clave in limites]
    ejemplos += [(clave, NO_ES_ROPA) for clave in usos if clave in limites]
    a_ubicar = [clave for clave, ps in partes.items() if not ps and clave not in usos and clave in limites]
    if not ejemplos or not a_ubicar:
        return {}
    claves, etiquetas = [c for c, _ in ejemplos], [e for _, e in ejemplos]

    # Paso 4: dibujo + palabras del nombre, solo si es muy seguro.
    vocabulario = CountVectorizer(token_pattern=r"\S+", binary=True)
    x = hstack([dibujo(claves), vocabulario.fit_transform(palabras(p) for _, p in claves)]).tocsr()
    junto = RandomForestClassifier(500, n_jobs=-1, random_state=0).fit(x, etiquetas)
    probabilidades = junto.predict_proba(hstack([dibujo(a_ubicar), vocabulario.transform(palabras(p) for _, p in a_ubicar)]).tocsr())

    # Paso 5: el dibujo y el nombre por separado, promediados (sirve cuando el dibujo es de otro cuerpo).
    solo_dibujo = RandomForestClassifier(500, n_jobs=-1, random_state=0).fit(dibujo(claves), etiquetas)
    trozos = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
    solo_nombre = LogisticRegression(max_iter=3000, C=5).fit(trozos.fit_transform(nombre_sin_numeros(p) for _, p in claves), etiquetas)
    promedio = (solo_dibujo.predict_proba(dibujo(a_ubicar))
                + solo_nombre.predict_proba(trozos.transform(nombre_sin_numeros(p) for _, p in a_ubicar))) / 2

    # No es ropa solo si el dibujo y el nombre, cada uno por su lado, dicen que no lo es.
    clases = list(solo_dibujo.classes_)
    no_es_ropa = clases.index(NO_ES_ROPA)
    dice_dibujo = solo_dibujo.predict_proba(dibujo(a_ubicar)).argmax(1) == no_es_ropa
    dice_nombre = solo_nombre.predict_proba(trozos.transform(nombre_sin_numeros(p) for _, p in a_ubicar)).argmax(1) == no_es_ropa
    ubicadas = {}
    for i, (clave, segura, probable) in enumerate(zip(a_ubicar, probabilidades, promedio)):
        mejor = segura.argmax()
        if segura[mejor] >= SEGURIDAD_MINIMA:
            ubicadas[clave] = junto.classes_[mejor]
        elif dice_dibujo[i] and dice_nombre[i]:
            ubicadas[clave] = NO_ES_ROPA
        else:
            probable[no_es_ropa] = -1
            ubicadas[clave] = clases[probable.argmax()]
    return ubicadas


def completar_prendas_rotas(analizados: dict, partes: dict, por_palabra: dict) -> None:
    """A las Prendas que no declaran Piezas, o solo en Partes que el Gaturro no tiene, les anota
    "parecido": las Partes de su Pieza `<Item>_on`, de una Prenda que funciona y se llama igual en
    otro SWF, o de la primera palabra de su nombre, para ubicarlas en su categoría. Si hay una que funciona, la sugiere en el motivo."""
    que_funcionan = defaultdict(list)
    for swf, datos in analizados.items():
        for clase, item in datos["items"].items():
            if item["tipo"] == PRENDA and not item.get("motivo") and set(item.get("partes", [])) & PARTES_DEL_GATURRO:
                que_funcionan[clase].append((swf, item["partes"]))
    for swf, datos in analizados.items():
        for clase, item in datos["items"].items():
            if item["tipo"] != PRENDA or set(item.get("partes", [])) & PARTES_DEL_GATURRO:
                continue
            otra = next(iter(que_funcionan.get(clase, [])), None)
            de_la_pieza = [p for p in partes.get((swf, f"{clase}_on"), []) if p in PARTES_DEL_GATURRO]
            por_nombre = [p for p in [por_palabra.get(primera_palabra(clase))] if p in PARTES_DEL_GATURRO]
            parecido = de_la_pieza or (otra[1] if otra else []) or por_nombre
            if parecido:
                item["parecido"] = parecido
            if otra and item.get("motivo"):
                item["motivo"] += f" (la que funciona: {otra[0]}.{clase})"


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
    otros: dict[tuple[str, str], str] = {}
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as hilos:
        for n, (swf, datos, error) in enumerate(hilos.map(lambda s: analizar(fuente, ffdec, args.trabajo, s), nombres), 1):
            if datos is None:
                errores.append(f"{swf}: {error}")
            else:
                analizados[swf] = datos
                for destino, piezas in datos["usos"].items():
                    for pieza, partes in piezas.items():
                        usos[destino][pieza] |= set(partes)
                for destino, piezas in datos["otros_usos"].items():
                    for pieza, uso in piezas.items():
                        otros[(destino, pieza)] = uso
            print(f"\r{n}/{len(nombres)} {swf:40}", end="", flush=True)
    print()

    # 1. Lo que el juego viste.
    partes = {(swf, pieza): ps for swf, datos in analizados.items()
              for pieza, ps in categorias(datos["piezas"], usos.get(swf, {})).items()}
    por_palabra = partes_por_primera_palabra(partes)
    limites = {(swf, pieza): tuple(r) for swf, datos in analizados.items() for pieza, r in datos["limites"].items()}
    otros = {clave: uso for clave, uso in otros.items() if clave in partes and not partes[clave]}  # 2. Lo que no es ropa.
    motivos = Counter({"vestida por un Item": sum(1 for ps in partes.values() if ps), "usada para otra cosa": len(otros)})

    # 2b. Ropa de mascota de otro SWF: empieza como la de la mascota (`mono_`, `dragon_`).
    def prefijo(pieza):
        return pieza.split("_", 1)[0] if "_" in pieza.removesuffix("_on") else None
    de_ropa = {prefijo(pieza) for (_, pieza), ps in partes.items() if ps}
    de_mascota = {prefijo(pieza) for (_, pieza), uso in otros.items() if uso == MASCOTA} - de_ropa - {None}
    for clave, ps in partes.items():
        if not ps and clave not in otros and prefijo(clave[1]) in de_mascota:
            otros[clave] = MASCOTA
            motivos["ropa de mascota por su nombre"] += 1

    # 3. La misma Pieza (mismo nombre y mismo dibujo) en otro SWF.
    con_parte = defaultdict(list)
    for (swf, pieza), ps in partes.items():
        if ps:
            con_parte[pieza].append((swf, ps))
    for (swf, pieza), ps in partes.items():
        if ps or (swf, pieza) in otros or (swf, pieza) not in limites:
            continue
        iguales = [ps2 for swf2, ps2 in con_parte.get(pieza, []) if limites.get((swf2, pieza)) == limites[(swf, pieza)]]
        if iguales:
            partes[(swf, pieza)] = iguales[0]
            motivos["misma Pieza en otro SWF"] += 1

    # 4 y 5. Dónde está dibujada y cómo se llama.
    for clave, parte in ubicar_por_dibujo(partes, otros, limites).items():
        if parte != NO_ES_ROPA:
            partes[clave] = [parte]
            motivos["por su dibujo y su nombre"] += 1

    # 6. Lo que sigue sin Parte ni uso (no parece ropa, o no tiene dibujo): `remeraGranjero` es una remera.
    for clave, ps in partes.items():
        if ps or clave in otros:
            continue
        parte = por_palabra.get(primera_palabra(clave[1]))
        if parte and parte != NO_ES_ROPA:
            partes[clave] = [parte]
            motivos["por la primera palabra del nombre"] += 1
        else:
            motivos["no parece ropa"] += 1

    completar_prendas_rotas(analizados, partes, por_palabra)

    indice = {"swfs": {
        swf: {
            "version": datos["version"],
            "piezas": {pieza: partes[(swf, pieza)] for pieza in datos["piezas"]},
            "otros_usos": {pieza: otros[(swf, pieza)] for pieza in datos["piezas"] if (swf, pieza) in otros},
            "items": datos["items"],
            "se_ve": datos["se_ve"],
        }
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

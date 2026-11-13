"""Sintaxis extendida de una Pieza: colores por forma y ajuste de posición, rotación y escala.

El cliente del juego lee el valor de una Parte del cuerpo como `pack.Clase_on[,c0,c1,…][//x,y,rot,escala]`
(`GaturroColorManager.customColorStr`, `ClothCustomUtil.applyTransform`):

- cada `c_i` pinta la forma `i` de la Pieza (las formas van ordenadas de menor a mayor tamaño): un entero RGB,
  `QUITAR` (saca esa forma) o `DEFECTO` (la deja como está; el editor del juego escribe -1 en las animadas); opcional
  `;a` con `a` de 0 a 10 = opacidad `a/10` (en una Pieza de una sola forma, la «saturación» del editor).
  Las formas sin color van quedando como están, así que solo hace falta nombrarlas hasta la última que se toca.
- el ajuste `x,y,rot,escala` mueve, rota y escala la Pieza entera. El juego solo lo aplica a las Partes
  "rotables" (o a administradores) y con topes; `escala` va de 5 a 10 y vale `escala/10` (10 = tamaño normal).

Acá se valida la personalización de un Look y se arma ese valor: lo usan la vista previa, la entrega (en el SWF
trucado o en los atributos de `inventory.addOptions`) y los guardados. El propio juego guarda así su «Personalizar
prenda» (`ClothEditorModal`: `wear_<parte> = "<pieza>,…//x,y,rot,escala"`), y al ponerse la Prenda solo le agrega el
SWF a la Pieza si no tiene punto (`ClothInventorySceneObject`), así que la cola llega intacta.
"""

import re

from mgitems.items import es_ruta_valida

QUITAR, DEFECTO = -3, -2
# Topes del ajuste para un jugador normal (ClothCustomUtil.TRANSFORM_*).
LIMITES_AJUSTE = {"x": (-15, 15), "y": (-15, 15), "rot": (-180, 180), "escala": (5, 10)}
AJUSTE_DEFECTO = {"x": 0, "y": 0, "rot": 0, "escala": 10}
# Partes donde el juego aplica el ajuste a un jugador normal (prefijo; ClothCustomUtil.ROTATABLE_CATEGORIES).
PARTES_ROTABLES = ("hairs", "hats", "accesories", "mouths", "neck", "cloth", "leg", "grip", "glove")
# Donde el juego no la aplica: el efecto de cabeza se busca por el nombre exacto de la Pieza
# (`GaturroEffectsManager.applyHead`) y el transporte no pinta formas (`Gaturro.add`). La acción no es una Parte.
PARTES_SIN_PERSONALIZAR = frozenset({"effect", "transport", "action"})
MAXIMO_FORMAS = 999  # el editor del juego escribe todas las formas de la Pieza, aunque no las toque


class PersonalizacionInvalida(ValueError):
    """La personalización no tiene la forma esperada."""

_TOKEN_COLOR = re.compile(r"^-?\d+(?:;\d+)?$")
_TOKEN_AJUSTE = re.compile(r"^-?\d+$")


def es_parte_rotable(parte: str) -> bool:
    return any(parte == c or parte.startswith(c) for c in PARTES_ROTABLES)


def es_personalizable(parte: str) -> bool:
    return parte not in PARTES_SIN_PERSONALIZAR


def _entero(valor, minimo: int, maximo: int, que: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
        raise PersonalizacionInvalida(f"{que} no es válido: {valor!r}")
    return valor


def _normalizar_forma(forma) -> dict:
    if not isinstance(forma, dict):
        raise PersonalizacionInvalida("Una forma no tiene la forma esperada.")
    if forma.get("quitar"):
        return {"quitar": True}
    if forma.get("color") is None:
        return {"color": None}
    normal = {"color": _entero(forma["color"], 0, 0xFFFFFF, "El color")}
    if forma.get("opacidad") is not None:
        opacidad = _entero(forma["opacidad"], 0, 10, "La opacidad")
        if opacidad < 10:
            normal["opacidad"] = opacidad
    return normal


def normalizar(personalizacion, partes: dict) -> dict[str, dict]:
    """La personalización validada, por Parte: `{"colores": [forma…], "ajuste": {x, y, rot, escala}}`, solo con lo
    que cambia algo (sin las formas por defecto del final, sin el ajuste si no mueve nada o la Parte no es rotable).

    Se descarta la de Partes sin Pieza en `partes` o que no se pueden personalizar (queda de una Pieza que ya no
    está). Lanza `PersonalizacionInvalida` si no tiene la forma esperada.
    """
    if not personalizacion:
        return {}
    if not isinstance(personalizacion, dict):
        raise PersonalizacionInvalida("La personalización no tiene la forma esperada.")
    resultado = {}
    for parte, datos in personalizacion.items():
        if parte not in partes or not es_personalizable(parte) or not datos:
            continue
        if not isinstance(datos, dict):
            raise PersonalizacionInvalida(f"La personalización de {parte} no tiene la forma esperada.")
        colores = datos.get("colores") or []
        if not isinstance(colores, list) or len(colores) > MAXIMO_FORMAS:
            raise PersonalizacionInvalida(f"Los colores de {parte} no tienen la forma esperada.")
        colores = [_normalizar_forma(f) for f in colores]
        while colores and colores[-1] == {"color": None}:
            colores.pop()
        entrada = {"colores": colores} if colores else {}
        ajuste = datos.get("ajuste")
        if ajuste is not None:
            if not isinstance(ajuste, dict):
                raise PersonalizacionInvalida(f"El ajuste de {parte} no tiene la forma esperada.")
            ajuste = {k: _entero(ajuste.get(k, AJUSTE_DEFECTO[k]), -999, 999, f"El ajuste ({k})") for k in AJUSTE_DEFECTO}
            ajuste = {k: _clamp(v, *LIMITES_AJUSTE[k]) for k, v in ajuste.items()}
            if es_parte_rotable(parte) and ajuste != AJUSTE_DEFECTO:
                entrada["ajuste"] = ajuste
        if entrada:
            resultado[parte] = entrada
    return resultado


def con_personalizacion(partes: dict[str, str], personalizacion: dict[str, dict]) -> dict[str, str]:
    """`partes` con el valor de cada Pieza ya personalizado (`personalizacion` ya normalizada)."""
    return {parte: componer(ruta, personalizacion[parte].get("colores"), personalizacion[parte].get("ajuste"))
            if parte in personalizacion and isinstance(ruta, str) else ruta for parte, ruta in partes.items()}


def _clamp(valor: int, minimo: int, maximo: int) -> int:
    return max(minimo, min(maximo, valor))


def _token_color(spec: dict) -> str:
    """El token de una forma: `spec` = {color: int|None, quitar: bool, opacidad: int(0..10)|None}."""
    if spec.get("quitar"):
        return str(QUITAR)
    color = spec.get("color")
    if color is None:
        return str(DEFECTO)
    token = str(int(color) & 0xFFFFFF)
    opacidad = spec.get("opacidad")
    if opacidad is not None and 0 <= opacidad < 10:
        token += f";{opacidad}"
    return token


def componer(ruta: str, colores: list[dict] | None = None, ajuste: dict | None = None) -> str:
    """El valor extendido de la Pieza `ruta` con `colores` por forma y `ajuste` (x, y, rot, escala).

    Omite lo que esté en su valor por defecto: las formas sin tocar del final, y el ajuste si no mueve nada.
    """
    valor = ruta
    tokens = [_token_color(c) for c in (colores or [])]
    while tokens and tokens[-1] == str(DEFECTO):  # el cliente deja igual las formas que no se nombran
        tokens.pop()
    if tokens:
        valor += "," + ",".join(tokens)
    if ajuste:
        a = {k: _clamp(int(ajuste.get(k, AJUSTE_DEFECTO[k])), *LIMITES_AJUSTE[k]) for k in AJUSTE_DEFECTO}
        if a != AJUSTE_DEFECTO:
            valor += f"//{a['x']},{a['y']},{a['rot']},{a['escala']}"
    return valor


def separar(valor: str) -> tuple[str, list[dict], dict]:
    """(ruta limpia, colores por forma, ajuste) de un valor extendido. Lo que falte vuelve vacío/por defecto."""
    resto, _, cola_ajuste = valor.partition("//")
    ruta, _, cola_colores = resto.partition(",")
    colores = [_leer_token_color(t) for t in cola_colores.split(",")] if cola_colores else []
    ajuste = dict(AJUSTE_DEFECTO)
    if cola_ajuste:
        partes = cola_ajuste.split(",")
        for clave, texto in zip(("x", "y", "rot", "escala"), partes):
            if _TOKEN_AJUSTE.match(texto):
                ajuste[clave] = _clamp(int(texto), *LIMITES_AJUSTE[clave])
    return ruta, colores, ajuste


def _leer_token_color(token: str) -> dict:
    cabeza, _, opacidad = token.partition(";")
    numero = int(cabeza) if _TOKEN_AJUSTE.match(cabeza) else DEFECTO
    if numero == QUITAR:
        return {"quitar": True}
    if numero < 0:
        return {"color": None}
    return {"color": numero & 0xFFFFFF, "opacidad": int(opacidad) if opacidad.isdigit() else None}


def ruta_limpia(valor: str) -> str:
    """Solo la Pieza (`pack.Clase_on`), sin colores ni ajuste."""
    return valor.split("//", 1)[0].split(",", 1)[0]


def separar_cola(valor: str) -> tuple[str, str]:
    """(la Pieza, lo que le sigue: `,colores//ajuste`, o vacío)."""
    limpio = ruta_limpia(valor)
    return limpio, valor[len(limpio):]


def es_cola_valida(cola: str) -> bool:
    """Si `cola` (lo que sigue a la Pieza) son colores y ajuste bien formados, o nada."""
    return cola == "" or es_valor_valido("a.b" + cola)


def es_valor_valido(valor: str) -> bool:
    """Si `valor` es una Pieza válida, con o sin colores y ajuste bien formados."""
    if not isinstance(valor, str):
        return False
    resto, sep, cola_ajuste = valor.partition("//")
    ruta, _, cola_colores = resto.partition(",")
    if not es_ruta_valida(ruta):
        return False
    if cola_colores and not all(_TOKEN_COLOR.match(t) for t in cola_colores.split(",")):
        return False
    if sep and (not cola_ajuste or not all(_TOKEN_AJUSTE.match(t) for t in cola_ajuste.split(","))):
        return False
    return True


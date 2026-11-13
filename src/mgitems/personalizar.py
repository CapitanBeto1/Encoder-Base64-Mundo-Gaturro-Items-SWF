"""Sintaxis extendida de una Pieza: colores por forma y ajuste de posición, rotación y escala.

El cliente del juego lee el valor de una Parte del cuerpo como `pack.Clase_on[,c0,c1,…][//x,y,rot,escala]`
(`GaturroColorManager.customColorStr`, `ClothCustomUtil.applyTransform`):

- cada `c_i` pinta la forma `i` de la Pieza (las formas van ordenadas de menor a mayor tamaño): un entero RGB,
  `QUITAR` (saca esa forma) o `DEFECTO` (la deja como está); opcional `;a` con `a` de 1 a 10 = opacidad `a/10`.
  Las formas sin color van quedando como están, así que solo hace falta nombrarlas hasta la última que se toca.
- el ajuste `x,y,rot,escala` mueve, rota y escala la Pieza entera. El juego solo lo aplica a las Partes
  "rotables" (o a administradores) y con topes; `escala` va de 5 a 10 y vale `escala/10` (10 = tamaño normal).

Acá se arma y se lee ese valor; dibujarlo y entregarlo es de quien use estas funciones.
"""

import re

QUITAR, DEFECTO = -3, -2
# Topes del ajuste para un jugador normal (ClothCustomUtil.TRANSFORM_*).
LIMITES_AJUSTE = {"x": (-15, 15), "y": (-15, 15), "rot": (-180, 180), "escala": (5, 10)}
AJUSTE_DEFECTO = {"x": 0, "y": 0, "rot": 0, "escala": 10}
# Partes donde el juego aplica el ajuste a un jugador normal (prefijo; ClothCustomUtil.ROTATABLE_CATEGORIES).
PARTES_ROTABLES = ("hairs", "hats", "accesories", "mouths", "neck", "cloth", "leg", "grip", "glove")

_RUTA = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*\.[A-Za-z_][A-Za-z0-9_]*$")
_TOKEN_COLOR = re.compile(r"^-?\d+(?:;\d+)?$")
_TOKEN_AJUSTE = re.compile(r"^-?\d+$")


def es_parte_rotable(parte: str) -> bool:
    return any(parte == c or parte.startswith(c) for c in PARTES_ROTABLES)


def _clamp(valor: int, minimo: int, maximo: int) -> int:
    return max(minimo, min(maximo, valor))


def _token_color(spec: dict) -> str:
    """El token de una forma: `spec` = {color: int|None, quitar: bool, opacidad: int(1..10)|None}."""
    if spec.get("quitar"):
        return str(QUITAR)
    color = spec.get("color")
    if color is None:
        return str(DEFECTO)
    token = str(int(color) & 0xFFFFFF)
    opacidad = spec.get("opacidad")
    if opacidad is not None and 1 <= opacidad < 10:
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


def es_valor_valido(valor: str) -> bool:
    """Si `valor` es una Pieza válida, con o sin colores y ajuste bien formados."""
    if not isinstance(valor, str):
        return False
    resto, sep, cola_ajuste = valor.partition("//")
    ruta, _, cola_colores = resto.partition(",")
    if not _RUTA.match(ruta):
        return False
    if cola_colores and not all(_TOKEN_COLOR.match(t) for t in cola_colores.split(",")):
        return False
    if sep and (not cola_ajuste or not all(_TOKEN_AJUSTE.match(t) for t in cola_ajuste.split(","))):
        return False
    return True

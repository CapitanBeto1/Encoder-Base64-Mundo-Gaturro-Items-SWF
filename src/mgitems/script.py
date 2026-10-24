"""Scripts NPC y Encodes.

Un Script es el programa en el lenguaje de los NPC del juego; un Encode es ese
Script en Base64, listo para que el juego lo cargue en lugar de `lola.npc`.
"""

import base64
import binascii
import re

INDENTACION = "    "

# Líneas que forman parte de un Script que solo agrega Items.
_LINEA_INVENTORY_ADD = re.compile(r"^inventory\.add\s+(\d+)\s+(\S+)$")
_LINEAS_DE_AGREGAR_ITEMS = (
    re.compile(r"^\S+: DO$"),
    re.compile(r"^on activate \S+$"),
    re.compile(r"^user\.state get$"),
    re.compile(r"^after \d+ \S+$"),
    _LINEA_INVENTORY_ADD,
)


class EncodeInvalido(Exception):
    """El texto no es un Encode."""


def generar_script(pedidos: list[tuple[str, int]]) -> str:
    """Script que agrega cada Item en su cantidad, encadenando un bloque `A<n>` por Item.

    El formato (incluida la línea de 4 espacios tras `on activate` y los dos saltos
    finales) reproduce el de los Encodes que ya se sabe que funcionan en el juego.
    """
    lineas = ["INICIO: DO", f"{INDENTACION}on activate A1", INDENTACION]
    for n, (ruta, cantidad) in enumerate(pedidos, start=1):
        siguiente = f"A{n + 1}" if n < len(pedidos) else "INICIO"
        lineas += [
            f"A{n}: DO",
            f"{INDENTACION}user.state get",
            f"{INDENTACION}inventory.add {cantidad} {ruta}",
            f"{INDENTACION}after 1 {siguiente}",
        ]
        if n < len(pedidos):
            lineas.append("")
    return "\n".join(lineas) + "\n\n"


def leer_script(script: str) -> tuple[list[tuple[str, int]], bool]:
    """(Items y cantidades que agrega el Script, si además hace otras cosas).

    Un Item que aparece varias veces suma sus cantidades.
    """
    pedidos: dict[str, int] = {}
    otros_comandos = False
    for linea in script.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if agregado := _LINEA_INVENTORY_ADD.match(linea):
            ruta = agregado.group(2)
            pedidos[ruta] = pedidos.get(ruta, 0) + int(agregado.group(1))
        elif not any(p.match(linea) for p in _LINEAS_DE_AGREGAR_ITEMS):
            otros_comandos = True
    return list(pedidos.items()), otros_comandos


def codificar(script: str) -> str:
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def decodificar(encode: str) -> str:
    """Script de un Encode. Se ignoran espacios y saltos de línea dentro del Encode."""
    compacto = "".join(encode.split())
    if not compacto:
        raise EncodeInvalido("El Encode está vacío")
    try:
        datos = base64.b64decode(compacto, validate=True)
    except (binascii.Error, ValueError) as e:
        raise EncodeInvalido("El texto no es un Encode (Base64 inválido)") from e
    try:
        script = datos.decode("utf-8")
    except UnicodeDecodeError:
        script = datos.decode("latin-1")
    # Un texto cualquiera puede ser Base64 válido por casualidad, pero decodifica a bytes sin sentido.
    if any(not c.isprintable() and c not in "\t\r\n" for c in script):
        raise EncodeInvalido("El texto no es un Encode")
    return script

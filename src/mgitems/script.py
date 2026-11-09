"""Scripts NPC y Encodes.

Un Script es el programa en el lenguaje de los NPC del juego; un Encode es ese
Script en Base64, listo para que el juego lo cargue en lugar de `lola.npc`.
"""

import base64
import binascii
import json
import re

INDENTACION = "    "

# Líneas que forman parte de un Script que solo agrega Items.
_LINEA_INVENTORY_ADD = re.compile(r"^inventory\.add\s+(\d+)\s+(\S+)$")
_LINEA_INVENTORY_ADD_OPTIONS = re.compile(r"^inventory\.addOptions\s+(\S+)\s+(\d+)\s+\S+.*$")
_LINEAS_DE_AGREGAR_ITEMS = (
    re.compile(r"^\S+: DO$"),
    re.compile(r"^on activate \S+$"),
    re.compile(r"^user\.state get$"),
    re.compile(r"^after \d+ \S+$"),
    re.compile(r"^user\.attr \S+ \S+$"),
    _LINEA_INVENTORY_ADD,
    _LINEA_INVENTORY_ADD_OPTIONS,
)


class EncodeInvalido(Exception):
    """El texto no es un Encode."""


def _lineas_colores(colores: dict) -> list[str]:
    """Líneas `user.attr colorN <entero>` para aplicar colores al avatar.

    Convierte el color de hex (#RRGGBB) a entero porque el juego lo espera así
    (el mismo formato que usa `adds.color1` en los AS3 de los items).
    """
    return [f"{INDENTACION}user.attr {c} {int(v.lstrip('#'), 16)}" for c, v in colores.items()]


def generar_script(pedidos: list[tuple[str, int]], colores: dict | None = None) -> str:
    """Script que agrega cada Item en su cantidad, encadenando un bloque `A<n>` por Item.

    El formato (incluida la línea de 4 espacios tras `on activate` y los dos saltos
    finales) reproduce el de los Encodes que ya se sabe que funcionan en el juego.
    Si se pasan `colores` ({"color1": "#RRGGBB", …}), se aplican en el último bloque
    con `user.attr`, antes del `after`.
    """
    lineas = ["INICIO: DO", f"{INDENTACION}on activate A1", INDENTACION]
    for n, (ruta, cantidad) in enumerate(pedidos, start=1):
        siguiente = f"A{n + 1}" if n < len(pedidos) else "INICIO"
        lineas += [
            f"A{n}: DO",
            f"{INDENTACION}user.state get",
            f"{INDENTACION}inventory.add {cantidad} {ruta}",
        ]
        if n == len(pedidos) and colores:
            lineas += _lineas_colores(colores)
        lineas.append(f"{INDENTACION}after 1 {siguiente}")
        if n < len(pedidos):
            lineas.append("")
    return "\n".join(lineas) + "\n\n"


def generar_script_con_atributos(pedidos: list[tuple[str, int, dict]], colores: dict | None = None) -> str:
    """Como `generar_script`, pero cada Item llega con atributos propios (`inventory.addOptions`).

    `inventory.addOptions <Item> <cantidad> <catálogo> <atributos>` del juego (`NpcActionRunner.addItemWithOptions`)
    los suma a los del Item al recibirlo (`mergeAttrs` en `InventoryUtil.doAcquireObject`), y el servidor los guarda
    en ese objeto: el mismo Item puede llegar varias veces, cada una con otros atributos, sin trucar su SWF. Los
    atributos van como JSON sin espacios, porque el guion separa los argumentos por espacios (y no deja comillas
    dentro de un argumento entre comillas). Sin catálogo: `null`.
    Si se pasan `colores`, se aplican con `user.attr` en el último bloque."""
    lineas = ["INICIO: DO", f"{INDENTACION}on activate A1", INDENTACION]
    for n, (ruta, cantidad, atributos) in enumerate(pedidos, start=1):
        texto = json.dumps(atributos, separators=(",", ":"), ensure_ascii=True)
        if any(c.isspace() for c in texto):
            raise ValueError(f"los atributos de {ruta} no pueden tener espacios")
        siguiente = f"A{n + 1}" if n < len(pedidos) else "INICIO"
        lineas += [
            f"A{n}: DO",
            f"{INDENTACION}user.state get",
            f"{INDENTACION}inventory.addOptions {ruta} {cantidad} null {texto}",
        ]
        if n == len(pedidos) and colores:
            lineas += _lineas_colores(colores)
        lineas.append(f"{INDENTACION}after 1 {siguiente}")
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
        elif con_attrs := _LINEA_INVENTORY_ADD_OPTIONS.match(linea):
            ruta = con_attrs.group(1)
            pedidos[ruta] = pedidos.get(ruta, 0) + int(con_attrs.group(2))
        elif not any(p.match(linea) for p in _LINEAS_DE_AGREGAR_ITEMS):
            otros_comandos = True
    return list(pedidos.items()), otros_comandos


def generar_script_monedas(cantidad: int) -> str:
    """Script que da `cantidad` monedas al jugador via `reward.coin`."""
    cant = str(cantidad)
    return (
        f"initial: DO\n"
        f"{INDENTACION}on activate Ghoster\n"
        f"\n"
        f"Ghoster: DO\n"
        f"{INDENTACION}user.state get\n"
        f'{INDENTACION}modal.show "{cant}" "dailyBonus/props.moneda"\n'
        f"{INDENTACION}    inventory.add 1 monedas.sss\n"
        f"{INDENTACION}reward.coin {cant}\n"
        f"{INDENTACION}    goto initial\n"
    )


def generar_script_colores(colores: dict) -> str:
    """Script que setea los colores del Gaturro via `user.attr` (`color1`–`color4`).

    Los colores del avatar se guardan en el perfil del usuario en el servidor;
    no dependen de un Item y persisten permanentemente (ADR 0003, ADR 0005).
    """
    lineas = ["INICIO: DO", f"{INDENTACION}on activate A1", INDENTACION, "A1: DO"]
    lineas += _lineas_colores(colores)
    lineas.append(f"{INDENTACION}after 1 INICIO")
    return "\n".join(lineas) + "\n\n"


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

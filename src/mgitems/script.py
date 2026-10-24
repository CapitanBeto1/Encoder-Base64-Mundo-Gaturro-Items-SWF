"""Scripts NPC y Encodes.

Un Script es el programa en el lenguaje de los NPC del juego; un Encode es ese
Script en Base64, listo para que el juego lo cargue en lugar de `lola.npc`.
"""

import base64

INDENTACION = "    "


def generar_script(rutas_items: list[str]) -> str:
    """Script que agrega una unidad de cada Item al inventario, encadenando un bloque por Item.

    El formato (incluida la línea de 4 espacios tras `on activate` y los dos saltos
    finales) reproduce el de los Encodes que ya se sabe que funcionan en el juego.
    """
    lineas = ["INICIO: DO", f"{INDENTACION}on activate A1", INDENTACION]
    for n, ruta in enumerate(rutas_items, start=1):
        siguiente = f"A{n + 1}" if n < len(rutas_items) else "INICIO"
        lineas += [
            f"A{n}: DO",
            f"{INDENTACION}user.state get",
            f"{INDENTACION}inventory.add 1 {ruta}",
            f"{INDENTACION}after 1 {siguiente}",
        ]
        if n < len(rutas_items):
            lineas.append("")
    return "\n".join(lineas) + "\n\n"


def codificar(script: str) -> str:
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def decodificar(encode: str) -> str:
    return base64.b64decode(encode.strip(), validate=True).decode("utf-8")

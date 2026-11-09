"""Colores del Gaturro: aplica los colores del avatar al juego via user.attr."""

import re

_CLAVES = frozenset({"color1", "color2", "color3", "color4"})
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class Colores:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def aplicar_colores(self, colores: dict) -> dict:
        """Genera un Encode con `user.attr` para aplicar los colores del Gaturro al juego.

        Los colores se guardan en el perfil del usuario en el servidor y persisten
        permanentemente (ADR 0003: color1=cara, color2=cuerpo, color3=ojos, color4=nariz).
        """
        if not isinstance(colores, dict) or not colores:
            return {"ok": False, "error": "Elegí al menos un color."}
        invalidas = set(colores) - _CLAVES
        if invalidas:
            return {"ok": False, "error": f"Claves de color inválidas: {', '.join(sorted(invalidas))}."}
        invalidos = {c: v for c, v in colores.items() if not _HEX.match(str(v))}
        if invalidos:
            return {"ok": False, "error": f"Color hexadecimal inválido: {', '.join(f'{c}={v}' for c, v in invalidos.items())}."}
        from mgitems.script import codificar, generar_script_colores
        script = generar_script_colores(colores)
        encode = codificar(script)
        return {"ok": True, "encode": encode, "script": script, "colores": colores}

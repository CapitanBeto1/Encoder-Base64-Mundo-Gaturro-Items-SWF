"""Arma el SWF del Gaturro en vivo (docs/adr/0009) con el archivo que baja `obtener_binarios.py`.

Lo bajado (`anim_preview.swf`, de naw-trucador) trae el Gaturro del juego (`assets.GaturroMC`, el actual, con
todas sus animaciones) y el código del juego que lo viste (`Gaturro` y sus ayudantes). Con FFDec se le cambian
tres clases por las de `scripts/gaturro_en_vivo/`:

- `MMO`, la clase principal: crea un `Gaturro` del juego y recibe sus atributos de la página (`mgVestir`);
- `api` y `user`, dos globales del juego que el `Gaturro` consulta: pasan a aceptar cualquier objeto, para
  darle los mínimos que necesita sin armar el juego entero.

El resto del archivo queda como vino.
"""

import shutil
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDec

CLASES = Path(__file__).resolve().parent / "gaturro_en_vivo"
BAJADO = "anim_preview.swf"
ARMADO = "gaturro.swf"


def armar(carpeta: Path) -> None:
    """Deja `carpeta/gaturro.swf` armado con `carpeta/anim_preview.swf`, y saca el bajado. RuntimeError si no se pudo."""
    ffdec = FFDec()
    with tempfile.TemporaryDirectory() as tmp:
        armado = Path(tmp) / ARMADO
        ffdec.ejecutar("-importScript", str(carpeta / BAJADO), str(armado), str(CLASES))
        ffdec.ejecutar("-selectclass", "MMO", "-export", "script", str(Path(tmp) / "ver"), str(armado))
        principal = Path(tmp) / "ver" / "scripts" / "MMO.as"
        if not principal.is_file() or "mgVestir" not in principal.read_text(encoding="utf-8"):
            raise RuntimeError("FFDec no pudo armar el Gaturro en vivo")
        shutil.copyfile(armado, carpeta / ARMADO)
    (carpeta / BAJADO).unlink()

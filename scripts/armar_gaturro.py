"""Arma el SWF del Gaturro en vivo (docs/adr/0009) con el archivo que baja `obtener_binarios.py`.

Lo bajado (`anim_preview.swf`, de naw-trucador) trae el Gaturro del juego (`assets.GaturroMC`, el actual, con
todas sus animaciones) y el código del juego que lo viste (`Gaturro` y sus ayudantes), y también su editor de Piezas
(`ClothEditorModal`). Con FFDec se le cambian unas clases por las de `scripts/gaturro_en_vivo/`:

- `MMO`, la clase principal: crea un `Gaturro` del juego y recibe sus atributos de la página (`mgVestir`), y abre las
  ventanas de personalizar del juego: el editor de Piezas (`mgEditar`) o su menú (`mgPersonalizar`);
- `api`, `user`, `region`, `server` y `audio`, globales del juego que consultan el `Gaturro` y el editor: pasan a
  aceptar cualquier objeto, para darles los mínimos que necesitan sin armar el juego entero.

Y al `Gaturro` del juego se le saca una regla, `checkTransport`: en este cliente un vehículo (una Pieza con `type`)
solo se dibuja en Transporte, pero en el juego se ve también en otras Partes (la mano, la cabeza…), y la vista previa
tiene que ser igual al juego. La clase se saca del bajado y se cambia ahí: el repositorio no guarda nada del juego.

El resto del archivo queda como vino.
"""

import shutil
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDec

CLASES = Path(__file__).resolve().parent / "gaturro_en_vivo"
BAJADO = "anim_preview.swf"
ARMADO = "gaturro.swf"
GATURRO = "com.qb9.gaturro.view.world.avatars.Gaturro"
# `Gaturro.checkTransport`: true (no agregar la Pieza) si es un vehículo fuera de Transporte. Pasa a no frenar nunca.
REGLA_DEL_VEHICULO = 'return "type" in param1 && param2.name != AvatarAttributes.TRANSPORT_KEY;'
SIN_LA_REGLA = "return false;"


def armar(carpeta: Path) -> None:
    """Deja `carpeta/gaturro.swf` armado con `carpeta/anim_preview.swf`, y saca el bajado. RuntimeError si no se pudo."""
    ffdec = FFDec()
    with tempfile.TemporaryDirectory() as tmp:
        clases = Path(tmp) / "clases"
        shutil.copytree(CLASES, clases)
        _gaturro_sin_la_regla_del_vehiculo(ffdec, carpeta / BAJADO, clases, Path(tmp) / "gaturro")
        armado = Path(tmp) / ARMADO
        ffdec.ejecutar("-importScript", str(carpeta / BAJADO), str(armado), str(clases))
        ffdec.ejecutar("-selectclass", "MMO", "-export", "script", str(Path(tmp) / "ver"), str(armado))
        principal = Path(tmp) / "ver" / "scripts" / "MMO.as"
        if not principal.is_file() or "mgVestir" not in principal.read_text(encoding="utf-8"):
            raise RuntimeError("FFDec no pudo armar el Gaturro en vivo")
        ffdec.ejecutar("-selectclass", GATURRO, "-export", "script", str(Path(tmp) / "ver"), str(armado))
        if REGLA_DEL_VEHICULO in _clase_exportada(Path(tmp) / "ver").read_text(encoding="utf-8"):
            raise RuntimeError("FFDec no pudo sacarle al Gaturro la regla de los vehículos")
        shutil.copyfile(armado, carpeta / ARMADO)
    (carpeta / BAJADO).unlink()


def _clase_exportada(carpeta: Path) -> Path:
    return carpeta / "scripts" / Path(*GATURRO.split(".")).with_suffix(".as")


def _gaturro_sin_la_regla_del_vehiculo(ffdec: FFDec, bajado: Path, clases: Path, tmp: Path) -> None:
    """Deja en `clases` la clase `Gaturro` del bajado sin `checkTransport` (ver arriba). RuntimeError si no está."""
    ffdec.ejecutar("-selectclass", GATURRO, "-export", "script", str(tmp), str(bajado))
    codigo = _clase_exportada(tmp).read_text(encoding="utf-8")
    if codigo.count(REGLA_DEL_VEHICULO) != 1:
        raise RuntimeError("El Gaturro bajado no tiene la regla de los vehículos que se esperaba")
    destino = clases / Path(*GATURRO.split(".")).with_suffix(".as")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(codigo.replace(REGLA_DEL_VEHICULO, SIN_LA_REGLA), encoding="utf-8")

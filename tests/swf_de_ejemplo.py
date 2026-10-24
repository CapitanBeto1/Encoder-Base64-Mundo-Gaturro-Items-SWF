"""SWF de assets mínimos para pruebas.

`crear_swf` arma solo encabezado, SymbolClass y fin. Con `con_dibujos=True`, cada
clase es además un sprite con un rectángulo de color, para que FFDec lo pueda exportar.
"""

import lzma
import struct
import zlib

TAG_FIN, TAG_SHOW_FRAME, TAG_DEFINE_SHAPE, TAG_PLACE_OBJECT2, TAG_DEFINE_SPRITE, TAG_SYMBOL_CLASS = 0, 1, 2, 26, 39, 76
LADO = 800  # twips (40 píxeles)


def _tag(codigo: int, cuerpo: bytes) -> bytes:
    if len(cuerpo) < 0x3F:
        return struct.pack("<H", codigo << 6 | len(cuerpo)) + cuerpo
    return struct.pack("<HI", codigo << 6 | 0x3F, len(cuerpo)) + cuerpo


class _Bits:
    """Escritor de campos de bits del formato SWF (más significativo primero)."""

    def __init__(self):
        self._bits: list[int] = []

    def u(self, valor: int, cantidad: int) -> "_Bits":
        self._bits += [(valor >> i) & 1 for i in range(cantidad - 1, -1, -1)]
        return self

    def s(self, valor: int, cantidad: int) -> "_Bits":
        return self.u(valor & ((1 << cantidad) - 1), cantidad)

    def bytes(self) -> bytes:
        bits = self._bits + [0] * (-len(self._bits) % 8)
        return bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))


def _rect(xmin: int, xmax: int, ymin: int, ymax: int, bits: int = 13) -> bytes:
    return _Bits().u(bits, 5).s(xmin, bits).s(xmax, bits).s(ymin, bits).s(ymax, bits).bytes()


def _cuadrado(id_forma: int, color: tuple[int, int, int]) -> bytes:
    """DefineShape con un cuadrado relleno de un color."""
    estilos = bytes([1, 0x00, *color]) + bytes([0])  # 1 relleno sólido, 0 líneas
    n = 13
    registros = _Bits().u(1, 4).u(0, 4)  # NumFillBits=1, NumLineBits=0
    registros.u(0, 1).u(0, 1).u(0, 1).u(1, 1).u(0, 1).u(1, 1)  # StyleChange: FillStyle1 + MoveTo
    registros.u(n, 5).s(0, n).s(0, n).u(1, 1)  # mover a (0, 0), FillStyle1 = 1
    for dx, dy in ((LADO, 0), (0, LADO), (-LADO, 0), (0, -LADO)):
        registros.u(1, 1).u(1, 1).u(n - 2, 4).u(0, 1)  # recta, no general
        if dx:
            registros.u(0, 1).s(dx, n)
        else:
            registros.u(1, 1).s(dy, n)
    registros.u(0, 6)  # fin de la forma
    cuerpo = struct.pack("<H", id_forma) + _rect(0, LADO, 0, LADO) + estilos + registros.bytes()
    return _tag(TAG_DEFINE_SHAPE, cuerpo)


def _sprite(id_sprite: int, id_forma: int) -> bytes:
    """DefineSprite de un cuadro que muestra la forma."""
    colocar = _tag(TAG_PLACE_OBJECT2, bytes([0x02]) + struct.pack("<HH", 1, id_forma))
    cuerpo = struct.pack("<HH", id_sprite, 1) + colocar + _tag(TAG_SHOW_FRAME, b"") + _tag(TAG_FIN, b"")
    return _tag(TAG_DEFINE_SPRITE, cuerpo)


def crear_swf(clases: list[str], compresion: str = "CWS", con_dibujos: bool = False) -> bytes:
    tags = b""
    ids = list(range(1, len(clases) + 1))
    if con_dibujos:
        # Cada clase n: forma con id 1000+n y sprite con id n.
        for n in ids:
            color = (40 * n % 256, 200 - 30 * n % 200, 120)
            tags += _cuadrado(1000 + n, color) + _sprite(n, 1000 + n)
    symbol_class = struct.pack("<H", len(clases))
    for id_simbolo, nombre in zip(ids, clases):
        symbol_class += struct.pack("<H", id_simbolo) + nombre.encode("utf-8") + b"\0"
    tags += _tag(TAG_SYMBOL_CLASS, symbol_class) + _tag(TAG_SHOW_FRAME, b"") + _tag(TAG_FIN, b"")

    cuerpo = _rect(0, LADO, 0, LADO) + struct.pack("<HH", 24 << 8, 1) + tags
    largo_total = 8 + len(cuerpo)
    cabecera = struct.pack("<BI", 10, largo_total)

    if compresion == "FWS":
        return b"FWS" + cabecera + cuerpo
    if compresion == "CWS":
        return b"CWS" + cabecera + zlib.compress(cuerpo)
    if compresion == "ZWS":
        alone = lzma.compress(cuerpo, format=lzma.FORMAT_ALONE)
        propiedades, datos = alone[:5], alone[13:]
        return b"ZWS" + cabecera + struct.pack("<I", len(datos)) + propiedades + datos
    raise ValueError(compresion)

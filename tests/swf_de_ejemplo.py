"""SWF de assets mínimos para pruebas: solo encabezado, un tag SymbolClass y el tag de fin."""

import lzma
import struct
import zlib


def _tag(codigo: int, cuerpo: bytes) -> bytes:
    if len(cuerpo) < 0x3F:
        return struct.pack("<H", codigo << 6 | len(cuerpo)) + cuerpo
    return struct.pack("<HI", codigo << 6 | 0x3F, len(cuerpo)) + cuerpo


def _symbol_class(clases: list[str]) -> bytes:
    cuerpo = struct.pack("<H", len(clases))
    for id_simbolo, nombre in enumerate(clases, start=1):
        cuerpo += struct.pack("<H", id_simbolo) + nombre.encode("utf-8") + b"\0"
    return _tag(76, cuerpo)


def crear_swf(clases: list[str], compresion: str = "CWS") -> bytes:
    rect = bytes([0x00])  # RECT con 0 bits por campo: 1 byte
    cuerpo = rect + struct.pack("<HH", 24 << 8, 1) + _symbol_class(clases) + _tag(0, b"")
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

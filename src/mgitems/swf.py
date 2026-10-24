"""Lectura de SWF de assets: descompresión y nombres de clases (tag `SymbolClass`)."""

import lzma
import struct
import zlib

TAG_FIN = 0
TAG_SYMBOL_CLASS = 76


class SwfInvalido(Exception):
    """El archivo no es un SWF o está dañado."""


def leer_clases(data: bytes) -> list[str]:
    """Nombres de todas las clases que el SWF asocia a símbolos, en el orden en que aparecen."""
    return [nombre for _, nombre in leer_simbolos(data)]


def leer_simbolos(data: bytes) -> list[tuple[int, str]]:
    """(id del símbolo, nombre de la clase) de cada entrada de `SymbolClass`."""
    swf = _descomprimir(data)
    simbolos = []
    try:
        for codigo, cuerpo in _tags(swf):
            if codigo == TAG_SYMBOL_CLASS:
                simbolos += _entradas_symbol_class(cuerpo)
    except (struct.error, IndexError, ValueError, UnicodeDecodeError) as e:
        raise SwfInvalido("El SWF está dañado") from e
    return simbolos


def _descomprimir(data: bytes) -> bytes:
    """El SWF completo sin comprimir (firma `FWS`)."""
    firma = data[:3]
    if len(data) < 8 or firma not in (b"FWS", b"CWS", b"ZWS"):
        raise SwfInvalido("El archivo no es un SWF")
    if firma == b"FWS":
        return data
    largo_cuerpo = struct.unpack_from("<I", data, 4)[0] - 8
    try:
        if firma == b"CWS":
            cuerpo = zlib.decompress(data[8:])
        else:
            cuerpo = _descomprimir_lzma(data[12:17], data[17:], largo_cuerpo)
    except (zlib.error, lzma.LZMAError, IndexError) as e:
        raise SwfInvalido("El SWF está dañado") from e
    if len(cuerpo) < largo_cuerpo:
        raise SwfInvalido("El SWF está dañado")
    return b"FWS" + data[3:8] + cuerpo[:largo_cuerpo]


def _descomprimir_lzma(propiedades: bytes, datos: bytes, largo: int) -> bytes:
    """Cuerpo de un SWF `ZWS`: LZMA sin encabezado, con o sin marca de fin.

    Las 5 bytes de propiedades son las de LZMA: lc/lp/pb codificados en un byte
    y el tamaño de diccionario (4 bytes).
    """
    lc_lp_pb = propiedades[0]
    filtro = {
        "id": lzma.FILTER_LZMA1,
        "lc": lc_lp_pb % 9,
        "lp": lc_lp_pb // 9 % 5,
        "pb": lc_lp_pb // 45,
        "dict_size": struct.unpack("<I", propiedades[1:5])[0],
    }
    return lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[filtro]).decompress(datos, max_length=largo)


def _tags(swf: bytes):
    """(código, cuerpo) de cada tag, salteando el encabezado (rect, frame rate, frames)."""
    bits_rect = swf[8] >> 3
    pos = 8 + (5 + bits_rect * 4 + 7) // 8 + 4
    while pos < len(swf):
        cabecera = struct.unpack_from("<H", swf, pos)[0]
        pos += 2
        codigo, largo = cabecera >> 6, cabecera & 0x3F
        if largo == 0x3F:
            largo = struct.unpack_from("<I", swf, pos)[0]
            pos += 4
        if pos + largo > len(swf):
            raise ValueError("tag truncado")
        yield codigo, swf[pos:pos + largo]
        pos += largo
        if codigo == TAG_FIN:
            return


def _entradas_symbol_class(cuerpo: bytes) -> list[tuple[int, str]]:
    cantidad = struct.unpack_from("<H", cuerpo, 0)[0]
    pos = 2
    entradas = []
    for _ in range(cantidad):
        id_simbolo = struct.unpack_from("<H", cuerpo, pos)[0]
        pos += 2
        fin = cuerpo.index(b"\0", pos)
        entradas.append((id_simbolo, cuerpo[pos:fin].decode("utf-8")))
        pos = fin + 1
    return entradas

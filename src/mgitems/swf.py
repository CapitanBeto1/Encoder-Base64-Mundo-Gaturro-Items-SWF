"""Lectura de SWF de assets: descompresión, nombres de clases (tag `SymbolClass`) y dónde queda el dibujo
de cada símbolo."""

import lzma
import struct
import zlib

TAG_FIN = 0
TAG_SHOW_FRAME = 1
TAG_REMOVE_OBJECT2 = 28
TAG_DEFINE_SPRITE = 39
TAG_PLACE_OBJECT2 = 26
TAG_PLACE_OBJECT3 = 70
TAG_SYMBOL_CLASS = 76
# Tags que definen un dibujo con su rectángulo justo después del id (formas, formas animadas, textos).
TAGS_CON_RECTANGULO = (2, 22, 32, 83, 46, 84, 11, 33, 37)


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


def limites_de_simbolos(data: bytes) -> dict[str, tuple[float, float, float, float]]:
    """Clase → rectángulo (x0, y0, x1, y1, en píxeles) del primer cuadro de su símbolo.

    El rectángulo es relativo al punto de registro del símbolo: para una Pieza, el punto del cuerpo
    del Gaturro donde el juego la pega. Los símbolos sin dibujo no aparecen.
    """
    swf = _descomprimir(data)
    rectangulos, sprites, simbolos = {}, {}, []
    try:
        for codigo, cuerpo in _tags(swf):
            if codigo in TAGS_CON_RECTANGULO:
                rectangulos[struct.unpack_from("<H", cuerpo)[0]] = _rectangulo(cuerpo, 2)
            elif codigo == TAG_DEFINE_SPRITE:
                sprites[struct.unpack_from("<H", cuerpo)[0]] = cuerpo[4:]
            elif codigo == TAG_SYMBOL_CLASS:
                simbolos += _entradas_symbol_class(cuerpo)
        limites = _Limites(rectangulos, sprites)
        resultado = {}
        for id_simbolo, nombre in simbolos:
            rectangulo = limites.de(id_simbolo)
            if rectangulo:
                resultado[nombre] = tuple(round(v / 20, 1) for v in rectangulo)  # twips → píxeles
    except (struct.error, IndexError, ValueError, UnicodeDecodeError) as e:
        raise SwfInvalido("El SWF está dañado") from e
    return resultado


class _Limites:
    """Rectángulos de formas y sprites (un sprite: la unión de lo que coloca en su primer cuadro)."""

    def __init__(self, rectangulos: dict, sprites: dict):
        self._rectangulos, self._sprites, self._calculados = rectangulos, sprites, {}

    def de(self, id_simbolo: int):
        if id_simbolo in self._rectangulos:
            return self._rectangulos[id_simbolo]
        if id_simbolo not in self._sprites or id_simbolo in self._calculados:
            return self._calculados.get(id_simbolo)
        self._calculados[id_simbolo] = None  # un sprite que se contiene a sí mismo no suma
        resultado = None
        for hijo, matriz in self._primer_cuadro(self._sprites[id_simbolo]).values():
            rectangulo = self.de(hijo) if hijo is not None else None
            if rectangulo:
                resultado = _unir(resultado, _transformar(matriz, rectangulo))
        self._calculados[id_simbolo] = resultado
        return resultado

    @staticmethod
    def _primer_cuadro(cuerpo: bytes) -> dict[int, list]:
        """Profundidad → [id del símbolo, matriz] de lo que hay en el primer cuadro del sprite."""
        lista, pos = {}, 0
        while pos < len(cuerpo):
            cabecera = struct.unpack_from("<H", cuerpo, pos)[0]
            pos += 2
            codigo, largo = cabecera >> 6, cabecera & 0x3F
            if largo == 0x3F:
                largo = struct.unpack_from("<I", cuerpo, pos)[0]
                pos += 4
            tag, pos = cuerpo[pos:pos + largo], pos + largo
            if codigo in (TAG_SHOW_FRAME, TAG_FIN):
                break
            if codigo == TAG_REMOVE_OBJECT2:
                lista.pop(struct.unpack_from("<H", tag)[0], None)
            elif codigo in (TAG_PLACE_OBJECT2, TAG_PLACE_OBJECT3):
                banderas, q = tag[0], 1
                if codigo == TAG_PLACE_OBJECT3:
                    banderas3, q = tag[1], 2
                    if banderas3 & 0x08 or (banderas3 & 0x10 and banderas & 0x02):  # nombre de clase
                        q = tag.index(b"\0", q) + 1
                profundidad = struct.unpack_from("<H", tag, q)[0]
                q += 2
                entrada = lista.setdefault(profundidad, [None, (1.0, 0.0, 0.0, 1.0, 0, 0)])
                if banderas & 0x02:
                    entrada[0] = struct.unpack_from("<H", tag, q)[0]
                    q += 2
                if banderas & 0x04:
                    entrada[1] = _matriz(tag, q)
        return lista


class _Bits:
    def __init__(self, datos: bytes, inicio: int):
        self._datos, self._pos = datos, inicio * 8

    def sin_signo(self, n: int) -> int:
        valor = 0
        for _ in range(n):
            valor = (valor << 1) | (self._datos[self._pos >> 3] >> (7 - (self._pos & 7)) & 1)
            self._pos += 1
        return valor

    def con_signo(self, n: int) -> int:
        valor = self.sin_signo(n)
        return valor - (1 << n) if n and valor & (1 << (n - 1)) else valor


def _rectangulo(datos: bytes, inicio: int) -> tuple[int, int, int, int]:
    bits = _Bits(datos, inicio)
    n = bits.sin_signo(5)
    x0, x1, y0, y1 = (bits.con_signo(n) for _ in range(4))
    return x0, y0, x1, y1


def _matriz(datos: bytes, inicio: int) -> tuple:
    bits = _Bits(datos, inicio)
    a = d = 1.0
    b = c = 0.0
    if bits.sin_signo(1):
        n = bits.sin_signo(5)
        a, d = bits.con_signo(n) / 65536, bits.con_signo(n) / 65536
    if bits.sin_signo(1):
        n = bits.sin_signo(5)
        b, c = bits.con_signo(n) / 65536, bits.con_signo(n) / 65536
    n = bits.sin_signo(5)
    return a, b, c, d, bits.con_signo(n), bits.con_signo(n)


def _transformar(matriz: tuple, rectangulo: tuple) -> tuple:
    a, b, c, d, tx, ty = matriz
    x0, y0, x1, y1 = rectangulo
    esquinas = [(a * x + c * y + tx, b * x + d * y + ty) for x in (x0, x1) for y in (y0, y1)]
    xs, ys = [x for x, _ in esquinas], [y for _, y in esquinas]
    return min(xs), min(ys), max(xs), max(ys)


def _unir(a, b):
    if a is None:
        return b
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


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

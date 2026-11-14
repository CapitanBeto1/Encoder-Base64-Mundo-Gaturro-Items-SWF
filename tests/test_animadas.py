"""Qué se ve animado: los Items y las Piezas cuyo dibujo se mueve, y los Items que ponen una Pieza que se mueve."""
import struct
import zlib

import pytest

from fuente_falsa import FuenteFalsa
from mgitems.categorias import animadas, piezas_que_pone, se_mueven
from mgitems.prendas import leer_item_base
from mgitems.swf import ADENTRO, RAIZ, movimientos
from swf_de_ejemplo import LADO, _cuadrado, _rect, _tag
from test_categorias import nucleo_con, por_ruta
from test_mochila import codigo_mochila
from test_prendas import PrendasFalsas, codigo_prenda

FRAME_LABEL, PLACE_OBJECT2, SHOW_FRAME, FIN, DEFINE_SPRITE, SYMBOL_CLASS = 43, 26, 1, 0, 39, 76


def _colocar(id_simbolo: int | None = None, x: int = 0) -> bytes:
    """PlaceObject2 en la profundidad 1: coloca `id_simbolo` o mueve lo que está ahí a `x`."""
    if id_simbolo is not None:
        return _tag(PLACE_OBJECT2, bytes([0x02]) + struct.pack("<HH", 1, id_simbolo))
    return _tag(PLACE_OBJECT2, bytes([0x01 | 0x04]) + struct.pack("<H", 1) + _matriz_traslacion(x))  # mover, con matriz


def _matriz_traslacion(x: int) -> bytes:
    """MATRIX de SWF solo con traslación (x, 0), en twips."""
    nbits = 16
    bits = "0" + "0" + format(nbits, "05b") + format(x & 0xFFFF, "016b") + format(0, "016b")
    bits += "0" * (-len(bits) % 8)
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


def _sprite(id_sprite: int, cuadros: list[bytes], rotulo: str | None = None) -> bytes:
    """DefineSprite con un cuadro por elemento de `cuadros` (los tags de ese cuadro) y, si hay, un rótulo al principio."""
    cuerpo = b"".join(cuadro + _tag(SHOW_FRAME, b"") for cuadro in cuadros)
    if rotulo:
        cuerpo = _tag(FRAME_LABEL, rotulo.encode() + b"\0") + cuerpo
    return _tag(DEFINE_SPRITE, struct.pack("<HH", id_sprite, len(cuadros)) + cuerpo + _tag(FIN, b""))


def swf_con(sprites: bytes, clases: dict[str, int]) -> bytes:
    tags = _cuadrado(100, (200, 40, 40)) + sprites
    simbolos = struct.pack("<H", len(clases)) + b"".join(struct.pack("<H", i) + n.encode() + b"\0" for n, i in clases.items())
    tags += _tag(SYMBOL_CLASS, simbolos) + _tag(SHOW_FRAME, b"") + _tag(FIN, b"")
    cuerpo = _rect(0, LADO, 0, LADO) + struct.pack("<HH", 24 << 8, 1) + tags
    return b"CWS" + struct.pack("<BI", 10, 8 + len(cuerpo)) + zlib.compress(cuerpo)


# Un dibujo fijo; uno que se mueve (cambia de lugar cada cuadro); uno con estados (rótulos); uno fijo con uno que se
# mueve adentro; uno de varios cuadros que no cambia nada.
FIJO, MUEVE, ESTADOS, CONTIENE, QUIETO = 1, 2, 3, 4, 5
EJEMPLO = swf_con(
    _sprite(FIJO, [_colocar(100)])
    + _sprite(MUEVE, [_colocar(100), _colocar(x=200), _colocar(x=400)])
    + _sprite(ESTADOS, [_colocar(100), _colocar(x=200)], rotulo="double")
    + _sprite(CONTIENE, [_colocar(MUEVE)])
    + _sprite(QUIETO, [_colocar(100), b"", b""]),
    {"gorroFijo_on": FIJO, "chispas_on": MUEVE, "zapato_on": ESTADOS, "gorroConChispas_on": CONTIENE, "quieto_on": QUIETO},
)


def test_que_se_mueve_de_cada_dibujo():
    assert movimientos(EJEMPLO) == {"chispas_on": RAIZ, "gorroConChispas_on": ADENTRO}


def frame1(clase: str, cuerpo: str) -> str:
    return f"""package
{{
   public dynamic class {clase} extends MovieClip
   {{
      public function {clase}()
      {{
         super();
         addFrameScript(0,this.frame1);
      }}
      internal function frame1() : *
      {{
         {cuerpo}
      }}
   }}
}}
"""


def test_lo_que_su_codigo_frena_no_se_mueve_salvo_lo_de_adentro():
    # Un fondo: un cuadro por dibujo y `stop()` en el primero (muestra el elegido).
    fuentes = {"fondo": frame1("fondo", "if(x) { y(); }\n         stop();"), "gorro": frame1("gorro", "stop();")}
    assert se_mueven({"fondo": RAIZ, "gorro": ADENTRO, "chispas": RAIZ}, fuentes) == {"gorro", "chispas"}


def test_las_piezas_que_pone_un_item():
    prenda = leer_item_base(codigo_prenda("gorro", {"hats": "gorro_on", "neck": "costumes.collar_on"}))
    pocion = leer_item_base(codigo_mochila("pocion", "ConsumableMamboAsset",
                                           'adds.effect = "head.granja.crecePrueba";\n         adds.action = "drink.potions.tomar_on";'))
    filtro = leer_item_base(codigo_mochila("sepia", "ConsumableMamboAsset", 'adds.effect = "sepia";'))

    assert piezas_que_pone("ropa", prenda) == ["ropa.gorro_on", "costumes.collar_on"]
    assert piezas_que_pone("potions", pocion) == ["granja.crecePrueba"]  # el efecto sí; la animación de tomarla, no
    assert piezas_que_pone("potions", filtro) == []  # un filtro no es una Pieza


def test_un_item_que_pone_una_pieza_que_se_mueve_se_ve_animado():
    pone = {"gorro": ["ropa.gorro_on"], "pocion": ["granja.crecePrueba"], "remera": ["ropa.remera_on"]}

    resultado = animadas("ropa", {"gorro_on"}, pone, {"granja.crecePrueba"}.__contains__)

    assert resultado == ["gorro", "gorro_on", "pocion"]


# --- En el núcleo ---

def test_del_indice(tmp_path):
    nucleo = nucleo_con(tmp_path, FuenteFalsa(), PrendasFalsas(), {"ropa": {
        "version": "v1", "piezas": {"chispas_on": ["hats"], "gorro_on": ["hats"]}, "items": {"chispas": {"tipo": "prenda"}},
        "animadas": ["chispas", "chispas_on"]}})

    piezas = por_ruta(nucleo.piezas_de_swfs(["ropa"]))
    items = {i["ruta"]: i for i in nucleo.items_de_swfs(["ropa"])["items"]}

    assert piezas["ropa.chispas_on"]["se_mueve"] and not piezas["ropa.gorro_on"]["se_mueve"]
    assert items["ropa.chispas"]["se_mueve"]


def test_un_swf_fuera_del_indice_se_analiza(tmp_path):
    ffdec = PrendasFalsas()
    ffdec.codigo["gorroConChispas"] = codigo_prenda("gorroConChispas", {"hats": "gorroConChispas_on"})
    ffdec.codigo["gorroFijo"] = codigo_prenda("gorroFijo", {"hats": "gorroFijo_on"})
    swf = swf_con(
        _sprite(FIJO, [_colocar(100)]) + _sprite(MUEVE, [_colocar(100), _colocar(x=200)]) + _sprite(CONTIENE, [_colocar(MUEVE)]),
        {"gorroFijo_on": FIJO, "gorroFijo": FIJO, "gorroConChispas_on": CONTIENE, "gorroConChispas": FIJO},
    )
    nucleo = nucleo_con(tmp_path, FuenteFalsa({"ropa": swf}), ffdec, {})

    items = {i["clase"]: i["se_mueve"] for i in nucleo.items_de_swfs(["ropa"])["items"]}
    piezas = {p["clase"]: p["se_mueve"] for p in nucleo.piezas_de_swfs(["ropa"])["piezas"]}

    # El ícono del gorro es fijo, pero la Pieza que viste se mueve: se ve animado.
    assert items == {"gorroConChispas": True, "gorroFijo": False}
    assert piezas == {"gorroConChispas_on": True, "gorroFijo_on": False}


@pytest.mark.parametrize("dañado", [b"CWS\x0a\x00\x00\x00\x00basura", b"FWS"])
def test_un_swf_danado(dañado):
    from mgitems.swf import SwfInvalido
    with pytest.raises(SwfInvalido):
        movimientos(dañado)

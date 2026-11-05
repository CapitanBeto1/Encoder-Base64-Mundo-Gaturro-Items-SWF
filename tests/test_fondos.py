"""Fondos: objetos de la casa que muestran, de los cuadros de su dibujo, el que se elija (comportamiento painting)."""
import json

import pytest

from mgitems.categorias import IndicePiezas
from mgitems.fondos import Fondos, frena_en_el_primer_cuadro
from mgitems.npcs import Comportamientos
from mgitems.nucleo import Nucleo
from mgitems.script import decodificar
from mgitems.swf import cuadros_de_clases
from fuente_falsa import FuenteFalsa
from procesos_falso import ProcesosFalso
from swf_de_ejemplo import crear_swf
from test_npcs import CONOCIDOS, npc
from test_prendas import CLASES, PrendasFalsas, sistema  # noqa: F401 (fixture)

PAINTING = "initial: DO\n\tgotoSync changeFrame checkHost 100\n\nchangeFrame: DO\n\tself.state $(self.attr.frame)\n"


def test_cuenta_los_cuadros_del_dibujo_de_cada_clase():
    data = crear_swf(["fondo", "silla"], con_dibujos=True, cuadros={"fondo": 23})

    assert cuadros_de_clases(data) == {"fondo": 23, "silla": 1}
    assert cuadros_de_clases(crear_swf(["sinDibujo"])) == {"sinDibujo": 1}


def test_sirve_de_fondo_si_frena_en_el_primer_cuadro():
    assert frena_en_el_primer_cuadro("internal function frame1() : *\n      {\n         stop();\n      }")
    assert not frena_en_el_primer_cuadro("internal function frame1() : *\n      {\n         play();\n      }")
    assert not frena_en_el_primer_cuadro("public function x() { stop(); }")  # una animación sin cuadro quieto


class CuadrosFalsos:
    def __init__(self):
        self.pedidos = []

    def cuadros(self, swf, clase, data):
        self.pedidos.append((swf, clase))
        return [f"data:image/png;base64,{clase}{n}" for n in range(1, 4)]


@pytest.fixture
def cuadros():
    return CuadrosFalsos()


@pytest.fixture
def ffdec():
    return PrendasFalsas()


@pytest.fixture
def nucleo(sistema, ffdec, cuadros, tmp_path):
    fuente = FuenteFalsa({"costumes2": crear_swf(CLASES)})
    fuente.npcs = {"painting": npc(PAINTING), "brujaMesa": npc("x: DO\n\tcatalog potions\n")}
    (tmp_path / "comportamientos.json").write_text(json.dumps(CONOCIDOS), encoding="utf-8")
    (tmp_path / "fondos.json").write_text(json.dumps({"fondos": {"costumes2.remera5": 3, "costumes2.gorra1": 12}}), encoding="utf-8")
    return Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec,
                  indice=IndicePiezas(tmp_path / "sin_indice.json"), comportamientos=Comportamientos(tmp_path / "comportamientos.json"),
                  fondos=Fondos(tmp_path / "fondos.json"), cuadros=cuadros)


def test_lista_los_objetos_que_sirven_de_fondo(nucleo):
    resultado = nucleo.fondos()

    assert resultado["ok"] and resultado["comportamiento"] == "painting"
    assert resultado["fondos"] == [
        {"ruta": "costumes2.gorra1", "clase": "gorra1", "swf": "costumes2", "cuadros": 12},
        {"ruta": "costumes2.remera5", "clase": "remera5", "swf": "costumes2", "cuadros": 3},
    ]


def test_muestra_los_cuadros_de_un_objeto(nucleo, cuadros):
    resultado = nucleo.cuadros_de_fondo("costumes2.remera5")

    assert resultado["ok"] and len(resultado["cuadros"]) == 3
    assert cuadros.pedidos == [("costumes2", "remera5")]
    assert not nucleo.cuadros_de_fondo('x"y')["ok"]


def test_convertir_un_fondo_con_su_cuadro(nucleo, ffdec):
    resultado = nucleo.convertir_en_npcs([{"base": "costumes2.remera5", "comportamiento": "painting", "cuadro": 2}])

    assert resultado["ok"], resultado
    assert '{"behavior":"painting","monitorAttributes":false,"frame":2}' in resultado["script"] and ffdec.trucos == []
    malo = nucleo.convertir_en_npcs([{"base": "costumes2.gorra1", "comportamiento": "painting", "cuadro": 0}])
    assert not malo["ok"] and "cuadro" in malo["error"]


def test_mis_fondos_se_guardan_con_su_cuadro(nucleo, tmp_path):
    fondo = {"nombre": "Playa", "base": "costumes2.remera5", "comportamiento": "painting", "cuadro": 2}

    guardado = nucleo.guardar_npc("fondo", fondo)
    copia = nucleo.duplicar_npc("fondo", guardado["npc"]["id"])
    archivo = tmp_path / "playa.mgfondo"

    assert guardado["ok"] and guardado["npc"]["cuadro"] == 2
    assert copia["npc"]["cuadro"] == 2
    assert nucleo.npcs_guardados("tienda")["npcs"] == []  # cada tipo en su archivo
    assert "cuadro" in nucleo.guardar_npc("fondo", fondo | {"cuadro": None})["error"]
    assert nucleo.exportar_npc("fondo", fondo, str(archivo))["ok"]
    importado = nucleo.importar_npc_de_archivo("fondo", str(archivo))
    assert importado["ok"] and importado["npc"]["cuadro"] == 2
    assert "no es una tienda" in nucleo.importar_npc_de_archivo("tienda", str(archivo))["error"]


def test_el_mismo_objeto_llega_varias_veces_cada_una_con_su_cuadro(nucleo, ffdec):
    resultado = nucleo.convertir_en_npcs([
        {"base": "costumes2.remera5", "comportamiento": "painting", "cuadro": 2},
        {"base": "costumes2.remera5", "comportamiento": "painting", "cuadro": 3, "cantidad": 2},
    ])

    assert resultado["ok"], resultado
    script = decodificar(resultado["encode"])
    # Cada cuadro con su nombre: el inventario junta por nombre, y el juego ignora lo que sigue a un segundo punto.
    assert 'inventory.addOptions costumes2.remera5.cuadro2 1 null {"behavior":"painting","monitorAttributes":false,"frame":2}' in script
    assert 'inventory.addOptions costumes2.remera5.cuadro3 2 null {"behavior":"painting","monitorAttributes":false,"frame":3}' in script
    assert resultado["items"] == [{"ruta": "costumes2.remera5.cuadro2", "cantidad": 1}, {"ruta": "costumes2.remera5.cuadro3", "cantidad": 2}]
    assert ffdec.trucos == []  # sin trucar ningún SWF: los atributos van en el Encode
    assert not nucleo.tiene_swf_trucado(resultado["encode"])


@pytest.mark.parametrize("pedidos, error", [
    ([], "al menos uno"),
    ([{"base": "costumes2.remera5", "comportamiento": "painting", "cuadro": "2"}], "cuadro"),
    ([{"base": "costumes2.remera5", "comportamiento": "painting", "cuadro": 2}] * 2, "dos veces"),
    ([{"base": "costumes2.noEsUnItem", "comportamiento": "painting", "cuadro": 2}], "no es un Item"),
    ([{"base": "costumes2.remera5", "comportamiento": "painting", "cuadro": 2, "cantidad": 0}], "cantidad"),
])
def test_lo_que_no_se_puede_entregar_como_fondo(nucleo, pedidos, error):
    resultado = nucleo.convertir_en_npcs(pedidos)

    assert not resultado["ok"] and error in resultado["error"], resultado

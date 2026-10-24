import re
import xml.etree.ElementTree as ET

import pytest

from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_iconos import ExportadorFalso, SinJava
from test_prendas import CLASES, COSTUMES

SVG = "{http://www.w3.org/2000/svg}"


@pytest.fixture
def exportador():
    return ExportadorFalso()


@pytest.fixture
def fuente():
    return FuenteFalsa({"clothes1": crear_swf(CLASES), "costumes": COSTUMES})


@pytest.fixture
def nucleo(tmp_path, fuente, exportador):
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=exportador)


def piezas_dibujadas(svg: str) -> dict[str, list[str]]:
    """Parte del cuerpo → transformaciones de cada copia dibujada (el SVG tiene que ser válido)."""
    raiz = ET.fromstring(svg)
    dibujadas = {}
    for g in raiz.iter(f"{SVG}g"):
        if "data-parte" in g.attrib:
            dibujadas.setdefault(g.attrib["data-parte"], []).append(g.attrib["transform"])
    return dibujadas


def test_el_gaturro_con_piezas_de_varios_swf(nucleo):
    resultado = nucleo.gaturro({"hats": "costumes.coronaRey_on", "cloth": "clothes1.remera5_on", "arm": "clothes1.remera5_brazo_on"})

    assert resultado["ok"], resultado
    assert resultado["sin_imagen"] == []
    dibujadas = piezas_dibujadas(resultado["svg"])
    assert set(dibujadas) == {"hats", "cloth", "arm"}
    assert len(dibujadas["arm"]) == 2 and "scale(-1,1)" in dibujadas["arm"][1]  # el otro brazo, reflejado
    assert 'data-clase="coronaRey_on"' in resultado["svg"] and 'data-clase="remera5_on"' in resultado["svg"]


def test_cada_pieza_se_pone_en_el_anclaje_de_su_parte(nucleo):
    svg = nucleo.gaturro({"hats": "costumes.coronaRey_on", "cloth": "clothes1.remera5_on"})["svg"]

    dibujadas = piezas_dibujadas(svg)
    assert dibujadas["cloth"] == ["translate(0,0)"]
    assert dibujadas["hats"] != dibujadas["cloth"]
    # Sin el corrimiento con el que FFDec centra la imagen: el anclaje de la Pieza queda en el de la Parte.
    assert "matrix(1.0, 0.0, 0.0, 1.0, 15.0, 12.5)" not in svg


def test_los_ids_de_cada_pieza_no_se_pisan(nucleo):
    svg = nucleo.gaturro({"hats": "costumes.coronaRey_on", "cloth": "clothes1.remera5_on"})["svg"]

    ids = re.findall(r'\bid="([^"]+)"', svg)
    assert len(ids) == len(set(ids)) == 4
    for referencia in re.findall(r'(?:href="#|url\(#)([^")]+)', svg):
        assert referencia in ids


def test_las_imagenes_se_exportan_una_vez_por_version_del_swf(nucleo, exportador, fuente, tmp_path):
    nucleo.gaturro({"cloth": "clothes1.remera5_on"})
    nucleo.gaturro({"cloth": "clothes1.buzo1_on", "arm": "clothes1.buzo1_brazo_on"})

    assert len(exportador.llamadas) == 1
    assert set(exportador.llamadas[0].values()) == {
        "buzo1_brazo_on", "buzo1_on", "capa1_on", "gorra1_on", "remera5_brazo_on", "remera5_on",
    }  # solo las Piezas del SWF

    fuente.publicar("clothes1", crear_swf(CLASES + ["nueva_on"]), '"v2"')
    otro = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=exportador)
    otro.gaturro({"cloth": "clothes1.remera5_on"})

    assert len(exportador.llamadas) == 2


def test_una_pieza_sin_imagen_no_rompe_el_resto(nucleo):
    resultado = nucleo.gaturro({"hats": "costumes.noExiste_on", "cloth": "clothes1.remera5_on",
                                "foot": "noHay.bota_on", "leg": "mal escrita"})

    assert resultado["ok"]
    assert set(piezas_dibujadas(resultado["svg"])) == {"cloth"}
    assert sorted(resultado["sin_imagen"]) == ["costumes.noExiste_on", "mal escrita", "noHay.bota_on"]


def test_sin_piezas_se_ve_el_gaturro_solo(nucleo, exportador):
    resultado = nucleo.gaturro({})

    assert resultado["ok"]
    assert piezas_dibujadas(resultado["svg"]) == {}
    assert "<ellipse" in resultado["svg"]
    assert exportador.llamadas == []


def test_partes_que_el_gaturro_no_tiene_se_ignoran(nucleo):
    assert piezas_dibujadas(nucleo.gaturro({"capeExtra": "clothes1.capa1_on"})["svg"]) == {}


def test_color_del_pelaje(nucleo):
    assert "#3366cc" in nucleo.gaturro({}, "#3366cc")["svg"]
    assert "javascript" not in nucleo.gaturro({}, '"/><script>javascript')["svg"]


def test_partes_con_forma_invalida(nucleo):
    assert not nucleo.gaturro(["hats"])["ok"]


def test_sin_java_devuelve_error(tmp_path, fuente):
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=SinJava())

    resultado = nucleo.gaturro({"cloth": "clothes1.remera5_on"})

    assert not resultado["ok"]
    assert "Java" in resultado["error"]

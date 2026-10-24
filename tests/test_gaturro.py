import re
import xml.etree.ElementTree as ET

import pytest

from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_iconos import ExportadorFalso, SinJava, svg_como_ffdec
from test_prendas import CLASES, COSTUMES

SVG = "{http://www.w3.org/2000/svg}"

# Como exporta FFDec el primer cuadro de assets.GaturroMC: cada clip con su nombre de instancia como id;
# los huecos son clips vacíos (tamaño 0).
CUERPO = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns:ffdec="https://www.free-decompiler.com/flash" xmlns:xlink="http://www.w3.org/1999/xlink" ffdec:objectType="frame" height="100.0px" width="80.0px" xmlns="http://www.w3.org/2000/svg">
  <g transform="matrix(1.0, 0.0, 0.0, 1.0, 40.0, 90.0)">
    <use ffdec:characterId="20" height="20.0" id="belly" transform="matrix(-0.8075, 0.0, 0.0, 0.8075, -2.65, -22.45)" width="20.0" xlink:href="#sprite1"/>
    <use ffdec:characterId="22" height="20.0" id="arm1" transform="matrix(-0.8075, 0.0, 0.0, 0.8075, -12.0, -25.85)" width="20.0" xlink:href="#sprite2"/>
    <use ffdec:characterId="30" height="40.0" id="head" transform="matrix(1.0, 0.0, 0.0, 1.0, 0.0, -50.0)" width="60.0" xlink:href="#sprite3"/>
  </g>
  <defs>
    <g id="sprite0"/>
    <g id="sprite1">
      <use ffdec:characterId="5" height="10.0" id="color2" transform="matrix(1.0, 0.0, 0.0, 1.0, -5.0, -5.0)" width="10.0" xlink:href="#shape0"/>
      <use ffdec:characterId="2" height="0.0" id="cloth" transform="matrix(1.0, 0.0, 0.0, 0.7654, -1.55, 1.1)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="clothBack" transform="matrix(1.0, 0.0, 0.0, 1.0, 0.0, 2.0)" width="0.0" xlink:href="#sprite0"/>
    </g>
    <g id="sprite2">
      <use ffdec:characterId="2" height="0.0" id="armFore" transform="matrix(1.0, 0.0, 0.0, 0.7654, -0.35, 0.05)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="armBack" transform="matrix(1.0, 0.0, 0.0, 1.0, 1.0, 1.0)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="gripFore" transform="matrix(1.0, 0.0, 0.0, 1.0, 3.0, 9.0)" width="0.0" xlink:href="#sprite0"/>
    </g>
    <g id="sprite3">
      <use ffdec:characterId="6" height="40.0" id="color1" transform="matrix(1.0, 0.0, 0.0, 1.0, -30.0, -20.0)" width="60.0" xlink:href="#shape0"/>
      <use ffdec:characterId="7" height="8.0" id="colorEye" transform="matrix(1.0, 0.0, 0.0, 1.0, -4.0, -4.0)" width="8.0" xlink:href="#shape0"/>
      <use ffdec:characterId="8" height="12.0" id="orejas" transform="matrix(1.0, 0.0, 0.0, 1.0, -20.0, -30.0)" width="40.0" xlink:href="#shape0"/>
      <use ffdec:characterId="2" height="0.0" id="hats" transform="matrix(1.0, 0.0, 0.0, 1.0, -2.25, -1.8)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="hairs" transform="matrix(1.0, 0.0, 0.0, 1.0, 0.0, -3.0)" width="0.0" xlink:href="#sprite0"/>
    </g>
    <g id="shape0">
      <path d="M0.0 0.0 L10.0 0.0 10.0 10.0 0.0 10.0 Z" fill="#ffcc00"/>
    </g>
  </defs>
</svg>
'''

# Una Pieza que trae su propio clip de color (el juego también la pinta).
PIEZA_CON_COLOR = svg_como_ffdec("buzo1_on").replace(
    '<use ffdec:characterId="7"',
    '<use ffdec:characterId="9" height="5.0" id="color1" transform="matrix(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)" width="5.0" xlink:href="#shape0"/>\n    <use ffdec:characterId="7"')


class ExportadorConGaturro(ExportadorFalso):
    def exportar(self, swf, simbolos, destino, formato="png"):
        super().exportar(swf, simbolos, destino, formato)
        if formato == "svg" and "assets.GaturroMC" in simbolos.values():
            (destino / "assets.GaturroMC.svg").write_text(CUERPO, encoding="utf-8")
        if formato == "svg" and "buzo1_on" in simbolos.values():
            (destino / "buzo1_on.svg").write_text(PIEZA_CON_COLOR, encoding="utf-8")


@pytest.fixture
def exportador():
    return ExportadorConGaturro()


def fuente_con(*swf_cuerpo):
    swfs = {"clothes1": crear_swf(CLASES + ["hide_gorro_on"]), "costumes": COSTUMES}
    swfs |= {nombre: crear_swf(["assets.GaturroMC", "otraCosa"]) for nombre in swf_cuerpo}
    return FuenteFalsa(swfs)


@pytest.fixture
def fuente():
    return fuente_con("fashion_nuevo")


@pytest.fixture
def nucleo(tmp_path, fuente, exportador):
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=exportador)


def raiz(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # tiene que ser un SVG válido


def puestas(svg: str) -> dict[str, list[str]]:
    """Parte del cuerpo → transformación de cada hueco donde quedó su Pieza."""
    resultado = {}
    for g in raiz(svg).iter(f"{SVG}g"):
        if "data-parte" in g.attrib:
            resultado.setdefault(g.attrib["data-parte"], []).append(g.attrib.get("transform"))
    return resultado


def por_id(svg: str, id_: str) -> list[ET.Element]:
    return [e for e in raiz(svg).iter() if e.attrib.get("id") == id_]


def colores(svg: str) -> dict[str, str]:
    return {f.attrib["id"]: f.find(f"{SVG}feFlood").attrib["flood-color"] for f in raiz(svg).iter(f"{SVG}filter")}


# --- El cuerpo original ---

def test_el_gaturro_es_el_original_del_juego(nucleo, fuente):
    resultado = nucleo.gaturro({})

    assert resultado["ok"], resultado
    assert por_id(resultado["svg"], "head") and por_id(resultado["svg"], "belly")
    assert "fashion_nuevo" in fuente.descargas


def test_si_falta_un_swf_con_el_gaturro_se_usa_el_otro(tmp_path, exportador):
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente_con("superHeroesTrajes"), catalogo=[], exportador=exportador)

    assert nucleo.gaturro({})["ok"]


def test_sin_el_gaturro_original_no_se_muestra_ninguno(tmp_path, exportador):
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente_con(), catalogo=[], exportador=exportador)

    resultado = nucleo.gaturro({"cloth": "clothes1.remera5_on"})

    assert not resultado["ok"]
    assert resultado["sin_gaturro"]
    assert "svg" not in resultado


def test_el_cuerpo_y_las_piezas_se_exportan_una_vez_por_version(nucleo, exportador):
    nucleo.gaturro({"cloth": "clothes1.remera5_on"})
    nucleo.gaturro({"cloth": "clothes1.buzo1_on", "hats": "clothes1.gorra1_on"})

    exportadas = [set(llamada.values()) for llamada in exportador.llamadas]
    assert exportadas[0] == {"assets.GaturroMC"}  # solo el cuerpo de ese SWF
    assert "remera5_on" in exportadas[1] and "remera5" not in exportadas[1]  # solo las Piezas
    assert len(exportador.llamadas) == 2


# --- Las Piezas, como las pone el juego ---

def test_cada_pieza_va_en_su_hueco_con_la_transformacion_del_hueco(nucleo):
    svg = nucleo.gaturro({"hats": "costumes.coronaRey_on", "cloth": "clothes1.remera5_on"})["svg"]

    assert puestas(svg) == {
        "hats": ["matrix(1.0, 0.0, 0.0, 1.0, -2.25, -1.8)"],
        "cloth": ["matrix(1.0, 0.0, 0.0, 0.7654, -1.55, 1.1)"],  # el Torso no va en clothBack
    }
    # Sin el corrimiento con el que FFDec centra la imagen de la Pieza.
    assert "matrix(1.0, 0.0, 0.0, 1.0, 15.0, 12.5)" not in svg


def test_una_parte_va_en_sus_huecos_fore_y_back(nucleo):
    svg = nucleo.gaturro({"arm": "clothes1.remera5_brazo_on", "clothBack": "clothes1.capa1_on"})["svg"]

    assert puestas(svg) == {
        "arm": ["matrix(1.0, 0.0, 0.0, 0.7654, -0.35, 0.05)", "matrix(1.0, 0.0, 0.0, 1.0, 1.0, 1.0)"],
        "clothBack": ["matrix(1.0, 0.0, 0.0, 1.0, 0.0, 2.0)"],
    }


def test_si_dos_partes_van_al_mismo_hueco_gana_la_mas_especifica(nucleo):
    svg = nucleo.gaturro({"gripFore": "clothes1.gorra1_on", "grip": "clothes1.remera5_on"})["svg"]

    assert puestas(svg) == {"gripFore": ["matrix(1.0, 0.0, 0.0, 1.0, 3.0, 9.0)"]}


def test_los_ids_de_cada_pieza_no_se_pisan(nucleo):
    svg = nucleo.gaturro({"hats": "costumes.coronaRey_on", "cloth": "clothes1.remera5_on"})["svg"]

    de_piezas = [e.attrib["id"] for e in raiz(svg).iter() if re.match(r"p\d+_", e.attrib.get("id", ""))]
    assert len(de_piezas) == len(set(de_piezas)) == 4
    todos = {e.attrib["id"] for e in raiz(svg).iter() if "id" in e.attrib}
    for referencia in re.findall(r'(?:href="#|url\(#)([^")]+)', svg):
        assert referencia in todos


def test_una_pieza_hide_esconde_las_partes_del_cuerpo_de_su_lugar(nucleo):
    svg = nucleo.gaturro({"hats": "clothes1.hide_gorro_on"})["svg"]

    assert por_id(svg, "orejas")[0].attrib.get("visibility") == "hidden"
    assert por_id(svg, "color1")[0].attrib.get("visibility") == "hidden"
    assert "visibility" not in por_id(svg, "hairs")[0].attrib  # los huecos no se esconden
    assert "visibility" not in por_id(svg, "belly")[0].attrib  # ni lo que está en otro lugar


def test_una_pieza_comun_no_esconde_nada(nucleo):
    assert 'visibility="hidden"' not in nucleo.gaturro({"hats": "clothes1.gorra1_on"})["svg"]


# --- Colores ---

def test_los_colores_de_fabrica_del_juego(nucleo):
    svg = nucleo.gaturro({})["svg"]

    assert por_id(svg, "color1")[0].attrib["filter"] == "url(#mg-color1)"
    assert por_id(svg, "color2")[0].attrib["filter"] == "url(#mg-color2)"
    assert por_id(svg, "colorEye")[0].attrib["filter"] == "url(#mg-colorEye)"
    assert colores(svg) == {"mg-color1": "#FFF200", "mg-color2": "#DDB42D", "mg-colorEye": "#FFFFFF"}


def test_los_colores_del_jugador(nucleo):
    svg = nucleo.gaturro({}, {"color1": "#3366cc", "color3": "#000000", "color2": '"/><script>'})["svg"]

    assert colores(svg) == {"mg-color1": "#3366cc", "mg-color2": "#DDB42D", "mg-colorEye": "#000000"}
    assert "<script" not in svg


def test_los_clips_de_color_de_las_piezas_tambien_se_pintan(nucleo):
    svg = nucleo.gaturro({"cloth": "clothes1.buzo1_on"})["svg"]

    pintados = [e for e in raiz(svg).iter() if e.attrib.get("filter") == "url(#mg-color1)"]
    assert len(pintados) == 2  # el de la cabeza y el de la Pieza


# --- Lo que no se puede dibujar ---

def test_una_pieza_sin_imagen_no_rompe_el_resto(nucleo):
    resultado = nucleo.gaturro({"hats": "costumes.noExiste_on", "cloth": "clothes1.remera5_on",
                                "foot": "noHay.bota_on", "leg": "mal escrita"})

    assert resultado["ok"]
    assert set(puestas(resultado["svg"])) == {"cloth"}
    assert sorted(resultado["sin_imagen"]) == ["costumes.noExiste_on", "mal escrita", "noHay.bota_on"]


def test_partes_donde_el_juego_no_pone_nada(nucleo):
    resultado = nucleo.gaturro({"accesories2": "clothes1.gorra1_on", "capeExtra": "clothes1.capa1_on"})

    assert puestas(resultado["svg"]) == {}
    assert sorted(resultado["sin_lugar"]) == ["clothes1.capa1_on", "clothes1.gorra1_on"]


def test_partes_con_forma_invalida(nucleo):
    assert not nucleo.gaturro(["hats"])["ok"]
    assert not nucleo.gaturro({}, ["#ffffff"])["ok"]


def test_sin_java_devuelve_error(tmp_path, fuente):
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=SinJava())

    resultado = nucleo.gaturro({"cloth": "clothes1.remera5_on"})

    assert not resultado["ok"]
    assert "Java" in resultado["error"]

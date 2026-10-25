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
                                "hairs": "noHay.bota_on", "clothBack": "mal escrita"})

    assert resultado["ok"]
    assert set(puestas(resultado["svg"])) == {"cloth"}
    assert sorted(resultado["sin_imagen"]) == ["costumes.noExiste_on", "mal escrita", "noHay.bota_on"]


def test_partes_donde_este_gaturro_no_tiene_lugar(nucleo):
    resultado = nucleo.gaturro({"capeExtra": "clothes1.capa1_on", "gloveFore": "clothes1.gorra1_on"})

    assert puestas(resultado["svg"]) == {}
    assert sorted(resultado["sin_lugar"]) == ["clothes1.capa1_on", "clothes1.gorra1_on"]


# --- Versión del Gaturro ---

def test_el_gaturro_publicado_es_una_version_anterior_y_se_avisa(nucleo):
    resultado = nucleo.gaturro({"accesories2": "clothes1.gorra1_on"})

    assert "versión anterior" in resultado["aviso"]
    assert resultado["sin_lugar"] == ["clothes1.gorra1_on"]  # no tiene lugar para «Accesorio 2»


def test_con_un_gaturro_actual_no_hay_aviso_y_accesorio_2_se_ve(tmp_path, fuente):
    class ConGaturroActual(ExportadorConGaturro):
        def exportar(self, swf, simbolos, destino, formato="png"):
            super().exportar(swf, simbolos, destino, formato)
            cuerpo = destino / "assets.GaturroMC.svg"
            if cuerpo.exists():
                cuerpo.write_text(CUERPO.replace(
                    '<use ffdec:characterId="2" height="0.0" id="hats"',
                    '<use ffdec:characterId="2" height="0.0" id="accesories2" transform="matrix(1.0, 0.0, 0.0, 1.0, 1.0, -6.0)" width="0.0" xlink:href="#sprite0"/>\n      '
                    '<use ffdec:characterId="2" height="0.0" id="hats"'), encoding="utf-8")

    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=ConGaturroActual())
    resultado = nucleo.gaturro({"accesories2": "clothes1.gorra1_on"})

    assert resultado["aviso"] is None
    assert puestas(resultado["svg"]) == {"accesories2": ["matrix(1.0, 0.0, 0.0, 1.0, 1.0, -6.0)"]}


def test_partes_con_forma_invalida(nucleo):
    assert not nucleo.gaturro(["hats"])["ok"]
    assert not nucleo.gaturro({}, ["#ffffff"])["ok"]


def test_sin_java_devuelve_error(tmp_path, fuente):
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=SinJava())

    resultado = nucleo.gaturro({"cloth": "clothes1.remera5_on"})

    assert not resultado["ok"]
    assert "Java" in resultado["error"]


def test_el_gaturro_publicado_no_tiene_color_de_nariz(nucleo):
    resultado = nucleo.gaturro({})

    assert resultado["color_de_nariz"] is False
    assert resultado["colores_de_fabrica"] == {"color1": "#FFF200", "color2": "#DDB42D", "color3": "#FFFFFF"}


def test_un_gaturro_con_otra_zona_de_color_tiene_color_de_nariz(tmp_path, fuente):
    class ConNariz(ExportadorConGaturro):
        def exportar(self, swf, simbolos, destino, formato="png"):
            super().exportar(swf, simbolos, destino, formato)
            cuerpo = destino / "assets.GaturroMC.svg"
            if cuerpo.exists():
                cuerpo.write_text(CUERPO.replace('id="orejas"', 'id="colorNose"'), encoding="utf-8")

    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=ConNariz())

    assert nucleo.gaturro({})["color_de_nariz"] is True


# --- Espalda: el hueco de la plantilla de 2025 (fashion2025.maniqui_so) ---

# El Gaturro publicado no tiene `clothBack`; el torso del maniquí de 2025 sí (y `clothFront`).
CUERPO_SIN_ESPALDA = re.sub(r'\s*<use [^>]*id="clothBack"[^>]*/>', "", CUERPO)
PLANTILLA = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns:ffdec="https://www.free-decompiler.com/flash" xmlns:xlink="http://www.w3.org/1999/xlink" ffdec:objectType="frame" height="120.0px" width="80.0px" xmlns="http://www.w3.org/2000/svg">
  <g transform="matrix(1.0, 0.0, 0.0, 1.0, 40.0, 110.0)">
    <use ffdec:characterId="52" height="20.0" id="belly" transform="matrix(-0.807, 0.0, 0.0, 0.807, -2.15, -45.7)" width="20.0" xlink:href="#sprite1"/>
  </g>
  <defs>
    <g id="sprite0"/>
    <g id="sprite1">
      <use ffdec:characterId="2" height="0.0" id="clothBack" transform="matrix(1.0, 0.0, 0.0, 1.0, -1.55, 1.15)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="51" height="15.0" transform="matrix(1.0, 0.0, 0.0, 1.0, -8.0, -7.0)" width="15.0" xlink:href="#shape0"/>
      <use ffdec:characterId="2" height="0.0" id="cloth" transform="matrix(1.0, 0.0, 0.0, 0.7676, -1.55, 1.1)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="clothFront" transform="matrix(1.0, 0.0, 0.0, 1.0, -1.55, 1.05)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="neck" transform="matrix(1.0, 0.0, 0.0, 0.7676, -1.55, -3.65)" width="0.0" xlink:href="#sprite0"/>
    </g>
    <g id="shape0"><path d="M0.0 0.0 L10.0 10.0" fill="#cccccc"/></g>
  </defs>
</svg>
'''


class ExportadorConPlantilla(ExportadorConGaturro):
    def exportar(self, swf, simbolos, destino, formato="png"):
        super().exportar(swf, simbolos, destino, formato)
        if formato == "svg" and "assets.GaturroMC" in simbolos.values():
            (destino / "assets.GaturroMC.svg").write_text(CUERPO_SIN_ESPALDA, encoding="utf-8")
        if formato == "svg" and "maniqui_so" in simbolos.values():
            (destino / "maniqui_so.svg").write_text(PLANTILLA, encoding="utf-8")


def nucleo_espalda(tmp_path, con_plantilla=True):
    fuente = fuente_con("fashion_nuevo")
    if con_plantilla:
        fuente.publicar("fashion2025", crear_swf(["maniqui_so", "otraCosa_so"]), '"v1"')
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=ExportadorConPlantilla())


def hijos_del_torso(svg: str) -> list[str]:
    torso = next(g for g in raiz(svg).iter(f"{SVG}g") if any(h.attrib.get("data-parte") == "cloth" or h.attrib.get("id") == "cloth" for h in g))
    return [h.attrib.get("data-parte") or h.attrib.get("id") or "·" for h in torso]


def test_la_espalda_va_donde_la_pone_la_plantilla_de_2025(tmp_path):
    resultado = nucleo_espalda(tmp_path).gaturro({"clothBack": "clothes1.capa1_on", "cloth": "clothes1.remera5_on"})

    assert resultado["ok"], resultado
    assert resultado["sin_lugar"] == []
    assert puestas(resultado["svg"])["clothBack"] == ["matrix(1.0, 0.0, 0.0, 1.0, -1.55, 1.15)"]
    # Detrás de todo el torso, como en la plantilla; clothFront, justo delante del Torso; y lo que falte
    # del torso de la plantilla (acá, el Cuello), en su capa.
    assert hijos_del_torso(resultado["svg"]) == ["clothBack", "color2", "cloth", "clothFront", "neck"]


def test_del_maniqui_solo_se_copian_los_huecos(tmp_path):
    svg = nucleo_espalda(tmp_path).gaturro({})["svg"]

    assert "#cccccc" not in svg  # el dibujo del maniquí no se copia


def test_sin_la_plantilla_la_espalda_no_se_dibuja(tmp_path):
    resultado = nucleo_espalda(tmp_path, con_plantilla=False).gaturro({"clothBack": "clothes1.capa1_on"})

    assert resultado["ok"]
    assert resultado["sin_lugar"] == ["clothes1.capa1_on"]


# --- Hipótesis de la nariz y «Accesorio 2» (a confirmar en el juego) ---

# Una cabeza con la forma de la publicada: … eye2 … hairs accesories <nariz sin nombre> hats.
CABEZA_PUBLICADA = '''    <g id="sprite3">
      <use ffdec:characterId="6" height="40.0" id="color1" transform="matrix(1.0, 0.0, 0.0, 1.0, -30.0, -20.0)" width="60.0" xlink:href="#shape0"/>
      <use ffdec:characterId="2" height="0.0" id="mouths" transform="matrix(1.0, 0.0, 0.0, 1.0, -2.8, 28.8)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="56" height="8.0" id="eye1" transform="matrix(1.0, 0.0, 0.0, 1.0, -21.75, -9.9)" width="8.0" xlink:href="#shape0"/>
      <use ffdec:characterId="60" height="8.0" id="eye2" transform="matrix(1.0, 0.0, 0.0, 1.0, 17.0, -9.45)" width="8.0" xlink:href="#shape0"/>
      <use ffdec:characterId="2" height="0.0" id="hairs" transform="matrix(1.0, 0.0, 0.0, 1.0, -4.1, -7.2)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="2" height="0.0" id="accesories" transform="matrix(1.0, 0.0, 0.0, 1.0, -4.5, 14.65)" width="0.0" xlink:href="#sprite0"/>
      <use ffdec:characterId="62" height="6.0" transform="matrix(1.0, 0.0, 0.0, 1.0, -2.95, 17.9)" width="9.0" xlink:href="#shape0"/>
      <use ffdec:characterId="2" height="0.0" id="hats" transform="matrix(1.0, 0.0, 0.0, 1.0, -2.25, -1.8)" width="0.0" xlink:href="#sprite0"/>
    </g>
'''
CUERPO_CABEZA_PUBLICADA = re.sub(r'    <g id="sprite3">.*?</g>\n', lambda _: CABEZA_PUBLICADA, CUERPO, count=1, flags=re.S)


class ExportadorCabezaPublicada(ExportadorConGaturro):
    def exportar(self, swf, simbolos, destino, formato="png"):
        super().exportar(swf, simbolos, destino, formato)
        if formato == "svg" and "assets.GaturroMC" in simbolos.values():
            (destino / "assets.GaturroMC.svg").write_text(CUERPO_CABEZA_PUBLICADA, encoding="utf-8")


def hijos_de_la_cabeza(svg: str) -> list[str]:
    cabeza = next(g for g in raiz(svg).iter(f"{SVG}g")
                  if any(h.attrib.get("id") == "eye2" for h in g))
    return [h.attrib.get("data-parte") or h.attrib.get("id") or "nariz" for h in cabeza]


def test_la_nariz_va_debajo_del_pelo_como_en_la_cabeza_del_album_2018(tmp_path, fuente):
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=ExportadorCabezaPublicada())

    resultado = nucleo.gaturro({"hairs": "clothes1.remera5_on", "accesories2": "clothes1.gorra1_on"})

    assert resultado["ok"], resultado
    # Ojos, nariz, Boca, Pelo (lo que va en Pelo tapa la nariz); «Accesorio 2» arriba de Accesorio.
    assert hijos_de_la_cabeza(resultado["svg"]) == ["color1", "eye1", "eye2", "nariz", "mouths", "hairs", "accesories", "accesories2", "hats"]
    # En el mismo lugar que Accesorio (las Piezas de nariz están dibujadas para ese hueco).
    assert puestas(resultado["svg"])["accesories2"] == ["matrix(1.0, 0.0, 0.0, 1.0, -4.5, 14.65)"]
    assert resultado["sin_lugar"] == []
    # Sigue siendo la versión anterior: el hueco lo agregó el programa.
    assert "versión anterior" in resultado["aviso"]


def test_sin_la_forma_conocida_la_cabeza_no_se_toca(nucleo):
    resultado = nucleo.gaturro({})

    assert por_id(resultado["svg"], "hairs") and "nariz" not in resultado["svg"]

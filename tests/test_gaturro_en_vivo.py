"""El Gaturro en vivo: lo que el núcleo le dice que se ponga, y el servidor local que le da sus archivos."""
import urllib.error
import urllib.request

import pytest

from mgitems import servidor
from mgitems.gaturro import COLORES
from mgitems.nucleo import Nucleo
from mgitems.servidor import ServidorDelGaturro
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_gaturro import fuente_con


@pytest.fixture
def nucleo(tmp_path):
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente_con(), catalogo=[])


def test_los_atributos_traen_todas_las_partes_del_cuerpo_aunque_esten_vacias(nucleo):
    resultado = nucleo.gaturro_en_vivo({"cloth": "clothes1.remera5_on"})

    assert resultado["ok"], resultado
    atributos = resultado["atributos"]
    assert atributos["cloth"] == "clothes1.remera5_on"
    # Vacías: así se saca lo que tenía puesto.
    assert atributos["hats"] == atributos["accesories2"] == atributos["transport"] == atributos["effect"] == ""
    assert atributos["action"] == ""


def test_los_colores_van_como_enteros_y_los_que_faltan_son_los_de_fabrica(nucleo):
    atributos = nucleo.gaturro_en_vivo({}, {"color1": "#3366FF", "color2": "no es un color"})["atributos"]

    assert atributos["color1"] == 0x3366FF
    assert atributos["color2"] == int(COLORES["color2"][1:], 16)
    assert atributos["color3"] == 0xFFFFFF and atributos["color4"] == 0xFB8CBB


def test_la_emocion_es_la_del_look_o_la_normal(nucleo):
    assert nucleo.gaturro_en_vivo({}, None, "angry")["atributos"]["emote"] == "angry"
    assert nucleo.gaturro_en_vivo({})["atributos"]["emote"] == "normal"
    assert nucleo.gaturro_en_vivo({}, None, "inventada")["atributos"]["emote"] == "normal"


def test_el_transporte_y_el_efecto_de_cabeza_van_como_en_el_juego(nucleo):
    atributos = nucleo.gaturro_en_vivo({"effect": "clothes1.remera5_on", "transport": "clothes1.buzo1_on"})["atributos"]

    assert atributos["effect"] == "head.clothes1.remera5_on"
    assert atributos["transport"] == "clothes1.buzo1_on"


def test_la_accion_es_la_animacion_con_su_pieza(nucleo):
    con_pieza = nucleo.gaturro_en_vivo({"action": "clothes1.remera5_on"}, None, None, "showObject")["atributos"]
    sola = nucleo.gaturro_en_vivo({}, None, None, "dance")["atributos"]
    sin_animacion = nucleo.gaturro_en_vivo({"action": "clothes1.remera5_on"})["atributos"]

    assert con_pieza["action"] == "showObject.clothes1.remera5_on"
    assert sola["action"] == "dance"
    assert sin_animacion["action"] == ""
    assert nucleo.gaturro_en_vivo({}, None, None, "no vale")["atributos"]["action"] == ""


def test_avisa_lo_que_el_juego_no_dibuja(nucleo):
    resultado = nucleo.gaturro_en_vivo({"transport": "clothes1.remera5_on"})  # en Transporte solo se ven vehículos

    assert [n["ruta"] for n in resultado["no_se_ven"]] == ["clothes1.remera5_on"]


def test_las_partes_tienen_que_tener_la_forma_esperada(nucleo):
    assert not nucleo.gaturro_en_vivo(["cloth"])["ok"]


# --- El servidor local ---

@pytest.fixture
def pagina(nucleo):
    servidor_local = ServidorDelGaturro(nucleo.swf_del_juego)
    yield servidor_local.iniciar()
    servidor_local.detener()


def bajar(pagina: str, ruta: str) -> bytes:
    with urllib.request.urlopen(pagina.rsplit("/", 1)[0] + ruta, timeout=10) as respuesta:
        return respuesta.read()


def test_sirve_la_pagina_del_gaturro(pagina):
    with urllib.request.urlopen(pagina, timeout=10) as respuesta:
        assert b"mgVestir" in respuesta.read()


def test_le_da_al_gaturro_el_swf_de_cada_pieza(pagina, nucleo):
    assert bajar(pagina, "/assets/clothes1.swf") == nucleo.swf_del_juego("clothes1")


def test_sirve_ruffle_y_el_gaturro_de_vendor(pagina, tmp_path, monkeypatch):
    (tmp_path / "ruffle").mkdir()
    (tmp_path / "ruffle" / "ruffle.js").write_bytes(b"ruffle")
    (tmp_path / "gaturro").mkdir()
    (tmp_path / "gaturro" / "gaturro.swf").write_bytes(b"FWS")
    monkeypatch.setattr(servidor, "carpeta_vendor", lambda: tmp_path)

    assert bajar(pagina, "/ruffle/ruffle.js") == b"ruffle"
    assert bajar(pagina, "/gaturro.swf?v=1") == b"FWS"


@pytest.mark.parametrize("ruta", ["/assets/noExiste.swf", "/ruffle/../gaturro/gaturro.swf", "/index.html", "/assets/..%2Fx.swf"])
def test_lo_demas_no_existe(pagina, ruta):
    with pytest.raises(urllib.error.HTTPError) as error:
        bajar(pagina, ruta)
    assert error.value.code == 404


# --- El banner del editor de Piezas ---

def test_el_servidor_le_da_al_editor_su_banner():
    servidor_local = ServidorDelGaturro(lambda swf: None, lambda nombre: b"CWS-banner" if nombre == "CustomClothBanner" else None)
    pagina = servidor_local.iniciar()
    try:
        assert bajar(pagina, "/banners/CustomClothBanner.swf?33294") == b"CWS-banner"
        with pytest.raises(urllib.error.HTTPError):
            bajar(pagina, "/banners/OtroBanner.swf")
    finally:
        servidor_local.detener()


def test_el_nucleo_solo_da_el_banner_del_editor(tmp_path):
    banner = crear_swf(["CustomClothBanner", "EditorModalMC"])
    fuente = fuente_con()
    fuente.publicar("banners/CustomClothBanner", banner, '"v1"')
    fuente.publicar("banners/AvatarSaverBanner", crear_swf(["AvatarSaverBanner"]), '"v1"')
    nucleo = Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[])

    assert nucleo.banner_del_juego("CustomClothBanner") == banner  # tal cual: el juego verifica su firma
    assert nucleo.banner_del_juego("AvatarSaverBanner") is None

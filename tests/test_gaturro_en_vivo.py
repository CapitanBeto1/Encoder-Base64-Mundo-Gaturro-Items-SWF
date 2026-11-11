"""El Gaturro en vivo: lo que el núcleo le dice que se ponga, y el servidor local que le da sus archivos."""
import urllib.error
import urllib.request

import pytest

from mgitems import servidor
from mgitems.gaturro import COLORES
from mgitems.nucleo import Nucleo
from mgitems.servidor import ServidorDelGaturro
from sistema_falso import SistemaFalso
from test_gaturro import fuente_con


@pytest.fixture
def nucleo(tmp_path):
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente_con(), catalogo=[])


def test_se_viste_con_todas_las_partes_del_cuerpo_aunque_esten_vacias(nucleo):
    resultado = nucleo.gaturro_en_vivo({"cloth": "clothes1.remera5_on"})

    assert resultado["ok"], resultado
    partes = resultado["vestir"]["partes"]
    assert partes["cloth"] == "clothes1.remera5_on"
    assert partes["hats"] == "" and partes["accesories2"] == ""  # vacías: así se saca lo que tenía puesto
    assert "transport" not in partes and "effect" not in partes


def test_los_colores_van_como_enteros_y_los_que_faltan_son_los_de_fabrica(nucleo):
    vestir = nucleo.gaturro_en_vivo({}, {"color1": "#3366FF", "color2": "no es un color"})["vestir"]

    assert vestir["colores"]["color1"] == 0x3366FF
    assert vestir["colores"]["color2"] == int(COLORES["color2"][1:], 16)
    assert set(vestir["colores"]) == set(COLORES)


def test_la_emocion_es_la_del_look_o_la_normal(nucleo):
    assert nucleo.gaturro_en_vivo({}, None, "angry")["vestir"]["emote"] == "angry"
    assert nucleo.gaturro_en_vivo({})["vestir"]["emote"] == "normal"
    assert nucleo.gaturro_en_vivo({}, None, "inventada")["vestir"]["emote"] == "normal"


def test_el_transporte_y_el_efecto_de_cabeza_no_tienen_lugar(nucleo):
    resultado = nucleo.gaturro_en_vivo({"effect": "clothes1.remera5_on", "cloth": "clothes1.buzo1_on"})

    assert resultado["sin_lugar"] == ["clothes1.remera5_on"]
    assert resultado["vestir"]["partes"]["cloth"] == "clothes1.buzo1_on"


def test_lo_que_el_juego_no_dibuja_no_se_pone(nucleo):
    resultado = nucleo.gaturro_en_vivo({"transport": "clothes1.remera5_on"})  # en Transporte solo se ven vehículos

    assert [n["ruta"] for n in resultado["no_se_ven"]] == ["clothes1.remera5_on"]
    assert resultado["sin_lugar"] == []


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
    (tmp_path / "gaturro" / "preview.swf").write_bytes(b"FWS")
    monkeypatch.setattr(servidor, "carpeta_vendor", lambda: tmp_path)

    assert bajar(pagina, "/ruffle/ruffle.js") == b"ruffle"
    assert bajar(pagina, "/preview.swf?v=1") == b"FWS"


@pytest.mark.parametrize("ruta", ["/assets/noExiste.swf", "/ruffle/../gaturro/preview.swf", "/index.html", "/assets/..%2Fx.swf"])
def test_lo_demas_no_existe(pagina, ruta):
    with pytest.raises(urllib.error.HTTPError) as error:
        bajar(pagina, ruta)
    assert error.value.code == 404

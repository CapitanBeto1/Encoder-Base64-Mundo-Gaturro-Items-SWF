import json

import pytest

from mgitems.categorias import IndicePiezas
from mgitems.iconos import version_de
from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_prendas import CLASES, COSTUMES, PrendasFalsas, codigo_prenda

CLOTHES1 = crear_swf(CLASES)


def indice(tmp_path, swfs: dict) -> IndicePiezas:
    archivo = tmp_path / "indice.json"
    archivo.write_text(json.dumps({"swfs": swfs}), encoding="utf-8")
    return IndicePiezas(archivo)


@pytest.fixture
def fuente():
    return FuenteFalsa({"clothes1": CLOTHES1, "costumes": COSTUMES})


@pytest.fixture
def ffdec():
    ffdec = PrendasFalsas()
    # Una Prenda de clothes1 que usa una Pieza propia en otra Parte y una de costumes.
    ffdec.codigo["buzo1"] = codigo_prenda("buzo1", {"cloth": "buzo1_on", "clothBack": "remera5_on", "hats": "costumes.coronaRey_on"})
    return ffdec


def nucleo_con(tmp_path, fuente, ffdec, swfs_indice: dict, catalogo=()) -> Nucleo:
    return Nucleo(SistemaFalso(tmp_path / "sistema"), fuente=fuente, catalogo=list(catalogo),
                  prendas_ffdec=ffdec, indice=indice(tmp_path, swfs_indice))


def por_ruta(resultado) -> dict:
    return {p["ruta"]: p for p in resultado["piezas"]}


def test_del_indice_sin_descargar_ni_analizar(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {
        "costumes": {"version": "otra", "piezas": {"coronaRey_on": ["hats"], "capaRey_on": ["clothBack"], "raro_on": []}},
    })

    resultado = nucleo.piezas_de_swfs(["costumes"])

    assert resultado["ok"], resultado
    assert por_ruta(resultado)["costumes.coronaRey_on"] == {
        "ruta": "costumes.coronaRey_on", "clase": "coronaRey_on", "swf": "costumes", "partes": ["hats"]}
    assert por_ruta(resultado)["costumes.raro_on"]["partes"] == []  # "Otros"
    assert fuente.descargas == [] and ffdec.analisis == 0


def test_un_swf_fuera_del_indice_se_analiza_y_se_recuerda(tmp_path, fuente, ffdec):
    resultado = nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs(["clothes1"])

    assert resultado["ok"], resultado
    piezas = por_ruta(resultado)
    assert piezas["clothes1.remera5_on"]["partes"] == ["cloth", "clothBack"]  # el juego la usa en dos Partes
    assert piezas["clothes1.gorra1_on"]["partes"] == ["hats"]
    assert piezas["clothes1.capa1_on"]["partes"] == ["capeExtra"]
    assert "clothes1.coronaRey_on" not in piezas  # es de costumes
    assert ffdec.analisis == 1

    otra_vez = nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs(["clothes1"])

    assert otra_vez["piezas"] == resultado["piezas"]
    assert ffdec.analisis == 1  # se recordó


def test_una_copia_de_otra_version_que_el_indice_se_analiza(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"clothes1": {"version": "vieja", "piezas": {"remera5_on": ["leg"]}}})
    nucleo.abrir_swf_del_cdn("clothes1")  # queda una copia descargada (de otra versión que la del índice)

    resultado = nucleo.piezas_de_swfs(["clothes1"])

    assert por_ruta(resultado)["clothes1.remera5_on"]["partes"] == ["cloth", "clothBack"]


def test_una_copia_de_la_misma_version_usa_el_indice(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"clothes1": {"version": version_de(CLOTHES1), "piezas": {"remera5_on": ["leg"]}}})
    nucleo.abrir_swf_del_cdn("clothes1")

    resultado = nucleo.piezas_de_swfs(["clothes1"])

    assert resultado["piezas"] == [{"ruta": "clothes1.remera5_on", "clase": "remera5_on", "swf": "clothes1", "partes": ["leg"]}]
    assert ffdec.analisis == 0


def test_todos_los_swf_del_indice_y_del_catalogo(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"costumes": {"version": "x", "piezas": {"coronaRey_on": ["hats"]}}},
                        catalogo=[{"swf": "clothes1", "items": 5}, {"swf": "costumes", "items": 1}])

    resultado = nucleo.piezas_de_swfs()

    assert {p["swf"] for p in resultado["piezas"]} == {"costumes", "clothes1"}


def test_el_orden_es_el_de_los_swf_pedidos(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {
        "costumes": {"version": "x", "piezas": {"coronaRey_on": ["hats"]}},
        "clothes1": {"version": "y", "piezas": {"gorra1_on": ["hats"]}},
    })

    assert [p["swf"] for p in nucleo.piezas_de_swfs(["clothes1", "costumes"])["piezas"]] == ["clothes1", "costumes"]


def test_un_swf_que_no_existe_no_impide_los_demas(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"costumes": {"version": "x", "piezas": {"coronaRey_on": ["hats"]}}})

    resultado = nucleo.piezas_de_swfs(["noExiste", "costumes", "../malo"])

    assert resultado["ok"]
    assert [p["ruta"] for p in resultado["piezas"]] == ["costumes.coronaRey_on"]
    assert set(resultado["errores"]) == {"noExiste", "../malo"}


def test_swfs_con_forma_invalida(tmp_path, fuente, ffdec):
    assert not nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs("clothes1")["ok"]

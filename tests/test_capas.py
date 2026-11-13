"""Las capas de «Configura tus accesorios»: hasta tres Piezas en Sombrero, Pelo, Accesorio, Boca y Cuello."""
import pytest

from mgitems.prendas import leer_item_base, parte_de_la_capa
from fuente_falsa import FuenteFalsa
from test_categorias import nucleo_con
from test_mochila import ffdec, fuente, nucleo, sistema  # noqa: F401 (fixtures)
from test_prendas import COSTUMES, PrendasFalsas

CAPAS = [f"{p}{n}" for p in ("hats", "hairs", "accesories", "mouths", "neck") for n in ("", "2", "3")]


def capas_vacias(**valores) -> dict:
    """Lo que devuelve la ventana del juego: todas las capas, vacías salvo `valores`."""
    return {parte: "" for parte in CAPAS} | valores


@pytest.mark.parametrize("parte, base", [("hats2", "hats"), ("neck3", "neck"), ("accesories2", "accesories"),
                                         ("hats", "hats"), ("cloth", "cloth"), ("leg2", "leg2")])
def test_la_parte_de_cada_capa(parte, base):
    assert parte_de_la_capa(parte) == base


def test_las_capas_son_partes_conocidas_y_dicen_de_que_parte_son(nucleo):
    partes = {p["id"]: p for p in nucleo.partes_del_cuerpo()["partes_del_cuerpo"]}

    assert partes["hats2"] == {"id": "hats2", "nombre": "Sombrero (capa 2)", "capa_de": "hats"}
    assert partes["accesories2"]["nombre"] == "Accesorio (capa 2)"
    assert "capa_de" not in partes["hats"]
    assert all(parte in partes for parte in CAPAS)


def test_el_gaturro_en_vivo_recibe_todas_las_capas(nucleo):
    atributos = nucleo.gaturro_en_vivo({"hats": "costumes.coronaRey_on", "hats3": "costumes2.buzo1_on"})["atributos"]

    assert atributos["hats3"] == "costumes2.buzo1_on"
    assert all(atributos[parte] == "" for parte in CAPAS if parte not in ("hats", "hats3"))  # las vacías, vacías


def test_la_grilla_de_las_capas_lleva_las_piezas_de_las_fuentes_en_su_pestana(tmp_path):
    nucleo = nucleo_con(tmp_path, FuenteFalsa({"costumes": COSTUMES}), PrendasFalsas(), {"costumes": {"version": "otra", "piezas": {
        "coronaRey_on": ["hats"], "capaRey_on": ["clothBack"], "raro_on": [], "barba_on": ["mouths", "hats"],
        "aro_on": ["accesories2"]}}})

    resultado = nucleo.para_personalizar({"hats": "costumes.coronaRey_on", "cloth": "costumes.capaRey_on"}, swfs=["costumes"])

    assert resultado["ok"], resultado
    # Como `CustomLayerBanner.getItemCategory`: la primera de Sombrero, Pelo, Accesorio, Boca, Cuello que usa.
    assert sorted(resultado["capas"], key=lambda c: c["ruta"]) == [
        {"ruta": "costumes.aro_on", "parte": "accesories"},
        {"ruta": "costumes.barba_on", "parte": "hats"},
        {"ruta": "costumes.coronaRey_on", "parte": "hats"},
    ]
    assert resultado["piezas"] == {"hats": "costumes.coronaRey_on", "cloth": "costumes.capaRey_on"}  # las del editor
    assert resultado["atributos"]["hats2"] == ""


def test_al_guardar_las_capas_cambian_las_piezas_y_la_personalizacion_sigue_a_la_suya(nucleo):
    partes = {"hats": "costumes.coronaRey_on", "hats2": "costumes2.buzo1_on", "cloth": "costumes2.remera5"}
    personalizacion = {"hats": {"ajuste": {"x": 0, "y": 0, "rot": 30, "escala": 10}}}
    # Subió la segunda (la ventana mueve el valor entero, con su personalización) y se agregó un cuello en la capa 3.
    valores = capas_vacias(hats="costumes2.buzo1_on", hats2="costumes.coronaRey_on//0,0,30,10", neck3="costumes.coronaRey_on")

    resultado = nucleo.capas_configuradas(partes, personalizacion, valores)

    assert resultado["ok"], resultado
    assert resultado["partes"] == {"hats": "costumes2.buzo1_on", "hats2": "costumes.coronaRey_on",
                                   "neck3": "costumes.coronaRey_on", "cloth": "costumes2.remera5"}
    assert resultado["personalizacion"] == {"hats2": {"ajuste": {"x": 0, "y": 0, "rot": 30, "escala": 10}}}


def test_una_capa_vaciada_sale_del_look_con_su_personalizacion(nucleo):
    resultado = nucleo.capas_configuradas({"hats": "costumes.coronaRey_on"}, {"hats": {"colores": [{"color": 255}]}},
                                          capas_vacias())

    assert resultado["partes"] == {} and resultado["personalizacion"] == {}


def test_lo_que_la_ventana_no_nombra_queda_como_estaba(nucleo):
    resultado = nucleo.capas_configuradas({"hats": "costumes.coronaRey_on", "effect": "costumes.coronaRey_on"}, None, {})

    assert resultado["partes"] == {"hats": "costumes.coronaRey_on", "effect": "costumes.coronaRey_on"}


def test_un_valor_roto_de_la_ventana_no_cambia_nada(nucleo):
    assert not nucleo.capas_configuradas({}, None, capas_vacias(hats="costumes.corona Rey"))["ok"]


def test_las_capas_llegan_al_juego_en_la_prenda(nucleo, ffdec):
    look = {"nombre": "Capas", "base": "costumes2.remera5",
            "partes": {"hats": "costumes.coronaRey_on", "hats2": "costumes2.buzo1_on"}}

    resultado = nucleo.aplicar_look(look)

    assert resultado["ok"], resultado
    # Al ponerse la Prenda, el juego le pone al avatar cada `wear_<parte>`, también `hats2` (ClothInventorySceneObject).
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"hats": "costumes.coronaRey_on", "hats2": "buzo1_on"}

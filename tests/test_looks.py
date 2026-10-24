import base64
import xml.etree.ElementTree as ET

import pytest

from mgitems.fuente import URL_ASSETS
from mgitems.nucleo import Nucleo
from mgitems.prendas import leer_prenda
from fuente_falsa import FuenteFalsa
from procesos_falso import ProcesosFalso
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_prendas import CLASES, COSTUMES, PrendasFalsas

REY = {
    "nombre": "Rey",
    "base": "clothes1.remera5",
    "partes": {
        "hats": "costumes.coronaRey_on",
        "cloth": "costumes.capaRey_on",
        "grip": "clothes1.gorra1_on",
        "foot": "clothes1.remera5_brazo_on",
    },
}


@pytest.fixture
def sistema(tmp_path):
    sistema = SistemaFalso(tmp_path)
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    return sistema


@pytest.fixture
def fuente():
    swf = crear_swf(CLASES)
    return FuenteFalsa({"clothes1": swf, "antro2017/wears": swf, "costumes": COSTUMES})


@pytest.fixture
def ffdec():
    return PrendasFalsas()


def nuevo_nucleo(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("clothes1")
    return nucleo


@pytest.fixture
def nucleo(sistema, fuente, ffdec):
    return nuevo_nucleo(sistema, fuente, ffdec)


# --- Guardar, listar, editar, duplicar, borrar ---

def test_ciclo_completo_de_un_look(nucleo, sistema, fuente, ffdec):
    guardado = nucleo.guardar_look(REY)
    assert guardado["ok"], guardado
    id_rey = guardado["look"]["id"]
    assert id_rey

    # Persiste: un programa nuevo lo ve.
    otro = nuevo_nucleo(sistema, fuente, ffdec)
    assert [l["nombre"] for l in otro.looks()["looks"]] == ["Rey"]
    assert otro.looks()["looks"][0]["partes"] == REY["partes"]

    # Editar: mismo id, se reemplaza.
    editado = dict(REY, id=id_rey, nombre="Rey Mago", partes={"hats": "costumes.coronaRey_on"})
    assert nucleo.guardar_look(editado)["ok"]
    assert [(l["id"], l["nombre"], l["partes"]) for l in nucleo.looks()["looks"]] == [
        (id_rey, "Rey Mago", {"hats": "costumes.coronaRey_on"}),
    ]

    # Duplicar: otro id y otro nombre.
    copia = nucleo.duplicar_look(id_rey)
    copia2 = nucleo.duplicar_look(id_rey)
    assert copia["look"]["nombre"] == "Rey Mago (copia)"
    assert copia2["look"]["nombre"] == "Rey Mago (copia 2)"
    assert len({id_rey, copia["look"]["id"], copia2["look"]["id"]}) == 3

    # Borrar.
    assert nucleo.borrar_look(copia["look"]["id"])["ok"]
    assert [l["nombre"] for l in nucleo.looks()["looks"]] == ["Rey Mago", "Rey Mago (copia 2)"]


def test_sin_looks_la_lista_esta_vacia(nucleo):
    assert nucleo.looks() == {"ok": True, "looks": []}


@pytest.mark.parametrize(
    "look, error",
    [
        (dict(REY, nombre="  "), "nombre"),
        (dict(REY, base="sinPunto"), "Prenda base"),
        (dict(REY, partes={"hats": "costumes.corona Rey_on"}), "no válida"),
        (dict(REY, partes={"sombrero de rey": "costumes.coronaRey_on"}), "no válida"),
        ("no es un look", "forma"),
    ],
)
def test_un_look_invalido_no_se_guarda(nucleo, look, error):
    resultado = nucleo.guardar_look(look)

    assert not resultado["ok"]
    assert error in resultado["error"]
    assert nucleo.looks()["looks"] == []


def test_borrar_o_duplicar_un_look_que_no_existe_devuelve_error(nucleo):
    assert not nucleo.borrar_look("noExiste")["ok"]
    assert not nucleo.duplicar_look("noExiste")["ok"]


def test_un_look_danado_en_el_archivo_no_impide_ver_los_demas(nucleo, sistema):
    nucleo.guardar_look(REY)
    archivo = sistema.base / "Roaming" / "MGItems" / "looks.json"
    archivo.write_text(archivo.read_text(encoding="utf-8").replace('"looks": [', '"looks": [{"nombre": ""},', 1), encoding="utf-8")

    assert [l["nombre"] for l in nucleo.looks()["looks"]] == ["Rey"]


def test_un_archivo_de_looks_ilegible_se_informa(nucleo, sistema):
    archivo = sistema.base / "Roaming" / "MGItems" / "looks.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text("{no es json", encoding="utf-8")

    resultado = nucleo.looks()

    assert not resultado["ok"]
    assert "Looks" in resultado["error"]


# --- Aplicar ---

def test_aplicar_un_look_truca_la_prenda_base_con_todas_sus_piezas(nucleo, ffdec):
    resultado = nucleo.aplicar_look(REY)

    assert resultado["ok"], resultado
    clase, fuente = ffdec.trucos[0]
    assert clase == "remera5"
    # Las del mismo SWF van sin prefijo; las de otro, con su SWF.
    assert leer_prenda(fuente).partes == {
        "hats": "costumes.coronaRey_on",
        "cloth": "costumes.capaRey_on",
        "grip": "gorra1_on",
        "foot": "remera5_brazo_on",
    }
    assert "inventory.add 1 clothes1.remera5\n" in base64.b64decode(resultado["encode"]).decode()
    assert resultado["look"] == {"nombre": "Rey", "base": "clothes1.remera5", "base_propuesta": False}


def test_aplicar_y_entregar_un_look_entrega_el_swf_de_la_prenda_base(nucleo, sistema):
    resultado = nucleo.aplicar_look(REY)

    assert nucleo.entregar_encode(resultado["encode"])["ok"]

    archivo = sistema.documentos / "Fiddler2" / "AutoResponder.xml"
    reglas = [r.get("Match") for r in ET.parse(archivo).getroot().find("State").findall("ResponseRule")]
    assert reglas[1] == f"EXACT:{URL_ASSETS}clothes1.swf?{len(crear_swf(CLASES))}"
    assert len(reglas) == 2


def test_la_prenda_base_puede_ser_de_un_swf_que_no_es_el_abierto(nucleo, ffdec):
    look = dict(REY, base="antro2017/wears.buzo1", partes={"hats": "costumes.coronaRey_on", "grip": "antro2017/wears.gorra1_on"})

    resultado = nucleo.aplicar_look(look)

    assert resultado["ok"], resultado
    assert resultado["prenda"]["ruta"] == "antro2017/wears.buzo1"
    assert leer_prenda(ffdec.trucos[0][1]).partes == {"hats": "costumes.coronaRey_on", "grip": "gorra1_on"}
    assert nucleo.piezas()["swf"] == "clothes1"  # el SWF abierto no cambia


def test_sin_prenda_base_se_propone_una_que_funcione(nucleo, ffdec):
    resultado = nucleo.aplicar_look({"nombre": "Sin base", "base": None, "partes": {"hats": "clothes1.gorra1_on"}})

    assert resultado["ok"], resultado
    assert resultado["look"]["base_propuesta"]
    assert resultado["look"]["base"] == "clothes1.buzo1"  # la primera Prenda del SWF de la Pieza
    assert ffdec.trucos[0][0] == "buzo1"


@pytest.mark.parametrize(
    "partes, error",
    [
        ({}, "al menos una Pieza"),
        ({"hats": "costumes.noExiste_on"}, "no es una Pieza de costumes"),
        ({"hats": "costumes.coronaRey"}, "no es una Pieza de costumes"),
        ({"hats": "noExiste.algo_on"}, "no existe"),
    ],
)
def test_un_look_que_no_se_puede_aplicar_se_avisa_antes_de_trucar(nucleo, ffdec, partes, error):
    resultado = nucleo.aplicar_look(dict(REY, partes=partes))

    assert not resultado["ok"]
    assert error in resultado["error"]
    assert ffdec.trucos == []


def test_aplicar_con_una_base_que_no_es_prenda_se_avisa(nucleo, ffdec):
    resultado = nucleo.aplicar_look(dict(REY, base="clothes1.silla"))

    assert not resultado["ok"]
    assert "no es una Prenda" in resultado["error"]


def test_las_partes_del_cuerpo_estan_sin_swf_abierto(sistema, ffdec):
    partes = Nucleo(sistema, catalogo=[], prendas_ffdec=ffdec).partes_del_cuerpo()["partes_del_cuerpo"]

    assert {"id": "hats", "nombre": "Sombrero"} in partes
    assert {"id": "grip", "nombre": "Mano"} in partes

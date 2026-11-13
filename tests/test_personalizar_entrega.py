"""La personalización de una Pieza (colores por forma y ajuste) llega al juego y se guarda con el Look."""
import base64
import json

import pytest

from mgitems.prendas import leer_item_base
from test_mochila import ffdec, fuente, nucleo, sistema  # noqa: F401 (fixtures)

ROJO_VERDE = {"colores": [{"color": 0xFF0000}, {"color": 0x00FF00}]}
GIRADA = {"ajuste": {"x": 10, "y": -8, "rot": 25, "escala": 7}}

LOOK = {
    "nombre": "Personalizado",
    "base": "costumes2.remera5",
    "partes": {"cloth": "costumes2.buzo1_on", "hats": "costumes.coronaRey_on"},
    "personalizacion": {"cloth": ROJO_VERDE, "hats": GIRADA},
}


def script_de(resultado) -> str:
    return base64.b64decode(resultado["encode"]).decode()


# --- Aplicar Look: va en el SWF trucado ---

def test_aplicar_look_escribe_la_personalizacion_en_la_prenda(nucleo, ffdec):
    resultado = nucleo.aplicar_look(LOOK)

    assert resultado["ok"], resultado
    # La del mismo SWF va sin él (el juego se lo agrega; la cola no tiene punto), la de otro, con él.
    assert leer_item_base(ffdec.trucos[0][1]).partes == {
        "cloth": "buzo1_on,16711680,65280",
        "hats": "costumes.coronaRey_on//10,-8,25,7",
    }


def test_en_un_item_de_mochila_la_pieza_va_con_su_swf_y_su_personalizacion(nucleo, ffdec):
    resultado = nucleo.aplicar_look(dict(LOOK, base="bruja.pocima1"))

    assert resultado["ok"], resultado
    fuente = ffdec.trucos[0][1]
    assert 'adds.cloth = "costumes2.buzo1_on,16711680,65280";' in fuente
    assert 'adds.hats = "costumes.coronaRey_on//10,-8,25,7";' in fuente


def test_sin_personalizacion_no_cambia_nada(nucleo, ffdec):
    nucleo.aplicar_look(dict(LOOK, personalizacion={}))

    assert leer_item_base(ffdec.trucos[0][1]).partes == {"cloth": "buzo1_on", "hats": "costumes.coronaRey_on"}


# --- Trucar Prenda: en el SWF trucado o, con «Persistir», en los atributos del Encode ---

TRUCADA = {"base": "costumes2.remera5", "parte": "grip", "pieza": "costumes.coronaRey_on",
           "personalizacion": {"colores": [{"quitar": True}, {"color": 0x0000FF, "opacidad": 5}], "ajuste": {"rot": 90}}}


def test_trucar_varias_lleva_la_personalizacion(nucleo, ffdec):
    resultado = nucleo.trucar_varias([TRUCADA])

    assert resultado["ok"], resultado
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"grip": "costumes.coronaRey_on,-3,255;5//0,0,90,10"}


def test_trucar_via_encode_guarda_la_personalizacion_en_wear(nucleo):
    resultado = nucleo.trucar_varias_via_encode([TRUCADA])

    assert resultado["ok"], resultado
    linea = next(l for l in script_de(resultado).splitlines() if "inventory.addOptions" in l)
    atributos = json.loads(linea.split(" null ", 1)[1])
    # Como guarda el juego su «Personalizar prenda»: el texto entero en `wear_<parte>`.
    assert atributos == {"wear_grip": "costumes.coronaRey_on,-3,255;5//0,0,90,10"}


def test_trucar_via_encode_sin_personalizacion(nucleo):
    resultado = nucleo.trucar_varias_via_encode([dict(TRUCADA, personalizacion=None)])

    assert '{"wear_grip":"costumes.coronaRey_on"}' in script_de(resultado)


@pytest.mark.parametrize("personalizacion", [
    "rojo", {"colores": "rojo"}, {"colores": [{"color": "rojo"}]}, {"colores": [{"color": 0x1000000}]},
    {"colores": [{"color": 255, "opacidad": 11}]}, {"ajuste": {"rot": "mucho"}}, {"ajuste": [1, 2]},
])
def test_una_personalizacion_rota_no_entrega_nada(nucleo, personalizacion):
    for entregar in (nucleo.trucar_varias, nucleo.trucar_varias_via_encode):
        resultado = entregar([dict(TRUCADA, personalizacion=personalizacion)])
        assert not resultado["ok"]


def test_en_el_transporte_y_el_efecto_no_se_aplica(nucleo, ffdec):
    """El juego no pinta formas del transporte ni busca el efecto de cabeza con colores: no se mandan."""
    look = dict(LOOK, partes={"effect": "costumes.coronaRey_on"}, personalizacion={"effect": ROJO_VERDE})

    nucleo.aplicar_look(look)

    assert leer_item_base(ffdec.trucos[0][1]).partes == {"effect": "head.costumes.coronaRey_on"}


def test_el_ajuste_solo_va_en_las_partes_que_el_juego_ajusta(nucleo, ffdec):
    look = dict(LOOK, partes={"foot": "costumes2.buzo1_on"}, personalizacion={"foot": dict(ROJO_VERDE, **GIRADA)})

    nucleo.aplicar_look(look)

    assert leer_item_base(ffdec.trucos[0][1]).partes == {"foot": "buzo1_on,16711680,65280"}  # sin el ajuste


# --- Vista previa ---

def test_la_vista_previa_dibuja_la_personalizacion(nucleo):
    resultado = nucleo.gaturro_en_vivo(LOOK["partes"], None, None, None, LOOK["personalizacion"])

    assert resultado["atributos"]["cloth"] == "costumes2.buzo1_on,16711680,65280"
    assert resultado["atributos"]["hats"] == "costumes.coronaRey_on//10,-8,25,7"


# --- Guardar e importar ---

def test_el_look_guardado_conserva_la_personalizacion(nucleo):
    guardado = nucleo.guardados.guardar("look", LOOK)["documento"]

    assert guardado["personalizacion"] == {"cloth": ROJO_VERDE, "hats": GIRADA}
    assert nucleo.guardados.lista("look")["guardados"][0]["personalizacion"] == guardado["personalizacion"]


def test_exportar_e_importar_conserva_la_personalizacion(nucleo, tmp_path):
    archivo = tmp_path / "Personalizado.mglook"
    nucleo.guardados.exportar("look", LOOK, str(archivo))

    assert nucleo.guardados.importar_de_archivo("look", str(archivo))["documento"]["personalizacion"] == {
        "cloth": ROJO_VERDE, "hats": GIRADA}


def test_la_personalizacion_de_una_pieza_que_ya_no_esta_se_descarta(nucleo):
    guardado = nucleo.guardados.guardar("look", dict(LOOK, partes={"cloth": "costumes2.buzo1_on"}))["documento"]

    assert guardado["personalizacion"] == {"cloth": ROJO_VERDE}


# --- El editor de Piezas del juego ---

def test_al_editor_van_las_piezas_personalizables_con_su_personalizacion(nucleo):
    partes = dict(LOOK["partes"], effect="costumes.coronaRey_on")
    resultado = nucleo.para_el_editor(partes, None, None, LOOK["personalizacion"])

    assert resultado["ok"], resultado
    # El efecto de cabeza no se personaliza; las demás van con su personalización, como las tendría el avatar.
    assert resultado["piezas"] == {"cloth": "costumes2.buzo1_on,16711680,65280", "hats": "costumes.coronaRey_on//10,-8,25,7"}
    assert resultado["atributos"]["effect"] == "head.costumes.coronaRey_on"


def test_lo_que_guarda_el_editor_es_la_personalizacion_del_look(nucleo):
    # Como lo escribe el juego: todas las formas, -1 (animada sin tocar), -2, la saturación con «;».
    valores = {"cloth": "costumes2.buzo1_on,16711680,-1,-2", "hats": "costumes.coronaRey_on,65253;5//0,0,40,7"}

    resultado = nucleo.personalizacion_del_editor(LOOK["partes"], valores, ["cloth", "hats"])

    assert resultado["ok"], resultado
    assert resultado["personalizacion"] == {
        "cloth": {"colores": [{"color": 0xFF0000}]},
        "hats": {"colores": [{"color": 65253, "opacidad": 5}], "ajuste": {"x": 0, "y": 0, "rot": 40, "escala": 7}},
    }
    assert resultado["quitadas"] == []


def test_lo_que_el_editor_corto_con_la_tijera_se_saca(nucleo):
    resultado = nucleo.personalizacion_del_editor(LOOK["partes"], {"cloth": "costumes2.buzo1_on"}, ["cloth", "hats"])

    assert resultado["quitadas"] == ["hats"]
    assert resultado["personalizacion"] == {}


def test_una_parte_que_el_editor_no_mostro_no_se_saca(nucleo):
    resultado = nucleo.personalizacion_del_editor(LOOK["partes"], {"cloth": "costumes2.buzo1_on"}, ["cloth"])

    assert resultado["quitadas"] == []


def test_la_saturacion_en_cero_vale(nucleo):
    resultado = nucleo.personalizacion_del_editor(LOOK["partes"], {"cloth": "costumes2.buzo1_on,255;0"}, ["cloth"])

    assert resultado["personalizacion"] == {"cloth": {"colores": [{"color": 255, "opacidad": 0}]}}


def test_un_valor_roto_del_editor_no_cambia_nada(nucleo):
    assert not nucleo.personalizacion_del_editor(LOOK["partes"], {"cloth": "costumes2.buzo1_on,rojo"}, ["cloth"])["ok"]

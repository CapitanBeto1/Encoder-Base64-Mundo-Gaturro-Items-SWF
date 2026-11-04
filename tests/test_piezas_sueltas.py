"""Piezas que ningún Item trae (como unicefClothes.remeraEscritor_on), recibidas vestibles sin trucar ningún SWF."""
import json

import pytest

from mgitems.categorias import IndicePiezas
from mgitems.nucleo import Nucleo
from mgitems.script import decodificar
from procesos_falso import ProcesosFalso
from test_prendas import sistema  # noqa: F401 (fixture)

INDICE = {"swfs": {
    "unicef": {"piezas": {"remeraEscritor_on": ["cloth"], "remeraEscritor_brazo_on": ["arm"], "zapatoEscritor_on": ["foot"],
                          "sinParte_on": []},
               "items": {"zapatoAladin": {"tipo": "prenda", "partes": ["foot"], "destino": "guardarropa"}}},
    "clothes1": {"items": {"remera5": {"tipo": "prenda", "partes": ["cloth", "arm"], "destino": "guardarropa"}}},
    "moda": {"items": {"traje": {"tipo": "prenda", "partes": ["cloth", "arm", "leg"], "destino": "guardarropa"},
                       "remera": {"tipo": "prenda", "partes": ["arm", "cloth"], "destino": "guardarropa"}}},
}}


@pytest.fixture
def nucleo(sistema, tmp_path):
    (tmp_path / "indice.json").write_text(json.dumps(INDICE), encoding="utf-8")
    return Nucleo(sistema, ProcesosFalso(), catalogo=[], indice=IndicePiezas(tmp_path / "indice.json"))


def test_la_remera_llega_en_una_prenda_que_viste_lo_mismo_con_su_manga(nucleo):
    resultado = nucleo.pieza_para_recibir("unicef.remeraEscritor_on")

    assert resultado["ok"], resultado
    item = resultado["item"]
    # No clothes1 (el servidor la vuelve a la original) ni el traje (vestiría también las piernas).
    assert item["base"] == "moda.remera"
    # El juego no acepta nombres con «_on»: la Pieza va en los atributos, y el nombre es el de la Prenda con un sufijo.
    assert item["ruta"] == "moda.remera.remeraEscritor"
    assert item["atributos"] == {"wear_cloth": "unicef.remeraEscritor_on", "wear_arm": "unicef.remeraEscritor_brazo_on"}


def test_primero_una_prenda_del_mismo_swf(nucleo):
    assert nucleo.pieza_para_recibir("unicef.zapatoEscritor_on")["item"]["base"] == "unicef.zapatoAladin"
    assert not nucleo.pieza_para_recibir("unicef.sinParte_on")["ok"]
    assert not nucleo.pieza_para_recibir('x"y')["ok"]


def test_el_encode_mezcla_items_comunes_y_con_atributos(nucleo):
    pieza = nucleo.pieza_para_recibir("unicef.remeraEscritor_on")["item"]

    resultado = nucleo.generar_encode([pieza, {"ruta": "clothes1.remera5", "cantidad": 2}])

    assert resultado["ok"], resultado
    script = decodificar(resultado["encode"])
    assert ('inventory.addOptions moda.remera.remeraEscritor 1 null '
            '{"wear_cloth":"unicef.remeraEscritor_on","wear_arm":"unicef.remeraEscritor_brazo_on"}') in script
    assert "inventory.add 2 clothes1.remera5" in script
    # Sin atributos, el Encode es el de siempre.
    assert "addOptions" not in decodificar(nucleo.generar_encode(["clothes1.remera5"])["encode"])


@pytest.mark.parametrize("item", [
    {"ruta": "moda.remera.x", "atributos": {"behavior": "brujaMesa"}},  # solo wear_*
    {"ruta": "moda.remera.x", "atributos": {"wear_cloth": "no es una ruta"}},
    {"ruta": "moda.remera.x y"},  # un nombre con sufijo solo con atributos
])
def test_atributos_que_no_se_aceptan(nucleo, item):
    assert not nucleo.generar_encode([item])["ok"]

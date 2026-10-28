import base64
import json
from pathlib import Path

import pytest

from mgitems.ffdec import FFDec, FFDecNoDisponible
from mgitems.fuente import FuenteCDN
from mgitems.nucleo import Nucleo
from mgitems.prendas import MOCHILA, USOS_ILIMITADOS, ItemsBaseFFDec, leer_item_base, reescribir_partes
from fuente_falsa import FuenteFalsa
from procesos_falso import ProcesosFalso
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_prendas import CLASES, COSTUMES, PrendasFalsas, reglas


def codigo_mochila(clase: str, padre: str, cuerpo: str, simbolo: str = "symbol7") -> str:
    """Código AS3 como el que exporta FFDec para un Item usable o consumible del juego."""
    return f'''package
{{
   [Embed(source="/_assets/assets.swf", symbol="{simbolo}")]
   public dynamic class {clase} extends {padre}
   {{

      public function {clase}()
      {{
         super();
         addFrameScript(0,this.frame1);
      }}

      internal function frame1() : *
      {{
{cuerpo}
      }}
   }}
}}
'''


# Como pocimaAchicadora de bruja: una animación al tomarla, un efecto, un solo uso y solo por la sesión.
POCIMA = codigo_mochila("pocima1", "ConsumableMamboAsset", '''         questItem = true;
         session = true;
         adds.action = "drink.bruja.pocima1_on";
         adds.effect = "scale.07";''')
JUGO = codigo_mochila("jugo1", "UsableMamboAsset", '''         adds = {"action":"drink.bruja.jugo1_on","effect":"dirty"};
         questItem = true;''')
BRUJA = crear_swf(["pocima1", "pocima1_on", "jugo1", "jugo1_on"])


@pytest.fixture
def sistema(tmp_path):
    sistema = SistemaFalso(tmp_path)
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    return sistema


@pytest.fixture
def ffdec():
    ffdec = PrendasFalsas()
    ffdec.codigo |= {"pocima1": POCIMA, "jugo1": JUGO}
    return ffdec


@pytest.fixture
def fuente():
    return FuenteFalsa({"bruja": BRUJA, "clothes1": crear_swf(CLASES), "costumes": COSTUMES})


@pytest.fixture
def nucleo(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("bruja")
    return nucleo


# --- Código AS3 ---

def test_leer_un_item_de_mochila():
    item = leer_item_base(POCIMA)

    assert item.clase == "pocima1"
    assert item.tipo == MOCHILA
    assert item.consumible
    assert item.partes == {"action": "drink.bruja.pocima1_on", "effect": "scale.07"}


def test_leer_un_usable_que_declara_adds_como_objeto():
    item = leer_item_base(JUGO)

    assert item.tipo == MOCHILA
    assert not item.consumible
    assert item.partes == {"action": "drink.bruja.jugo1_on", "effect": "dirty"}


def test_reescribir_un_consumible_solo_viste_con_usos_ilimitados():
    nuevo = reescribir_partes(leer_item_base(POCIMA), {"hats": "costumes.coronaRey_on", "grip": "bruja.pocima1_on"})

    item = leer_item_base(nuevo)
    assert item.partes == {"hats": "costumes.coronaRey_on", "grip": "bruja.pocima1_on"}  # sin animación ni efecto
    assert item.usos == USOS_ILIMITADOS
    assert "session" not in nuevo  # no dura solo la sesión
    assert "questItem = true;" in nuevo  # lo demás queda igual (y va a la mochila)
    assert 'symbol="symbol7"' in nuevo


def test_reescribir_un_usable_no_le_agrega_usos():
    nuevo = reescribir_partes(leer_item_base(JUGO), {"hats": "costumes.coronaRey_on"})

    assert leer_item_base(nuevo).partes == {"hats": "costumes.coronaRey_on"}
    assert "uses" not in nuevo


# --- En el núcleo ---

def test_los_items_de_mochila_se_ofrecen_como_base(nucleo):
    resultado = nucleo.prendas()

    assert resultado["ok"], resultado
    items = {p["clase"]: p for p in resultado["prendas"]}
    assert items["pocima1"]["tipo"] == "mochila"
    assert items["pocima1"]["partes"] == {}  # la animación y el efecto no son Partes del cuerpo
    assert items["jugo1"]["tipo"] == "mochila"


def test_trucar_un_item_de_mochila(nucleo, ffdec):
    resultado = nucleo.trucar_prenda("pocima1", "grip", "pocima1_on")

    assert resultado["ok"], resultado
    assert resultado["prenda"] == {"ruta": "bruja.pocima1", "tipo": "mochila", "partes": {"grip": "bruja.pocima1_on"}}
    assert "inventory.add 1 bruja.pocima1\n" in base64.b64decode(resultado["encode"]).decode()
    # Las Piezas del mismo SWF van con su nombre: se aplican tal cual al Gaturro.
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"grip": "bruja.pocima1_on"}


def test_un_look_en_un_item_de_mochila_de_otro_swf(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("clothes1")
    look = {"nombre": "Rey", "base": "bruja.pocima1",
            "partes": {"hats": "costumes.coronaRey_on", "cloth": "clothes1.remera5_on"}}

    resultado = nucleo.aplicar_look(look)

    assert resultado["ok"], resultado
    assert resultado["prenda"]["tipo"] == "mochila"
    item = leer_item_base(ffdec.trucos[0][1])
    assert item.partes == look["partes"]
    assert item.usos == USOS_ILIMITADOS
    assert nucleo.entregar_encode(resultado["encode"])["ok"]
    assert any(r["Match"].endswith(f"bruja.swf?{len(BRUJA)}") for r in reglas(sistema))


def test_un_look_con_una_pieza_en_la_cabeza_como_efecto(sistema, fuente, ffdec):
    # El efecto de cabeza («head.<swf>.<Pieza>», GaturroEffectsManager.applyHead): al usar el Item de
    # mochila, el juego pone la Pieza sobre la cabeza, aunque sea un vehículo.
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    look = {"nombre": "Corona arriba", "base": "bruja.pocima1", "partes": {"effect": "costumes.coronaRey_on"}}

    resultado = nucleo.aplicar_look(look)

    assert resultado["ok"], resultado
    item = leer_item_base(ffdec.trucos[0][1])
    assert item.partes == {"effect": "head.costumes.coronaRey_on"}
    assert item.usos == USOS_ILIMITADOS  # se usa de nuevo cada vez que se entra al juego


def test_la_base_propuesta_de_un_look_es_una_prenda(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("bruja")

    resultado = nucleo.aplicar_look({"nombre": "X", "partes": {"hats": "clothes1.gorra1_on"}})

    assert resultado["ok"], resultado
    assert resultado["look"]["base"] == "clothes1.buzo1"


def test_lo_guardado_antes_de_los_items_de_mochila_se_vuelve_a_leer(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("bruja")
    nucleo.prendas()
    guardado = next((sistema.base).rglob("bruja.json"))
    datos = json.loads(guardado.read_text(encoding="utf-8"))
    # Como lo guardaba la versión anterior: solo Prendas.
    guardado.write_text(json.dumps({"version": datos["version"], "prendas": {}}), encoding="utf-8")

    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("bruja")

    assert "pocima1" in {p["clase"] for p in nucleo.prendas()["prendas"]}
    assert ffdec.analisis == 2


# --- Con FFDec y el servidor del juego de verdad ---

def _hay_ffdec_y_red() -> bool:
    try:
        FFDec().programas()
        FuenteCDN().version("bruja")
    except (FFDecNoDisponible, OSError):
        return False
    return True


@pytest.mark.skipif(not _hay_ffdec_y_red(), reason="Hace falta Java, FFDec e internet")
def test_con_ffdec_real_una_pocima_viste_al_usarla(sistema):
    nucleo = Nucleo(sistema, ProcesosFalso(), catalogo=[])
    assert nucleo.abrir_swf_del_cdn("bruja")["ok"]
    assert {p["clase"]: p["tipo"] for p in nucleo.prendas()["prendas"]}["pocimaAchicadora"] == "mochila"

    resultado = nucleo.trucar_prenda("pocimaAchicadora", "hats", "costumes.coronaRey_on")

    assert resultado["ok"], resultado
    assert nucleo.entregar_encode(resultado["encode"])["ok"]
    trucado = Path(reglas(sistema)[1]["Action"]).read_bytes()
    item = ItemsBaseFFDec().analizar(trucado, ["pocimaAchicadora"])["pocimaAchicadora"]
    assert item.partes == {"hats": "costumes.coronaRey_on"}
    assert item.usos == USOS_ILIMITADOS


def test_items_base_de_cualquier_swf_sin_abrirlo(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("clothes1")

    resultado = nucleo.items_base("bruja")

    assert resultado["ok"], resultado
    assert [(i["clase"], i["tipo"]) for i in resultado["items"]] == [("jugo1", "mochila"), ("pocima1", "mochila")]
    assert resultado["items"][0]["ruta"] == "bruja.jugo1"
    assert nucleo.items_base("noExiste")["ok"] is False

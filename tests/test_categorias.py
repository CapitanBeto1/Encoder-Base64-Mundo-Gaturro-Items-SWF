import json

import pytest

from mgitems.categorias import IndicePiezas
from mgitems.iconos import version_de
from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_mochila import codigo_mochila
from test_prendas import CLASES, COSTUMES, PrendasFalsas, codigo_prenda

CLOTHES1 = crear_swf(CLASES)


def clase_con(clase: str, padre: str, cuerpo: str) -> str:
    """Código AS3 como el que exporta FFDec para un Item que no es Item base (transporte, casa, mascota)."""
    return f'''package
{{
   public dynamic class {clase} extends {padre}
   {{
      internal function frame1() : *
      {{
         {cuerpo}
      }}
   }}
}}
'''


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
        "ruta": "costumes.coronaRey_on", "clase": "coronaRey_on", "swf": "costumes", "partes": ["hats"], "uso": None}
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


def test_lo_que_viste_un_item_de_mochila_tiene_parte(tmp_path, ffdec):
    # Como una pócima que al tomarla te pone un sombrero: la animación al tomarla no viste.
    ffdec.codigo["pocima1"] = codigo_mochila("pocima1", "ConsumableMamboAsset", '''         adds.action = "drink.bruja.pocima1_on";
         adds.hats = "bruja.sombrero1_on";''')
    fuente = FuenteFalsa({"bruja": crear_swf(["pocima1", "pocima1_on", "sombrero1_on"])})

    piezas = por_ruta(nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs(["bruja"]))

    assert piezas["bruja.sombrero1_on"]["partes"] == ["hats"]
    assert piezas["bruja.pocima1_on"]["partes"] == []


def test_para_que_usa_el_juego_lo_que_no_viste(tmp_path, ffdec):
    ffdec.codigo |= {
        "pocima1": codigo_mochila("pocima1", "ConsumableMamboAsset", '         adds.action = "drink.varios.pocima1_on";'),
        "skate1": clase_con("skate1", "TransportMamboAsset", 'vehicle = "skate1_on";'),
        "pared1": clase_con("pared1", "HouseMamboAsset", ""),
        "perroPirata": clase_con("perroPirata", "PetClothMamboAsset", 'clothes = {"hats":"varios.perro_gorroPirata_on"};'),
    }
    fuente = FuenteFalsa({"varios": crear_swf([
        "pocima1", "pocima1_on", "skate1", "skate1_on", "pared1", "pared1_on", "perroPirata", "perro_gorroPirata_on", "raro_on"])})

    piezas = por_ruta(nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs(["varios"]))

    assert {ruta: (p["partes"], p["uso"]) for ruta, p in piezas.items()} == {
        "varios.pocima1_on": ([], "accion"),
        "varios.skate1_on": ([], "transporte"),
        "varios.pared1_on": ([], "casa"),
        "varios.perro_gorroPirata_on": ([], "mascota"),
        "varios.raro_on": ([], None),
    }


def test_el_uso_de_lo_que_no_viste_viene_del_indice(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"costumes": {
        "version": "x", "piezas": {"coronaRey_on": ["hats"], "capaRey_on": []}, "otros_usos": {"capaRey_on": "casa"}}})

    piezas = por_ruta(nucleo.piezas_de_swfs(["costumes"]))

    assert piezas["costumes.capaRey_on"]["uso"] == "casa"
    assert piezas["costumes.coronaRey_on"]["uso"] is None


def test_lo_clasificado_con_la_forma_anterior_se_vuelve_a_clasificar(tmp_path, fuente, ffdec):
    nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs(["clothes1"])
    [guardado] = (tmp_path / "sistema").rglob("categorias/clothes1.json")
    anterior = json.loads(guardado.read_text(encoding="utf-8"))
    guardado.write_text(json.dumps({"version": anterior["version"], "piezas": {"remera5_on": ["leg"]}}), encoding="utf-8")

    resultado = nucleo_con(tmp_path, fuente, ffdec, {}).piezas_de_swfs(["clothes1"])

    assert por_ruta(resultado)["clothes1.remera5_on"]["partes"] == ["cloth", "clothBack"]


def test_una_copia_de_otra_version_que_el_indice_se_analiza(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"clothes1": {"version": "vieja", "piezas": {"remera5_on": ["leg"]}}})
    nucleo.abrir_swf_del_cdn("clothes1")  # queda una copia descargada (de otra versión que la del índice)

    resultado = nucleo.piezas_de_swfs(["clothes1"])

    assert por_ruta(resultado)["clothes1.remera5_on"]["partes"] == ["cloth", "clothBack"]


def test_una_copia_de_la_misma_version_usa_el_indice(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"clothes1": {"version": version_de(CLOTHES1), "piezas": {"remera5_on": ["leg"]}}})
    nucleo.abrir_swf_del_cdn("clothes1")

    resultado = nucleo.piezas_de_swfs(["clothes1"])

    assert resultado["piezas"] == [{"ruta": "clothes1.remera5_on", "clase": "remera5_on", "swf": "clothes1", "partes": ["leg"], "uso": None}]
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


def test_los_items_de_un_swf_con_su_tipo(tmp_path, ffdec):
    ffdec.codigo |= {
        "pocima1": codigo_mochila("pocima1", "ConsumableMamboAsset", '         adds.hats = "varios.gorro1_on";'),
        "skate1": clase_con("skate1", "TransportMamboAsset", 'vehicle = "skate1_on";'),
        "silla1": clase_con("silla1", "HolderMamboAsset", ""),
        "perroPirata": clase_con("perroPirata", "PetClothMamboAsset", 'clothes = {"petType":"perro","hats":"varios.perro_gorroPirata_on"};'),
        "pez1": clase_con("pez1", "PetFoodMamboAsset", 'energy = 5; forPetType = "acuario";'),
        "pelota1": clase_con("pelota1", "PetToyMamboAsset", "love = 3;"),
        "dino1": clase_con("dino1", "OwnedNpcMamboAsset", 'nameOwnedNpc = "Dino";'),
        "remera5": codigo_prenda("remera5", {"cloth": "remera5_on", "arm": "remera5_brazo_on"}),
        "ClothMamboAsset": clase_con("ClothMamboAsset", "GrabbableMamboAsset", ""),  # la clase base que trae el SWF
    }
    fuente = FuenteFalsa({"varios": crear_swf([
        "pocima1", "skate1", "silla1", "perroPirata", "pez1", "pelota1", "dino1", "remera5", "remera5_on", "ClothMamboAsset", "evento1"])})

    resultado = nucleo_con(tmp_path, fuente, ffdec, {}).items_de_swfs(["varios"])

    assert resultado["ok"], resultado
    assert {i["ruta"]: (i["tipo"], i["partes"], i["mascota"]) for i in resultado["items"]} == {
        "varios.dino1": ("casa", [], None),  # no es una mascota válida del juego: no da una mascota
        "varios.pelota1": ("juguete_mascota", [], None),
        "varios.perroPirata": ("ropa_mascota", [], "perro"),
        "varios.pez1": ("comida_mascota", [], "acuario"),
        "varios.pocima1": ("mochila", [], None),
        "varios.remera5": ("prenda", ["arm", "cloth"], None),
        "varios.silla1": ("casa", [], None),
        "varios.skate1": ("transporte", [], None),
    }


def test_los_items_vienen_del_indice(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"costumes": {
        "version": "x", "piezas": {}, "items": {
            "coronaRey": {"tipo": "prenda", "partes": ["hats"], "destino": "guardarropa"},
            "trono": {"tipo": "casa", "destino": "casa"}}}})

    resultado = nucleo.items_de_swfs(["costumes"])

    assert resultado["items"] == [
        {"ruta": "costumes.coronaRey", "clase": "coronaRey", "swf": "costumes", "tipo": "prenda", "partes": ["hats"], "mascota": None,
         "destino": "guardarropa", "motivo": None, "parecido": []},
        {"ruta": "costumes.trono", "clase": "trono", "swf": "costumes", "tipo": "casa", "partes": [], "mascota": None,
         "destino": "casa", "motivo": None, "parecido": []},
    ]
    assert fuente.descargas == [] and ffdec.analisis == 0


def test_donde_llega_cada_item_al_juego(tmp_path, ffdec):
    ffdec.codigo |= {
        "remera5": codigo_prenda("remera5", {"cloth": "remera5_on"}),
        "skate1": clase_con("skate1", "TransportMamboAsset", 'vehicle = "skate1_on";'),
        "pocima1": codigo_mochila("pocima1", "ConsumableMamboAsset", '         adds.action = "drink.varios.pocima1_on";'),
        "pocimaSesion": codigo_mochila("pocimaSesion", "ConsumableMamboAsset", "         session = true;"),
        "pocimaAlas": clase_con("pocimaAlas", "TransportMamboAsset", 'questItem = true; session = true; vehicle = "pocimaAlas_on";'),
        "silla1": clase_con("silla1", "HolderMamboAsset", ""),
        "perroPirata": clase_con("perroPirata", "PetClothMamboAsset", 'clothes = {"petType":"perro","hats":"varios.perro_gorroPirata_on"};'),
        "premio_catalog": clase_con("premio_catalog", "HouseDecorationMamboAsset", ""),
    }
    fuente = FuenteFalsa({"varios": crear_swf(list(ffdec.codigo)), "pet": crear_swf(["koala", "koalaHouse"])})
    # Confirmado en el juego: la mascota dada directo llega a la casa como adorno; la mascota es su casita.
    ffdec.codigo["koala"] = clase_con("koala", "NpcMamboAsset", 'behavior = "pets";')
    ffdec.codigo["koalaHouse"] = clase_con("koalaHouse", "OwnedNpcMamboAsset", 'nameOwnedNpc = "pet.koala"; behaviorOwnedNpc = "pets";')

    resultado = nucleo_con(tmp_path, fuente, ffdec, {}).items_de_swfs(["varios"])

    destinos = {i["clase"]: i["destino"] for i in resultado["items"]}
    assert {c: destinos[c] for c in ["remera5", "skate1", "pocima1", "pocimaSesion", "pocimaAlas", "silla1", "perroPirata", "premio_catalog"]} == {
        "remera5": "guardarropa",
        "skate1": "guardarropa",
        "pocima1": "mochila",
        "pocimaSesion": "sesion",  # el juego no se lo pide al servidor: se borra al salir
        "pocimaAlas": "oculto",  # de misión: el guardarropa no muestra los Items de misión (confirmado en el juego)
        "silla1": "casa",
        "perroPirata": "pantalla_mascota",  # la mochila no muestra la ropa de mascota
        "premio_catalog": "descartado",  # exclusivo de catálogo
    }
    assert all(i["motivo"] for i in resultado["items"] if i["destino"] in ("sesion", "pantalla_mascota", "descartado"))
    mascotas = {i["clase"]: (i["tipo"], i["destino"]) for i in nucleo_con(tmp_path, fuente, ffdec, {}).items_de_swfs(["pet"])["items"]}
    assert mascotas == {"koala": ("casa", "casa"), "koalaHouse": ("mascota", "mascota")}


def test_el_encode_avisa_lo_que_no_va_a_llegar_bien(tmp_path, fuente, ffdec):
    nucleo = nucleo_con(tmp_path, fuente, ffdec, {"costumes": {"version": "x", "piezas": {}, "items": {
        "coronaRey": {"tipo": "prenda", "destino": "guardarropa"},
        "pocimaRey": {"tipo": "mochila", "destino": "sesion", "motivo": "es de sesión"}}}})

    resultado = nucleo.generar_encode(["costumes.coronaRey", "costumes.pocimaRey", "achievements.acc1"])

    assert resultado["ok"]
    assert [(a["ruta"], a["destino"]) for a in resultado["avisos"]] == [
        ("costumes.pocimaRey", "sesion"), ("achievements.acc1", "descartado")]


def test_las_prendas_rotas_avisan_por_que(tmp_path, ffdec):
    ffdec.codigo |= {
        "collar1": clase_con("collar1", "ClothMamboAsset", ""),  # no declara Piezas
        "gorroRaro": codigo_prenda("gorroRaro", {"hat": "gorroRaro_on"}),  # Parte que el Gaturro no tiene
    }
    fuente = FuenteFalsa({"varios": crear_swf(["collar1", "collar1_on", "gorroRaro", "gorroRaro_on"])})

    items = {i["clase"]: i for i in nucleo_con(tmp_path, fuente, ffdec, {}).items_de_swfs(["varios"])["items"]}

    assert items["collar1"]["destino"] == "mochila" and "no se puede poner" in items["collar1"]["motivo"]
    assert items["gorroRaro"]["destino"] == "guardarropa" and "«hat»" in items["gorroRaro"]["motivo"]

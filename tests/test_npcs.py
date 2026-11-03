"""Tiendas y portales: cualquier Item que, puesto en la casa, hace lo mismo que un NPC del juego."""
import base64
import json

import pytest

from mgitems.categorias import IndicePiezas
from mgitems.nucleo import Nucleo
from mgitems.npcs import Comportamientos, NoSePuedeConvertir, clase_npc, clasificar, comportamiento_en_codigo, describir, leer_npc
from mgitems.script import decodificar
from fuente_falsa import FuenteFalsa
from procesos_falso import ProcesosFalso
from swf_de_ejemplo import crear_swf
from test_prendas import CLASES, PrendasFalsas, sistema  # noqa: F401 (fixture)

# Guiones como los del juego (npc/<comportamiento>.npc).
TIENDA = """initial: DO
\ton activate openCatalog

openCatalog:DO
\tcatalog potions2024 #pocimas
\tafter 1 initial
"""
PORTAL = """initial: DO
\ton activate waitTransport

checkRoom: FORK darkPark | magicForest
\teq $(room.id) 2539743

darkPark: DO
\troom.change 43032 3,7

magicForest: DO
\troom.change 2539743 3,7
"""
MINIJUEGO = "initial: DO\n\ton activate jugar\n\njugar: DO\n\tminigame climbing\n"
BANNER = "initial: DO\n\ton activate openCatalog\n\nopenCatalog: DO\n\tmodal.banner bebesCatalogs\n"


def npc(guion: str) -> bytes:
    return base64.b64encode(guion.encode())


# --- Qué hace cada comportamiento ---

def test_clasifica_lo_que_hace_un_npc_segun_su_guion():
    assert clasificar(TIENDA) == {"tipo": "tienda", "catalogos": ["potions2024"], "salas": [], "juegos": []}
    assert clasificar(PORTAL) == {"tipo": "portal", "catalogos": [], "salas": [43032, 2539743], "juegos": []}
    assert clasificar(MINIJUEGO)["tipo"] == "minijuego"
    # Un estado que se llama «openCatalog» no es abrir un catálogo: este abre un banner.
    assert clasificar(BANNER)["tipo"] is None


def test_describe_lo_que_hace_un_npc():
    assert describir(clasificar(TIENDA)) == "Abre el catálogo potions2024"
    assert describir(clasificar(PORTAL)) == "Te lleva a 2 salas"
    assert describir(clasificar("x: DO\n\troom.change 43032 3,7\n"), {"43032": "BOSQUE EMBRUJADO"}) == \
        "Te lleva a la sala 43032 (BOSQUE EMBRUJADO)"
    assert describir(clasificar(MINIJUEGO)) == "Abre el minijuego climbing"


def test_lee_el_guion_en_base64_o_en_texto():
    assert leer_npc(npc(TIENDA)) == TIENDA
    assert leer_npc(TIENDA.encode()) == TIENDA


# --- La clase convertida ---

ORIGINAL = '''package
{
   [Embed(source="/_assets/assets.swf", symbol="symbol94")]
   public dynamic class gorroVietnamita extends ClothMamboAsset
   {
   }
}
'''


def test_la_clase_convertida_hereda_de_mambo_asset_y_escribe_el_comportamiento():
    codigo = clase_npc(ORIGINAL, "gorroVietnamita", "magia/portal")

    assert 'symbol="symbol94"' in codigo  # el mismo dibujo
    assert "class gorroVietnamita extends MamboAsset" in codigo  # la clase que traen todos los SWF
    assert comportamiento_en_codigo(codigo) == "magia/portal"


@pytest.mark.parametrize("fuente, clase, comportamiento", [
    (ORIGINAL, "gorroVietnamita", 'x"; hackear(); "'),
    (ORIGINAL, "gorro Vietnamita", "brujaMesa"),
    ("package { public class silla extends HouseMamboAsset {} }", "silla", "brujaMesa"),  # sin dibujo
])
def test_no_convierte_con_datos_invalidos(fuente, clase, comportamiento):
    with pytest.raises(NoSePuedeConvertir):
        clase_npc(fuente, clase, comportamiento)


# Un envoltorio de un dibujo (como socialNetBackgrounds): su SWF no trae MamboAsset y la clase hereda de MovieClip.
ENVOLTORIO = '''package
{
   import flash.display.MovieClip;

   [Embed(source="/_assets/assets.swf", symbol="symbol306")]
   public dynamic class SocialNetBackgrounds extends MovieClip
   {
   }
}
'''


def test_un_swf_sin_mambo_asset_hereda_de_su_base_con_un_attributes_propio():
    codigo = clase_npc(ENVOLTORIO, "SocialNetBackgrounds", "painting")

    assert 'symbol="symbol306"' in codigo  # el mismo dibujo (de varios cuadros)
    assert "extends MovieClip" in codigo and "MamboAsset" not in codigo  # no se puede heredar de la que el SWF no trae
    assert "import flash.display.MovieClip;" in codigo
    assert "public var attributes:Object;" in codigo and "attributes = {};" in codigo  # su propio attributes
    assert comportamiento_en_codigo(codigo) == "painting"


# --- El núcleo ---

CONOCIDOS = {
    "comportamientos": {
        "brujaMesa": clasificar(TIENDA) | {"objetos": []},
        "subteJapon": {"tipo": "portal", "catalogos": [], "salas": [51687540], "juegos": [], "objetos": ["virtualGoods.semaforo"]},
        "magia/portal": clasificar(PORTAL) | {"objetos": []},
    },
    "salas": {"51687540": "JAPÓN"},
}


@pytest.fixture
def fuente():
    swf = crear_swf(CLASES)
    fuente = FuenteFalsa({"costumes2": swf, "clothes1": swf})
    fuente.npcs = {"brujaMesa": npc(TIENDA), "escritoAMano": npc(MINIJUEGO), "unBanner": npc(BANNER)}
    return fuente


@pytest.fixture
def ffdec():
    return PrendasFalsas()


@pytest.fixture
def nucleo(sistema, fuente, ffdec, tmp_path):
    archivo = tmp_path / "comportamientos.json"
    archivo.write_text(json.dumps(CONOCIDOS), encoding="utf-8")
    return Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec,
                  indice=IndicePiezas(tmp_path / "sin_indice.json"), comportamientos=Comportamientos(archivo))


def test_lista_los_comportamientos_de_un_tipo(nucleo):
    portales = nucleo.comportamientos("portal")

    assert portales["ok"]
    assert portales["comportamientos"] == [
        {"comportamiento": "magia/portal", "tipo": "portal", "descripcion": "Te lleva a 2 salas", "objeto": None},
        {"comportamiento": "subteJapon", "tipo": "portal", "descripcion": "Te lleva a la sala 51687540 (JAPÓN)",
         "objeto": "virtualGoods.semaforo"},
    ]
    assert [c["comportamiento"] for c in nucleo.comportamientos("tienda")["comportamientos"]] == ["brujaMesa"]
    assert not nucleo.comportamientos("banner")["ok"]


def test_un_comportamiento_escrito_a_mano_se_lee_del_juego(nucleo, fuente):
    escrito = nucleo.comportamiento("escritoAMano")
    banner = nucleo.comportamiento("unBanner")

    assert escrito["ok"] and escrito["comportamiento"]["descripcion"] == "Abre el minijuego climbing"
    assert banner["ok"] and banner["comportamiento"]["tipo"] is None  # se puede usar igual
    assert "no tiene el comportamiento" in nucleo.comportamiento("noExiste")["error"]
    assert "no es un nombre" in nucleo.comportamiento('a"b')["error"]
    fuente.sin_conexion = True
    assert nucleo.comportamiento("escritoAMano")["ok"]  # ya leído: no hace falta volver a bajarlo


def test_convertir_cualquier_item_en_un_npc(nucleo, ffdec):
    resultado = nucleo.convertir_en_npcs([
        {"base": "costumes2.remera5", "comportamiento": "brujaMesa", "cantidad": 2},
        {"base": "costumes2.gorra1", "comportamiento": "magia/portal"},
    ])

    assert resultado["ok"], resultado
    assert decodificar(resultado["encode"]).count("inventory.add") == 2
    assert "inventory.add 2 costumes2.remera5" in resultado["script"]
    assert resultado["items"] == [{"ruta": "costumes2.remera5", "cantidad": 2}, {"ruta": "costumes2.gorra1", "cantidad": 1}]
    convertidas = dict(ffdec.trucos)
    assert comportamiento_en_codigo(convertidas["remera5"]) == "brujaMesa"
    assert "extends MamboAsset" in convertidas["gorra1"]
    assert nucleo.tiene_swf_trucado(resultado["encode"])  # las dos en el mismo SWF trucado


@pytest.mark.parametrize("pedidos, error", [
    ([], "al menos uno"),
    ([{"base": "costumes2.remera5", "comportamiento": "brujaMesa"}] * 2, "dos veces"),
    ([{"base": "costumes2.remera5", "comportamiento": "brujaMesa", "cantidad": 0}], "cantidad"),
    ([{"base": "costumes2.remera5", "comportamiento": "noExiste"}], "no tiene el comportamiento"),
    ([{"base": "costumes2.noEsUnItem", "comportamiento": "brujaMesa"}], "no es un Item"),
    ([{"base": "clothes1.remera5", "comportamiento": "brujaMesa"}], "no sirve de Item base"),
    ([{"base": "costumes2.silla", "comportamiento": "brujaMesa"}], "no tiene dibujo"),
])
def test_lo_que_no_se_puede_convertir(nucleo, ffdec, pedidos, error):
    resultado = nucleo.convertir_en_npcs(pedidos)

    assert not resultado["ok"] and error in resultado["error"], resultado
    assert ffdec.trucos == []


# --- Mis tiendas y Mis portales ---

TIENDA_GUARDADA = {"nombre": "Pociones en la remera", "base": "costumes2.remera5", "comportamiento": "brujaMesa"}


def test_guardar_duplicar_y_borrar_tiendas(nucleo):
    guardada = nucleo.guardar_npc("tienda", TIENDA_GUARDADA)

    assert guardada["ok"], guardada
    tienda = guardada["npc"]
    assert tienda["id"] and tienda["comportamiento"] == "brujaMesa"
    copia = nucleo.duplicar_npc("tienda", tienda["id"])["npc"]
    assert (copia["nombre"], copia["comportamiento"]) == ("Pociones en la remera (copia)", "brujaMesa")
    assert [t["nombre"] for t in nucleo.npcs_guardados("tienda")["npcs"]] == ["Pociones en la remera", "Pociones en la remera (copia)"]
    assert nucleo.npcs_guardados("portal")["npcs"] == []  # cada tipo en su archivo
    assert nucleo.borrar_npc("tienda", tienda["id"])["ok"]
    assert len(nucleo.npcs_guardados("tienda")["npcs"]) == 1


@pytest.mark.parametrize("npc_, error", [
    (TIENDA_GUARDADA | {"nombre": ""}, "nombre a la tienda"),
    (TIENDA_GUARDADA | {"base": None}, "Elegí el Item"),
    (TIENDA_GUARDADA | {"comportamiento": None}, "comportamiento"),
    (TIENDA_GUARDADA | {"comportamiento": 'x"y'}, "no es válido"),
    (TIENDA_GUARDADA | {"partes": {"hats": "costumes.coronaRey_on"}}, "no lleva Piezas"),
])
def test_una_tienda_que_no_se_puede_guardar(nucleo, npc_, error):
    resultado = nucleo.guardar_npc("tienda", npc_)

    assert not resultado["ok"] and error in resultado["error"]
    assert nucleo.npcs_guardados("tienda")["npcs"] == []


def test_exportar_e_importar_un_portal(nucleo, tmp_path):
    portal = {"nombre": "Al bosque", "base": "costumes2.gorra1", "comportamiento": "magia/portal"}
    archivo = tmp_path / "bosque.mgportal"

    assert nucleo.exportar_npc("portal", portal, str(archivo))["ok"]
    importado = nucleo.importar_npc_de_archivo("portal", str(archivo))

    assert importado["ok"], importado
    assert {k: importado["npc"][k] for k in portal} == portal
    assert "no es una tienda" in nucleo.importar_npc_de_archivo("tienda", str(archivo))["error"]
    assert nucleo.importar_npc_de_archivo("portal", str(archivo))["npc"]["nombre"] == "Al bosque (2)"
    assert not nucleo.npcs_guardados("banner")["ok"]  # solo tiendas, portales y minijuegos


def test_los_minijuegos_se_convierten_y_se_guardan_como_las_tiendas(nucleo, ffdec, tmp_path):
    escalada = {"nombre": "Escalar", "base": "costumes2.gorra1", "comportamiento": "escritoAMano"}

    convertido = nucleo.convertir_en_npcs([{"base": escalada["base"], "comportamiento": "escritoAMano"}])
    guardado = nucleo.guardar_npc("minijuego", escalada)
    archivo = tmp_path / "escalar.mgminijuego"

    assert convertido["ok"] and comportamiento_en_codigo(dict(ffdec.trucos)["gorra1"]) == "escritoAMano"
    assert guardado["ok"] and [m["nombre"] for m in nucleo.npcs_guardados("minijuego")["npcs"]] == ["Escalar"]
    assert nucleo.npcs_guardados("tienda")["npcs"] == []
    assert nucleo.exportar_npc("minijuego", escalada, str(archivo))["ok"]
    assert "no es un portal" in nucleo.importar_npc_de_archivo("portal", str(archivo))["error"]
    assert nucleo.importar_npc_de_archivo("minijuego", str(archivo))["npc"]["nombre"] == "Escalar (2)"


# --- Con FFDec y el servidor del juego de verdad ---

from test_prendas import _hay_ffdec_y_red, reglas  # noqa: E402


@pytest.mark.skipif(not _hay_ffdec_y_red(), reason="Hace falta Java, FFDec e internet")
def test_con_ffdec_real_una_prenda_y_un_objeto_de_la_casa_se_convierten_en_npc(sistema):
    # Probado en el juego: gorroVietnamita (una Prenda de un SWF sin NpcMamboAsset) como la tienda brujaMesa
    # y el semáforo de virtualGoods como el portal subteJapon. Llegan a la casa y siguen así al volver a entrar.
    from pathlib import Path
    from mgitems.prendas import ItemsBaseFFDec

    nucleo = Nucleo(sistema, ProcesosFalso(), catalogo=[])

    resultado = nucleo.convertir_en_npcs([
        {"base": "costumes2.gorroVietnamita", "comportamiento": "brujaMesa"},
        {"base": "virtualGoods.semaforo", "comportamiento": "subteJapon"},
    ])

    assert resultado["ok"], resultado
    assert nucleo.entregar_encode(resultado["encode"])["ok"]
    swf_trucados = {Path(r["Action"]).name: Path(r["Action"]).read_bytes() for r in reglas(sistema)[1:]}
    assert len(swf_trucados) == 2
    for clase, comportamiento in (("gorroVietnamita", "brujaMesa"), ("semaforo", "subteJapon")):
        codigo = next(c for data in swf_trucados.values() if (c := ItemsBaseFFDec().fuentes(data, [clase]).get(clase)))
        assert "extends MamboAsset" in codigo and comportamiento_en_codigo(codigo) == comportamiento


# --- Encontrados en las salas que se recorrieron (el caché del juego) ---

def cache_del_juego(sistema, *comportamientos):
    """Como el caché HTTP del juego: las direcciones de los guiones en un archivo de bloques."""
    cache = sistema.base / "Roaming" / "MundoGaturro" / "Cache"
    cache.mkdir(parents=True, exist_ok=True)
    claves = b"".join(b"\x00\x01_dk_https://cdn-ar.mundogaturro.com https://cdn-ar.mundogaturro.com/juego/npc/" + c.encode()
                      + b".npc?cache=no%20cache\x00" for c in comportamientos)
    (cache / "data_1").write_bytes(b"\xc3\xca\x04\xc1" + claves)
    (cache / "f_000001").write_bytes(b"/juego/npc/enElContenido.npc")  # el contenido no se lee


def test_encuentra_los_npc_de_las_salas_que_se_recorrieron(nucleo, fuente, sistema):
    fuente.npcs["entradaCasaRaton"] = npc("x: DO\n\troom.change 51686469 5,5\n")
    cache_del_juego(sistema, "entradaCasaRaton", "brujaMesa", "unBanner", "noExiste", "magia/portal")

    resultado = nucleo.buscar_comportamientos_en_el_juego()

    assert resultado["ok"], resultado
    assert [(n["comportamiento"], n["tipo"], n["encontrado"]) for n in resultado["nuevos"]] == [("entradaCasaRaton", "portal", True)]
    portales = {c["comportamiento"]: c for c in nucleo.comportamientos("portal")["comportamientos"]}
    assert portales["entradaCasaRaton"]["encontrado"] and "encontrado" not in portales["subteJapon"]
    assert nucleo.comportamiento("entradaCasaRaton")["comportamiento"]["descripcion"] == "Te lleva a la sala 51686469"
    # Lo encontrado queda guardado: no se vuelve a bajar.
    fuente.npcs.clear()
    assert nucleo.buscar_comportamientos_en_el_juego()["nuevos"] == []
    assert "entradaCasaRaton" in {c["comportamiento"] for c in nucleo.comportamientos("portal")["comportamientos"]}


def test_sin_internet_lo_encontrado_queda_pendiente(nucleo, fuente, sistema):
    fuente.npcs["entradaCasaRaton"] = npc("x: DO\n\troom.change 51686469 5,5\n")
    cache_del_juego(sistema, "entradaCasaRaton")
    fuente.sin_conexion = True

    sin = nucleo.buscar_comportamientos_en_el_juego()
    fuente.sin_conexion = False
    con = nucleo.buscar_comportamientos_en_el_juego()

    assert sin["ok"] and sin["nuevos"] == [] and sin["sin_conexion"]
    assert [n["comportamiento"] for n in con["nuevos"]] == ["entradaCasaRaton"] and not con["sin_conexion"]


def test_antes_de_entregar_se_anotan_los_del_cache(nucleo, fuente, sistema):
    # La entrega borra el caché del juego: lo que había se anota antes y se baja la próxima vez.
    fuente.npcs["entradaCasaRaton"] = npc("x: DO\n\troom.change 51686469 5,5\n")
    cache_del_juego(sistema, "entradaCasaRaton")

    assert nucleo.entregar_encode(nucleo.generar_encode(["costumes2.remera5"])["encode"])["ok"]
    assert not (sistema.base / "Roaming" / "MundoGaturro" / "Cache" / "data_1").exists()

    assert [n["comportamiento"] for n in nucleo.buscar_comportamientos_en_el_juego()["nuevos"]] == ["entradaCasaRaton"]


def test_si_no_se_puede_leer_el_cache_se_avisa(nucleo, sistema):
    (sistema.base / "Roaming" / "MundoGaturro" / "Cache" / "data_1").mkdir(parents=True)  # no se puede leer

    resultado = nucleo.buscar_comportamientos_en_el_juego()

    assert not resultado["ok"] and "caché del juego" in resultado["error"]

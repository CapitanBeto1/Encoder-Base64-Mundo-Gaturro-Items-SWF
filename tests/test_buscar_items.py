import base64

import pytest

from mgitems.nucleo import Nucleo
from swf_de_ejemplo import crear_swf

CLASES_CLOTHES = [
    "remera5_on", "remera5_brazo_on", "remera5",
    "Remera6",
    "remera_onda",
    "traje_Lucha",
    "gorra1_on", "gorra1",
    "zapatoPop",
    "silla_so",
    "clothes1_fla.MainTimeline",
    "assets.GaturroMC",
]


@pytest.fixture
def nucleo():
    return Nucleo()


@pytest.fixture
def clothes1(tmp_path):
    ruta = tmp_path / "clothes1.swf"
    ruta.write_bytes(crear_swf(CLASES_CLOTHES))
    return ruta


@pytest.mark.parametrize("compresion", ["FWS", "CWS", "ZWS"])
def test_abre_swf_sin_comprimir_y_comprimidos(nucleo, tmp_path, compresion):
    ruta = tmp_path / "clothes1.swf"
    ruta.write_bytes(crear_swf(CLASES_CLOTHES, compresion))

    resultado = nucleo.abrir_swf(str(ruta))

    assert resultado == {"ok": True, "swf": "clothes1", "cantidad_items": 6}
    assert nucleo.buscar_items("r")["items"] == ["clothes1.remera5", "clothes1.Remera6", "clothes1.remera_onda"]


def test_los_resultados_excluyen_piezas_objetos_de_escenario_y_clases_internas(nucleo, clothes1):
    nucleo.abrir_swf(str(clothes1))

    resultado = nucleo.buscar_items("remera, gorra, traje, zapato, silla, clothes1, assets, Gaturro")

    assert resultado["items"] == [
        "clothes1.gorra1",
        "clothes1.remera5",
        "clothes1.Remera6",
        "clothes1.remera_onda",
        "clothes1.traje_Lucha",
        "clothes1.zapatoPop",
    ]


def test_un_nombre_con_on_en_el_medio_se_conserva_intacto(nucleo, clothes1):
    nucleo.abrir_swf(str(clothes1))

    assert nucleo.buscar_items("remera_o")["items"] == ["clothes1.remera_onda"]


def test_busca_por_comienzo_del_nombre_sin_distinguir_mayusculas(nucleo, clothes1):
    nucleo.abrir_swf(str(clothes1))

    assert nucleo.buscar_items("REMERA")["items"] == ["clothes1.remera5", "clothes1.Remera6", "clothes1.remera_onda"]
    assert nucleo.buscar_items("pop")["items"] == []


def test_los_resultados_estan_en_orden_natural(nucleo, tmp_path):
    ruta = tmp_path / "clothes1.swf"
    ruta.write_bytes(crear_swf(["anteojo10", "anteojo2", "Anteojo1", "anteojo5a", "anteojo5"]))
    nucleo.abrir_swf(str(ruta))

    assert nucleo.buscar_items("anteojo")["items"] == [
        "clothes1.Anteojo1",
        "clothes1.anteojo2",
        "clothes1.anteojo5",
        "clothes1.anteojo5a",
        "clothes1.anteojo10",
    ]


def test_busca_con_varios_prefijos_separados_por_coma(nucleo, clothes1):
    nucleo.abrir_swf(str(clothes1))

    resultado = nucleo.buscar_items(" gorra ,zapato,, gorra")

    assert resultado == {"ok": True, "items": ["clothes1.gorra1", "clothes1.zapatoPop"]}


def test_buscar_sin_prefijos_devuelve_error(nucleo, clothes1):
    nucleo.abrir_swf(str(clothes1))

    resultado = nucleo.buscar_items(" , ")

    assert not resultado["ok"]
    assert resultado["error"]


def test_buscar_sin_swf_abierto_devuelve_error(nucleo):
    resultado = nucleo.buscar_items("remera")

    assert not resultado["ok"]
    assert "SWF" in resultado["error"]


def test_abrir_otro_swf_reemplaza_al_anterior(nucleo, clothes1, tmp_path):
    costumes = tmp_path / "costumes.swf"
    costumes.write_bytes(crear_swf(["remeraDisfraz", "costumeUnicornio"]))
    nucleo.abrir_swf(str(clothes1))

    nucleo.abrir_swf(str(costumes))

    assert nucleo.buscar_items("remera")["items"] == ["costumes.remeraDisfraz"]


@pytest.mark.parametrize(
    "contenido",
    [
        b"17\r\nerror del servidor",  # respuesta de error guardada como .swf
        b"<html>Not found</html>",
        b"",
        b"CWS\x0a\x00\x10\x00\x00no es zlib",
        crear_swf(CLASES_CLOTHES, "FWS")[:-6],  # truncado
    ],
)
def test_un_archivo_que_no_es_un_swf_valido_devuelve_error(nucleo, tmp_path, contenido):
    ruta = tmp_path / "roto.swf"
    ruta.write_bytes(contenido)

    resultado = nucleo.abrir_swf(str(ruta))

    assert not resultado["ok"]
    assert "roto.swf" in resultado["error"]


def test_un_swf_invalido_no_reemplaza_al_abierto(nucleo, clothes1, tmp_path):
    roto = tmp_path / "roto.swf"
    roto.write_bytes(b"no es un swf")
    nucleo.abrir_swf(str(clothes1))

    nucleo.abrir_swf(str(roto))

    assert nucleo.buscar_items("gorra")["items"] == ["clothes1.gorra1"]


def test_un_archivo_inexistente_devuelve_error(nucleo, tmp_path):
    resultado = nucleo.abrir_swf(str(tmp_path / "no-existe.swf"))

    assert not resultado["ok"]
    assert resultado["error"]


def test_el_encode_contiene_solo_los_items_que_quedan_en_la_lista(nucleo, clothes1):
    nucleo.abrir_swf(str(clothes1))
    encontrados = nucleo.buscar_items("remera, gorra")["items"]
    elegidos = [i for i in encontrados if i != "clothes1.Remera6"]

    resultado = nucleo.generar_encode(elegidos)

    script = base64.b64decode(resultado["encode"]).decode("utf-8")
    assert [i["ruta"] for i in resultado["items"]] == ["clothes1.gorra1", "clothes1.remera5", "clothes1.remera_onda"]
    assert "inventory.add 1 clothes1.gorra1\n" in script
    assert "inventory.add 1 clothes1.remera5\n" in script
    assert "inventory.add 1 clothes1.remera_onda\n" in script
    assert "Remera6" not in script


def test_interpretar_items_escritos_a_mano(nucleo):
    assert nucleo.interpretar_items("clothes1.remera5, costumes.costumeUnicornio") == {
        "ok": True,
        "items": ["clothes1.remera5", "costumes.costumeUnicornio"],
    }
    assert not nucleo.interpretar_items("remera5")["ok"]

import pytest

from mgitems.catalogo import cargar_catalogo
from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf

CATALOGO = [
    {"swf": "antro2017/wears", "items": 2},
    {"swf": "boca2017/wears", "items": 53},
    {"swf": "clothes1", "items": 3},
    {"swf": "costumes", "items": 141},
    {"swf": "fashion_basicos", "items": 143},
]
CLOTHES1 = crear_swf(["remera5_on", "remera5", "gorra1", "zapatoPop"])
WEARS = crear_swf(["remeraAntro_on", "remeraAntro", "lentesAntro"])


@pytest.fixture
def sistema(tmp_path):
    return SistemaFalso(tmp_path)


@pytest.fixture
def fuente():
    return FuenteFalsa({"clothes1": CLOTHES1, "antro2017/wears": WEARS})


@pytest.fixture
def nucleo(sistema, fuente):
    return Nucleo(sistema, fuente=fuente, catalogo=CATALOGO)


def nombres(resultado):
    return [s["swf"] for s in resultado["swfs"]]


def test_el_catalogo_incluido_tiene_swf_con_items():
    catalogo = cargar_catalogo()

    assert len(catalogo) > 100
    assert all(s["items"] > 0 for s in catalogo)
    assert {"swf": "clothes1", "items": catalogo[[s["swf"] for s in catalogo].index("clothes1")]["items"]} in catalogo
    assert any("/" in s["swf"] for s in catalogo)


def test_buscar_en_el_catalogo_por_nombre(nucleo):
    assert nombres(nucleo.buscar_en_catalogo("WEARS")) == ["antro2017/wears", "boca2017/wears"]
    assert nombres(nucleo.buscar_en_catalogo("boca")) == ["boca2017/wears"]
    assert nombres(nucleo.buscar_en_catalogo("")) == [s["swf"] for s in CATALOGO]
    assert nucleo.buscar_en_catalogo("zzz")["swfs"] == []


def test_los_que_empiezan_con_el_texto_van_primero(nucleo):
    assert nombres(nucleo.buscar_en_catalogo("cos")) == ["costumes", "fashion_basicos"]
    assert nombres(nucleo.buscar_en_catalogo("s"))[:2] == ["antro2017/wears", "boca2017/wears"]
    assert nombres(nucleo.buscar_en_catalogo("ba"))[0] == "fashion_basicos"


def test_abrir_un_swf_del_cdn_lo_descarga_y_permite_buscar(nucleo, fuente, sistema):
    resultado = nucleo.abrir_swf_del_cdn("clothes1")

    assert resultado == {
        "ok": True, "swf": "clothes1", "cantidad_items": 3, "tamano": len(CLOTHES1), "origen": "descarga",
    }
    assert fuente.descargas == ["clothes1"]
    assert (sistema.base / "Local" / "MGItems" / "swf" / "clothes1.swf").read_bytes() == CLOTHES1
    assert nucleo.buscar_items("remera")["items"] == ["clothes1.remera5"]


def test_los_items_de_un_swf_en_subcarpeta_llevan_la_carpeta(nucleo):
    nucleo.abrir_swf_del_cdn("antro2017/wears")

    assert nucleo.buscar_items("remera, lentes")["items"] == ["antro2017/wears.lentesAntro", "antro2017/wears.remeraAntro"]


def test_un_swf_ya_descargado_no_se_vuelve_a_descargar(sistema, fuente):
    Nucleo(sistema, fuente=fuente, catalogo=CATALOGO).abrir_swf_del_cdn("clothes1")

    resultado = Nucleo(sistema, fuente=fuente, catalogo=CATALOGO).abrir_swf_del_cdn("clothes1")

    assert resultado["ok"]
    assert resultado["origen"] == "copia"
    assert fuente.descargas == ["clothes1"]


def test_si_el_swf_cambio_en_el_cdn_se_descarga_de_nuevo(nucleo, fuente):
    nucleo.abrir_swf_del_cdn("clothes1")
    nuevo = crear_swf(["remera5", "remera6", "gorra1", "zapatoPop"])
    fuente.publicar("clothes1", nuevo, '"v2"')

    resultado = nucleo.abrir_swf_del_cdn("clothes1")

    assert resultado["origen"] == "descarga"
    assert resultado["tamano"] == len(nuevo)
    assert resultado["cantidad_items"] == 4
    assert fuente.descargas == ["clothes1", "clothes1"]


def test_sin_internet_se_usa_la_copia_guardada_con_aviso(nucleo, fuente):
    nucleo.abrir_swf_del_cdn("clothes1")
    fuente.sin_conexion = True

    resultado = nucleo.abrir_swf_del_cdn("clothes1")

    assert resultado["ok"]
    assert resultado["origen"] == "copia"
    assert "Sin conexión" in resultado["aviso"]
    assert resultado["tamano"] == len(CLOTHES1)


def test_sin_internet_y_sin_copia_devuelve_error(nucleo, fuente):
    fuente.sin_conexion = True

    resultado = nucleo.abrir_swf_del_cdn("clothes1")

    assert not resultado["ok"]
    assert "internet" in resultado["error"]


def test_un_swf_inexistente_devuelve_error(nucleo):
    resultado = nucleo.abrir_swf_del_cdn("noExiste")

    assert not resultado["ok"]
    assert "no existe" in resultado["error"]


def test_un_swf_danado_en_el_cdn_devuelve_error_y_no_se_guarda(nucleo, fuente, sistema):
    fuente.publicar("roto", b"<html>error</html>", '"x"')

    resultado = nucleo.abrir_swf_del_cdn("roto")

    assert not resultado["ok"]
    assert not (sistema.base / "Local" / "MGItems" / "swf" / "roto.swf").exists()


@pytest.mark.parametrize("nombre", ["../config", "a\\b", "", "clothes1.swf", "/clothes1"])
def test_un_nombre_de_swf_invalido_devuelve_error(nucleo, fuente, nombre):
    resultado = nucleo.abrir_swf_del_cdn(nombre)

    assert not resultado["ok"]
    assert fuente.descargas == []


def test_el_tamano_queda_disponible_al_abrir_un_archivo_local(nucleo, tmp_path):
    ruta = tmp_path / "clothes1.swf"
    ruta.write_bytes(CLOTHES1)

    resultado = nucleo.abrir_swf(str(ruta))

    assert resultado["tamano"] == len(CLOTHES1)
    assert resultado["origen"] == "archivo"


def test_un_archivo_local_en_una_subcarpeta_conocida_usa_la_carpeta(nucleo, tmp_path):
    ruta = tmp_path / "antro2017" / "wears.swf"
    ruta.parent.mkdir()
    ruta.write_bytes(WEARS)

    resultado = nucleo.abrir_swf(str(ruta))

    assert resultado["swf"] == "antro2017/wears"
    assert nucleo.buscar_items("lentes")["items"] == ["antro2017/wears.lentesAntro"]


def test_un_archivo_local_en_una_carpeta_cualquiera_usa_solo_su_nombre(nucleo, tmp_path):
    ruta = tmp_path / "descargas" / "wears.swf"
    ruta.parent.mkdir()
    ruta.write_bytes(WEARS)

    assert nucleo.abrir_swf(str(ruta))["swf"] == "wears"

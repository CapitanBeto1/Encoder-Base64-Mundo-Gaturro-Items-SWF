import base64
import json

import pytest

from mgitems.entrega import URL_LOLA
from mgitems.fuente import URL_ASSETS
from mgitems.nucleo import Nucleo
from mgitems.prendas import leer_item_base
from fuente_falsa import FuenteFalsa
from procesos_falso import ProcesosFalso
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_prendas import CLASES, COSTUMES, PrendasFalsas

REY = {
    "nombre": "Rey",
    "base": "costumes2.remera5",
    "partes": {"hats": "costumes.coronaRey_on", "grip": "costumes2.gorra1_on"},
}
CLOTHES1 = crear_swf(CLASES)


@pytest.fixture
def fuente():
    return FuenteFalsa({"costumes2": CLOTHES1, "costumes": COSTUMES})


def nucleo_de(tmp_path, nombre, fuente, ffdec=None):
    """El programa de un jugador (cada uno con su carpeta)."""
    sistema = SistemaFalso(tmp_path / nombre)
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    return Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec or PrendasFalsas())


# --- Archivo de Look ---

def test_exportar_e_importar_conserva_el_look(tmp_path, fuente):
    yo = nucleo_de(tmp_path, "yo", fuente)
    guardado = yo.guardar_look(REY)["look"]
    archivo = tmp_path / "Rey.mglook"

    assert yo.exportar_look(guardado, str(archivo))["ok"]
    otro = nucleo_de(tmp_path, "otro", fuente)
    importado = otro.importar_look_de_archivo(str(archivo))

    assert importado["ok"], importado
    look = importado["look"]
    assert (look["nombre"], look["base"], look["partes"]) == ("Rey", REY["base"], REY["partes"])
    assert look["id"] and look["id"] != guardado["id"]  # es un Look nuevo para quien lo importa
    assert otro.looks()["looks"] == [look]


def test_el_archivo_no_lleva_el_id_del_look(tmp_path, fuente):
    yo = nucleo_de(tmp_path, "yo", fuente)
    archivo = tmp_path / "Rey.mglook"

    yo.exportar_look(yo.guardar_look(REY)["look"], str(archivo))

    assert "id" not in json.loads(archivo.read_text(encoding="utf-8"))


def test_importar_un_look_con_un_nombre_que_ya_existe(tmp_path, fuente):
    yo = nucleo_de(tmp_path, "yo", fuente)
    yo.guardar_look(REY)
    archivo = tmp_path / "Rey.mglook"
    yo.exportar_look(REY, str(archivo))

    assert yo.importar_look_de_archivo(str(archivo))["look"]["nombre"] == "Rey (2)"
    assert yo.importar_look_de_archivo(str(archivo))["look"]["nombre"] == "Rey (3)"


@pytest.mark.parametrize(
    "contenido, error",
    [
        ("esto no es un Look", "no es un Look de MG Items"),
        ('{"looks": []}', "no es un Look de MG Items"),
        ('{"formato": "mgitems-look", "version": 99, "nombre": "X", "partes": {}}', "versión más nueva"),
        ('{"formato": "mgitems-look", "version": 1, "nombre": "", "partes": {"hats": "a.b"}}', "nombre"),
        ('{"formato": "mgitems-look", "version": 1, "nombre": "X", "partes": {}}', "no tiene Piezas"),
        ('{"formato": "mgitems-look", "version": 1, "nombre": "X", "partes": {"hats": "x\\"; hackear(); \\""}}', "Pieza no válida"),
    ],
)
def test_un_archivo_de_look_invalido_muestra_un_error_claro(tmp_path, fuente, contenido, error):
    yo = nucleo_de(tmp_path, "yo", fuente)
    archivo = tmp_path / "malo.mglook"
    archivo.write_text(contenido, encoding="utf-8")

    resultado = yo.importar_look_de_archivo(str(archivo))

    assert not resultado["ok"]
    assert error in resultado["error"]
    assert yo.looks()["looks"] == []


def test_importar_un_archivo_que_no_existe(tmp_path, fuente):
    resultado = nucleo_de(tmp_path, "yo", fuente).importar_look_de_archivo(str(tmp_path / "no.mglook"))

    assert not resultado["ok"]
    assert "No se pudo abrir" in resultado["error"]


def test_aplicar_un_look_importado_descarga_los_swf_que_faltan(tmp_path, fuente):
    archivo = tmp_path / "Rey.mglook"
    nucleo_de(tmp_path, "yo", fuente).exportar_look(REY, str(archivo))
    ffdec = PrendasFalsas()
    otro = nucleo_de(tmp_path, "otro", fuente, ffdec)  # sin ningún SWF abierto ni descargado
    look = otro.importar_look_de_archivo(str(archivo))["look"]

    resultado = otro.aplicar_look(look)

    assert resultado["ok"], resultado
    assert "inventory.add 1 costumes2.remera5\n" in base64.b64decode(resultado["encode"]).decode()
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"hats": "costumes.coronaRey_on", "grip": "gorra1_on"}
    assert set(fuente.descargas) == {"costumes2", "costumes"}


# --- Encode + SWF trucado, para Fiddler a mano ---

def test_exportar_el_look_aplicado_como_encode_y_swf_trucado(tmp_path, fuente):
    yo = nucleo_de(tmp_path, "yo", fuente)
    resultado = yo.aplicar_look(REY)
    assert yo.tiene_swf_trucado(resultado["encode"])
    carpeta = tmp_path / "Look Rey"

    exportado = yo.exportar_truco(resultado["encode"], str(carpeta))

    assert exportado["ok"], exportado
    assert (carpeta / "encode.txt").read_text(encoding="ascii") == resultado["encode"]
    assert (carpeta / "costumes2.swf").read_bytes().startswith(CLOTHES1)
    leeme = (carpeta / "LEEME.txt").read_text(encoding="utf-8")
    assert f"EXACT:{URL_LOLA}" in leeme
    assert f"EXACT:{URL_ASSETS}costumes2.swf?{len(CLOTHES1)}" in leeme


def test_un_encode_comun_no_tiene_swf_trucado(tmp_path, fuente):
    yo = nucleo_de(tmp_path, "yo", fuente)

    assert not yo.tiene_swf_trucado(yo.generar_encode([{"ruta": "costumes2.remera5", "cantidad": 1}])["encode"])


def test_exportar_un_encode_invalido(tmp_path, fuente):
    resultado = nucleo_de(tmp_path, "yo", fuente).exportar_truco("@@@", str(tmp_path / "x"))

    assert not resultado["ok"]
    assert not (tmp_path / "x").exists()

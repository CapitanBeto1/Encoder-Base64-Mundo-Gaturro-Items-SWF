"""Las fotos del Gaturro en vivo (las miniaturas de los guardados), guardadas para la próxima vez."""
import base64
import os
import time

import pytest

from mgitems.nucleo import Nucleo
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_gaturro import fuente_con

FOTO = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"una foto").decode("ascii")
FORMATO = "webgl-240-1.6"


@pytest.fixture
def fuente():
    return fuente_con()


def abrir(tmp_path, fuente) -> Nucleo:
    """El programa, abierto otra vez sobre la misma carpeta (otra sesión)."""
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[])


def atributos_de(nucleo, partes, colores=None):
    nucleo.swf_del_juego("clothes1")  # el Gaturro en vivo le pide el SWF de cada Pieza al vestirse
    return nucleo.gaturro_en_vivo(partes, colores)["atributos"]


def test_una_foto_guardada_se_usa_la_proxima_vez(tmp_path, fuente):
    nucleo = abrir(tmp_path, fuente)
    atributos = atributos_de(nucleo, {"cloth": "clothes1.remera5_on"})

    assert nucleo.foto_guardada(atributos, FORMATO) == {"ok": True, "imagen": None}
    assert nucleo.guardar_foto(atributos, FORMATO, FOTO) == {"ok": True}
    assert abrir(tmp_path, fuente).foto_guardada(atributos, FORMATO) == {"ok": True, "imagen": FOTO}


def test_es_la_de_esos_atributos_sacada_de_esa_forma(tmp_path, fuente):
    nucleo = abrir(tmp_path, fuente)
    atributos = atributos_de(nucleo, {"cloth": "clothes1.remera5_on"})
    nucleo.guardar_foto(atributos, FORMATO, FOTO)

    otros_colores = atributos_de(nucleo, {"cloth": "clothes1.remera5_on"}, {"color1": "#3366FF"})
    assert nucleo.foto_guardada(otros_colores, FORMATO)["imagen"] is None
    assert nucleo.foto_guardada(atributos, "canvas-240-1.6")["imagen"] is None


def test_si_el_juego_cambia_el_swf_de_una_pieza_la_foto_no_sirve(tmp_path, fuente):
    nucleo = abrir(tmp_path, fuente)
    atributos = atributos_de(nucleo, {"cloth": "clothes1.remera5_on"})
    nucleo.guardar_foto(atributos, FORMATO, FOTO)

    fuente.publicar("clothes1", crear_swf(["remera5_on", "otraRemera_on"]), '"v2"')
    otra_sesion = abrir(tmp_path, fuente)
    otra_sesion.swf_del_juego("clothes1")  # se entera de la versión nueva

    assert otra_sesion.foto_guardada(atributos, FORMATO)["imagen"] is None


def test_las_fotos_guardadas_vencen_a_la_semana(tmp_path, fuente):
    nucleo = abrir(tmp_path, fuente)
    atributos = atributos_de(nucleo, {"cloth": "clothes1.remera5_on"})
    nucleo.guardar_foto(atributos, FORMATO, FOTO)
    hace_ocho_dias = time.time() - 8 * 24 * 3600
    for foto in (tmp_path / "Local" / "MGItems" / "fotos").iterdir():
        os.utime(foto, (hace_ocho_dias, hace_ocho_dias))

    assert nucleo.foto_guardada(atributos, FORMATO)["imagen"] is None


@pytest.mark.parametrize("imagen", ["data:text/html;base64,PGI+", "data:image/png;base64,no es base64!",
                                    "data:image/png;base64," + base64.b64encode(b"GIF89a").decode("ascii"), 42])
def test_solo_guarda_imagenes_png(tmp_path, fuente, imagen):
    nucleo = abrir(tmp_path, fuente)
    atributos = atributos_de(nucleo, {"cloth": "clothes1.remera5_on"})

    assert not nucleo.guardar_foto(atributos, FORMATO, imagen)["ok"]
    assert nucleo.foto_guardada(atributos, FORMATO)["imagen"] is None


@pytest.mark.parametrize("atributos, formato", [("no son atributos", FORMATO), ({}, "../otra carpeta"), ({}, "")])
def test_los_datos_tienen_que_tener_la_forma_esperada(tmp_path, fuente, atributos, formato):
    nucleo = abrir(tmp_path, fuente)

    assert not nucleo.guardar_foto(atributos, formato, FOTO)["ok"]
    assert not nucleo.foto_guardada(atributos, formato)["ok"]

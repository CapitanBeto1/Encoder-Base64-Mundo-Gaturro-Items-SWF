import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mgitems.entrega import URL_LOLA
from mgitems.nucleo import Nucleo
from procesos_falso import ProcesosFalso
from sistema_falso import SistemaFalso, crear_archivo

REGLAS_DEL_JUGADOR = """\ufeff<?xml version="1.0" encoding="utf-8"?>
<AutoResponder LastSave="2026-10-24T10:26:29.8675136-03:00" FiddlerVersion="6.0.20262.10021">
  <State Enabled="false" AcceptAllConnects="false" Fallthrough="true" UseLatency="true">
    <ResponseRule Match="EXACT:https://cdn-ar.mundogaturro.com/juego/npc/lola.npc?cache=no%20cache" Action="D:\\Encodes &amp; cosas\\regalo.txt" Enabled="false" />
    <ResponseRule Match="regex:.*ejemplo\\.com.*" Action="*drop" Enabled="true" />
  </State>
</AutoResponder>"""


@pytest.fixture
def sistema(tmp_path):
    sistema = SistemaFalso(tmp_path / "Tom & Jerry's PC")  # caracteres que hay que escapar en XML
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    perfil = sistema.base / "Roaming" / "MundoGaturro"
    crear_archivo(perfil / "Cache" / "data_1").write_bytes(b"lola.npc en cache")
    crear_archivo(perfil / "Cache" / "f_000001")
    crear_archivo(perfil / "accounts").write_text("cuentas", encoding="utf-8")
    crear_archivo(perfil / "Cookies").write_bytes(b"cookies")
    crear_archivo(perfil / "Local Storage" / "leveldb" / "000003.log").write_bytes(b"datos")
    return sistema


@pytest.fixture
def archivo_reglas(sistema) -> Path:
    archivo = sistema.documentos / "Fiddler2" / "AutoResponder.xml"
    archivo.write_text(REGLAS_DEL_JUGADOR, encoding="utf-8")
    return archivo


def juego(sistema):
    return sistema.base / "Local" / "Programs" / "gaturro-desktop" / "MundoGaturro.exe"


def fiddler(sistema):
    return sistema.base / "Local" / "Programs" / "Fiddler" / "Fiddler.exe"


def encode_de_prueba(nucleo):
    return nucleo.generar_encode([{"ruta": "virtualGoods.agua", "cantidad": 5}])["encode"]


def reglas(archivo: Path) -> list[dict]:
    return [dict(r.attrib) for r in ET.parse(archivo).getroot().find("State").findall("ResponseRule")]


def test_entrega_completa(sistema, archivo_reglas):
    procesos = ProcesosFalso(abiertos=(juego(sistema), fiddler(sistema)))
    nucleo = Nucleo(sistema, procesos)
    encode = encode_de_prueba(nucleo)

    resultado = nucleo.entregar_encode(encode)

    assert resultado["ok"], resultado
    assert all(p["ok"] for p in resultado["pasos"])
    assert "Lola" in resultado["que_hacer"]
    # Orden: cerrar juego y Fiddler antes de escribir; abrir Fiddler (y esperar que capture) antes que el juego.
    assert procesos.historial == [
        "cerrar MundoGaturro.exe",
        "cerrar Fiddler.exe",
        "abrir Fiddler.exe",
        "esperar puerto 8888",
        "abrir MundoGaturro.exe",
    ]

    primera, *del_jugador = reglas(archivo_reglas)
    assert primera["Match"] == "EXACT:" + URL_LOLA
    assert primera["Enabled"] == "true"
    assert Path(primera["Action"]).read_text(encoding="ascii") == encode
    assert Path(primera["Action"]).is_relative_to(sistema.base / "Roaming" / "MGItems")
    # Las reglas del jugador quedan iguales y después de la del programa.
    assert del_jugador == [
        {"Match": "EXACT:" + URL_LOLA, "Action": "D:\\Encodes & cosas\\regalo.txt", "Enabled": "false"},
        {"Match": "regex:.*ejemplo\\.com.*", "Action": "*drop", "Enabled": "true"},
    ]
    estado = ET.parse(archivo_reglas).getroot().find("State")
    assert estado.get("Enabled") == "true"
    assert estado.get("Fallthrough") == "true"


def test_antes_de_modificar_las_reglas_se_guarda_una_copia(sistema, archivo_reglas):
    nucleo = Nucleo(sistema, ProcesosFalso())

    nucleo.entregar_encode(encode_de_prueba(nucleo))

    respaldo = archivo_reglas.with_name("AutoResponder.mgitems.bak")
    assert respaldo.read_text(encoding="utf-8") == REGLAS_DEL_JUGADOR


def test_las_rutas_con_caracteres_especiales_se_escriben_con_escape_xml(sistema, archivo_reglas):
    nucleo = Nucleo(sistema, ProcesosFalso())

    nucleo.entregar_encode(encode_de_prueba(nucleo))

    texto = archivo_reglas.read_text(encoding="utf-8-sig")
    assert "Tom &amp; Jerry's PC" in texto
    assert "Tom & Jerry" not in texto
    assert "Tom & Jerry's PC" in reglas(archivo_reglas)[0]["Action"]


def test_se_borra_solo_el_cache_del_juego(sistema, archivo_reglas):
    nucleo = Nucleo(sistema, ProcesosFalso())
    perfil = sistema.base / "Roaming" / "MundoGaturro"

    nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert not (perfil / "Cache").exists()
    assert (perfil / "accounts").read_text(encoding="utf-8") == "cuentas"
    assert (perfil / "Cookies").read_bytes() == b"cookies"
    assert (perfil / "Local Storage" / "leveldb" / "000003.log").read_bytes() == b"datos"


def test_si_no_habia_reglas_se_crea_el_archivo(sistema):
    nucleo = Nucleo(sistema, ProcesosFalso())
    archivo = sistema.documentos / "Fiddler2" / "AutoResponder.xml"

    resultado = nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert resultado["ok"]
    assert [r["Match"] for r in reglas(archivo)] == ["EXACT:" + URL_LOLA]
    assert not archivo.with_name("AutoResponder.mgitems.bak").exists()


def test_una_entrega_nueva_reemplaza_la_regla_anterior_del_programa(sistema, archivo_reglas):
    nucleo = Nucleo(sistema, ProcesosFalso())
    nucleo.entregar_encode(encode_de_prueba(nucleo))
    segundo = nucleo.generar_encode(["clothes1.remera5"])["encode"]

    nucleo.entregar_encode(segundo)

    todas = reglas(archivo_reglas)
    assert len(todas) == 3
    assert Path(todas[0]["Action"]).read_text(encoding="ascii") == segundo


def test_fiddler_guardando_sus_reglas_al_cerrarse_no_pisa_la_regla_nueva(sistema, archivo_reglas):
    procesos = ProcesosFalso(abiertos=(fiddler(sistema),))
    # Fiddler escribe su copia en memoria al cerrarse: tiene que pasar antes de que se escriba la regla.
    procesos.al_cerrar["Fiddler.exe"] = lambda: archivo_reglas.write_text(REGLAS_DEL_JUGADOR, encoding="utf-8")
    nucleo = Nucleo(sistema, procesos)

    nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert reglas(archivo_reglas)[0]["Match"] == "EXACT:" + URL_LOLA


def test_si_falta_configurar_algo_no_se_toca_nada(sistema, archivo_reglas):
    sistema.ajustes["CaptureHTTPS"] = "False"
    procesos = ProcesosFalso(abiertos=(juego(sistema),))
    nucleo = Nucleo(sistema, procesos)

    resultado = nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert not resultado["ok"]
    assert resultado["falta_configurar"]
    assert "Descifrado HTTPS" in resultado["error"]
    assert procesos.historial == []
    assert archivo_reglas.read_text(encoding="utf-8") == REGLAS_DEL_JUGADOR


def test_un_encode_invalido_no_se_entrega(sistema, archivo_reglas):
    procesos = ProcesosFalso()

    resultado = Nucleo(sistema, procesos).entregar_encode("no es un encode")

    assert not resultado["ok"]
    assert procesos.historial == []


def test_si_el_juego_no_se_cierra_se_informa_y_no_se_sigue(sistema, archivo_reglas):
    procesos = ProcesosFalso(abiertos=(juego(sistema),))
    procesos.no_se_cierran.add("MundoGaturro.exe")
    nucleo = Nucleo(sistema, procesos)

    resultado = nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert not resultado["ok"]
    assert "Cerrar Mundo Gaturro" in resultado["error"]
    assert "a mano" in resultado["que_hacer"]
    assert [p["ok"] for p in resultado["pasos"]] == [False]
    assert archivo_reglas.read_text(encoding="utf-8") == REGLAS_DEL_JUGADOR
    assert (sistema.base / "Roaming" / "MundoGaturro" / "Cache").exists()


def test_reglas_ilegibles_no_se_sobrescriben(sistema):
    archivo = sistema.documentos / "Fiddler2" / "AutoResponder.xml"
    archivo.write_text("<AutoResponder><State>", encoding="utf-8")
    nucleo = Nucleo(sistema, ProcesosFalso())

    resultado = nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert not resultado["ok"]
    assert "Escribir la regla de Lola" in resultado["error"]
    assert resultado["que_hacer"]
    assert archivo.read_text(encoding="utf-8") == "<AutoResponder><State>"


def test_si_el_cache_esta_en_uso_se_informa(sistema, archivo_reglas):
    nucleo = Nucleo(sistema, ProcesosFalso())
    bloqueado = sistema.base / "Roaming" / "MundoGaturro" / "Cache" / "data_1"

    with open(bloqueado, "rb"):  # en Windows, un archivo abierto no se puede borrar
        resultado = nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert not resultado["ok"]
    assert "Borrar el caché del juego" in resultado["error"]
    assert "cerrado" in resultado["que_hacer"]


def test_si_fiddler_no_empieza_a_capturar_se_informa(sistema, archivo_reglas):
    procesos = ProcesosFalso()
    procesos.fiddler_captura = False
    nucleo = Nucleo(sistema, procesos)

    resultado = nucleo.entregar_encode(encode_de_prueba(nucleo))

    assert not resultado["ok"]
    assert "Abrir Fiddler" in resultado["error"]
    assert "abrir MundoGaturro.exe" not in procesos.historial


def test_desactivar_quita_solo_las_reglas_del_programa(sistema, archivo_reglas):
    nucleo = Nucleo(sistema, ProcesosFalso())
    nucleo.entregar_encode(encode_de_prueba(nucleo))
    procesos = ProcesosFalso(abiertos=(fiddler(sistema),))

    resultado = Nucleo(sistema, procesos).desactivar_reglas()

    assert resultado["ok"]
    assert resultado["quitadas"] == 1
    assert [r["Action"] for r in reglas(archivo_reglas)] == ["D:\\Encodes & cosas\\regalo.txt", "*drop"]
    # Fiddler estaba abierto: se cierra para escribir y se vuelve a abrir.
    assert procesos.historial == ["cerrar Fiddler.exe", "abrir Fiddler.exe", "esperar puerto 8888"]


def test_desactivar_con_fiddler_cerrado_no_lo_abre(sistema, archivo_reglas):
    procesos = ProcesosFalso()

    resultado = Nucleo(sistema, procesos).desactivar_reglas()

    assert resultado == {"ok": True, "quitadas": 0, "pasos": resultado["pasos"]}
    assert "abrir Fiddler.exe" not in procesos.historial
    assert reglas(archivo_reglas)[0]["Action"] == "D:\\Encodes & cosas\\regalo.txt"


def test_juego_abierto(sistema):
    assert Nucleo(sistema, ProcesosFalso(abiertos=(juego(sistema),))).juego_abierto()
    assert not Nucleo(sistema, ProcesosFalso()).juego_abierto()

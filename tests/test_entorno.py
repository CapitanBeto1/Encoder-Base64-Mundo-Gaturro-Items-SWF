from pathlib import Path

import pytest

from mgitems.nucleo import Nucleo
from sistema_falso import SistemaFalso, crear_archivo


@pytest.fixture
def sistema(tmp_path):
    return SistemaFalso(tmp_path)


def componentes(estado: dict) -> dict:
    return {c["id"]: c for c in estado["componentes"]}


def faltantes(estado: dict) -> list[str]:
    return [c["id"] for c in estado["componentes"] if not c["ok"]]


def test_todo_presente(sistema):
    juego = sistema.instalar_juego()
    fiddler = sistema.instalar_fiddler()

    estado = Nucleo(sistema).estado_entorno()

    assert estado["listo"]
    assert faltantes(estado) == []
    c = componentes(estado)
    assert c["juego"]["ruta"] == str(juego)
    assert c["perfil"]["ruta"] == str(sistema.base / "Roaming" / "MundoGaturro")
    assert c["fiddler"]["ruta"] == str(fiddler)
    assert c["reglas"]["ruta"] == str(sistema.documentos / "Fiddler2")


def test_falta_el_juego(sistema):
    sistema.instalar_fiddler()

    estado = Nucleo(sistema).estado_entorno()

    assert not estado["listo"]
    assert faltantes(estado) == ["juego", "perfil"]
    juego = componentes(estado)["juego"]
    assert juego["instrucciones"]
    assert juego["corregible"] == "archivo"


def test_falta_fiddler(sistema):
    sistema.instalar_juego()

    estado = Nucleo(sistema).estado_entorno()

    assert not estado["listo"]
    assert faltantes(estado) == ["fiddler", "reglas", "https", "certificado"]
    c = componentes(estado)
    assert c["fiddler"]["instrucciones"]
    # Los pasos de lo que depende de Fiddler empiezan por instalarlo.
    for id_ in ("reglas", "https", "certificado"):
        assert "instalá Fiddler" in c[id_]["instrucciones"][0]


def test_https_desactivado(sistema):
    sistema.instalar_juego()
    sistema.instalar_fiddler(https=False)

    estado = Nucleo(sistema).estado_entorno()

    assert not estado["listo"]
    assert faltantes(estado) == ["https"]
    pasos = " ".join(componentes(estado)["https"]["instrucciones"])
    assert "Decrypt HTTPS traffic" in pasos


def test_https_sin_capturar_connect(sistema):
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    sistema.ajustes["CaptureCONNECT"] = "False"

    assert faltantes(Nucleo(sistema).estado_entorno()) == ["https"]


def test_falta_el_certificado(sistema):
    sistema.instalar_juego()
    sistema.instalar_fiddler(certificado=False)

    estado = Nucleo(sistema).estado_entorno()

    assert faltantes(estado) == ["certificado"]
    assert "Trust Root Certificate" in " ".join(componentes(estado)["certificado"]["instrucciones"])


def test_falta_la_carpeta_de_reglas(sistema):
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    (sistema.documentos / "Fiddler2").rmdir()

    assert faltantes(Nucleo(sistema).estado_entorno()) == ["reglas"]


def test_detecta_programas_instalados_en_otro_lugar_por_el_registro(sistema):
    juego = sistema.instalar_juego(sistema.base / "Juegos" / "MG")
    fiddler = sistema.instalar_fiddler(sistema.base / "Herramientas" / "Fiddler")

    c = componentes(Nucleo(sistema).estado_entorno())

    assert c["juego"]["ruta"] == str(juego)
    assert c["fiddler"]["ruta"] == str(fiddler)


def test_detecta_fiddler_en_program_files_sin_registro(sistema):
    sistema.instalar_juego()
    fiddler = crear_archivo(sistema.base / "Program Files (x86)" / "Fiddler2" / "Fiddler.exe")

    assert componentes(Nucleo(sistema).estado_entorno())["fiddler"]["ruta"] == str(fiddler)


def test_una_ruta_corregida_a_mano_se_usa_y_persiste(sistema):
    juego = crear_archivo(sistema.base / "OtroDisco" / "MundoGaturro.exe")

    estado = Nucleo(sistema).corregir_ruta("juego", str(juego))

    assert componentes(estado)["juego"]["ok"]
    assert componentes(estado)["juego"]["corregida"]
    # Una ejecución nueva del programa (otro Nucleo) la sigue usando.
    assert componentes(Nucleo(sistema).estado_entorno())["juego"]["ruta"] == str(juego)


def test_una_carpeta_corregida_a_mano_se_usa(sistema):
    carpeta = sistema.base / "OneDrive" / "Fiddler2"
    carpeta.mkdir(parents=True)

    estado = Nucleo(sistema).corregir_ruta("reglas", str(carpeta))

    assert componentes(estado)["reglas"]["ruta"] == str(carpeta)


def test_si_la_ruta_corregida_desaparece_se_informa(sistema):
    sistema.instalar_juego()
    otro = crear_archivo(sistema.base / "OtroDisco" / "MundoGaturro.exe")
    nucleo = Nucleo(sistema)
    nucleo.corregir_ruta("juego", str(otro))
    otro.unlink()

    juego = componentes(nucleo.estado_entorno())["juego"]

    assert not juego["ok"]
    assert juego["corregida"]
    assert "ya no existe" in juego["detalle"]


def test_restablecer_vuelve_a_detectar_automaticamente(sistema):
    instalado = sistema.instalar_juego()
    otro = crear_archivo(sistema.base / "OtroDisco" / "MundoGaturro.exe")
    nucleo = Nucleo(sistema)
    nucleo.corregir_ruta("juego", str(otro))

    estado = nucleo.restablecer_ruta("juego")

    assert componentes(estado)["juego"]["ruta"] == str(instalado)
    assert not componentes(estado)["juego"]["corregida"]


@pytest.mark.parametrize(
    "id_componente, ruta, error",
    [
        ("juego", "OtroDisco/no-existe.exe", "No existe"),
        ("juego", "OtroDisco/Otro.exe", "MundoGaturro.exe"),
        ("fiddler", "OtroDisco/MundoGaturro.exe", "Fiddler.exe"),
        ("reglas", "OtroDisco/no-existe", "No existe"),
        ("https", "OtroDisco", "no se puede elegir"),
    ],
)
def test_una_ruta_que_no_corresponde_no_se_guarda(sistema, id_componente, ruta, error):
    crear_archivo(sistema.base / "OtroDisco" / "Otro.exe")
    crear_archivo(sistema.base / "OtroDisco" / "MundoGaturro.exe")
    nucleo = Nucleo(sistema)

    resultado = nucleo.corregir_ruta(id_componente, str(sistema.base / ruta))

    assert not resultado["ok"]
    assert error in resultado["error"]
    assert not any(c["corregida"] for c in nucleo.estado_entorno()["componentes"])


def test_una_configuracion_danada_se_ignora(sistema):
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    crear_archivo(sistema.base / "Roaming" / "MGItems" / "config.json").write_text("{no es json", encoding="utf-8")

    assert Nucleo(sistema).estado_entorno()["listo"]


def test_el_codigo_no_tiene_rutas_de_una_computadora_en_particular():
    codigo = Path(__file__).parent.parent / "src"
    for archivo in codigo.rglob("*.*"):
        if archivo.suffix in (".py", ".js", ".html", ".css"):
            texto = archivo.read_text(encoding="utf-8").lower()
            assert "c:\\users" not in texto and "c:/users" not in texto, archivo

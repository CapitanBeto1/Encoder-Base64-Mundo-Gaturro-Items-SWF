import base64

import pytest

from mgitems.nucleo import Nucleo


@pytest.fixture
def nucleo():
    return Nucleo()


def codificar(script: str) -> str:
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def test_la_cantidad_de_cada_item_se_usa_en_el_script(nucleo):
    resultado = nucleo.generar_encode([
        {"ruta": "virtualGoods.agua", "cantidad": 5},
        {"ruta": "clothes1.remera5", "cantidad": 1},
        "costumes.costumeUnicornio",
    ])

    script = base64.b64decode(resultado["encode"]).decode("utf-8")
    assert resultado["items"] == [
        {"ruta": "virtualGoods.agua", "cantidad": 5},
        {"ruta": "clothes1.remera5", "cantidad": 1},
        {"ruta": "costumes.costumeUnicornio", "cantidad": 1},
    ]
    assert "    inventory.add 5 virtualGoods.agua\n" in script
    assert "    inventory.add 1 clothes1.remera5\n" in script
    assert "    inventory.add 1 costumes.costumeUnicornio\n" in script


def test_la_cantidad_puede_llegar_como_texto_desde_la_interfaz(nucleo):
    resultado = nucleo.generar_encode([{"ruta": "virtualGoods.agua", "cantidad": "12"}])

    assert resultado["items"] == [{"ruta": "virtualGoods.agua", "cantidad": 12}]


@pytest.mark.parametrize("cantidad", [0, -3, "", "abc", "2.5", 2.5, None, True])
def test_una_cantidad_invalida_devuelve_error(nucleo, cantidad):
    resultado = nucleo.generar_encode([{"ruta": "virtualGoods.agua", "cantidad": cantidad}])

    assert not resultado["ok"]
    assert "virtualGoods.agua" in resultado["error"]


def test_una_lista_vacia_devuelve_error(nucleo):
    assert not nucleo.generar_encode([])["ok"]


def test_ida_y_vuelta_encode_items_encode_conserva_los_datos(nucleo):
    original = nucleo.generar_encode([
        {"ruta": "virtualGoods.agua", "cantidad": 5},
        {"ruta": "carnival2/mascaras.antifaz", "cantidad": 1},
        {"ruta": "clothes1.remera5", "cantidad": 30},
    ])

    importado = nucleo.importar_encode(original["encode"])
    regenerado = nucleo.generar_encode(importado["items"])

    assert importado["ok"]
    assert importado["items"] == original["items"]
    assert not importado["otros_comandos"]
    assert importado["ignorados"] == []
    assert regenerado["encode"] == original["encode"]


def test_importa_encodes_con_saltos_de_linea_y_espacios(nucleo):
    encode = nucleo.generar_encode(["clothes1.remera5"])["encode"]
    partido = "\n  " + "\r\n".join(encode[i:i + 20] for i in range(0, len(encode), 20)) + "\n"

    assert nucleo.importar_encode(partido)["items"] == [{"ruta": "clothes1.remera5", "cantidad": 1}]


def test_importa_encodes_hechos_por_otras_herramientas(nucleo):
    # Formato de mg-tool: sin espacios en la línea en blanco tras `on activate`
    script = (
        "INICIO: DO\n    on activate A1\n\n"
        "A1: DO\n    user.state get\n    inventory.add 5 virtualGoods.disfrazBatman\n    after 1 A2\n\n"
        "A2: DO\n    user.state get\n    inventory.add 2 virtualGoods.agua\n    after 1 INICIO\n"
    )

    resultado = nucleo.importar_encode(codificar(script))

    assert resultado["items"] == [
        {"ruta": "virtualGoods.disfrazBatman", "cantidad": 5},
        {"ruta": "virtualGoods.agua", "cantidad": 2},
    ]
    assert not resultado["otros_comandos"]


def test_un_item_repetido_en_el_encode_suma_sus_cantidades(nucleo):
    script = (
        "INICIO: DO\n    on activate A1\n\n"
        "A1: DO\n    inventory.add 2 virtualGoods.agua\n    after 1 A2\n\n"
        "A2: DO\n    inventory.add 3 virtualGoods.agua\n    after 1 INICIO\n"
    )

    assert nucleo.importar_encode(codificar(script))["items"] == [{"ruta": "virtualGoods.agua", "cantidad": 5}]


def test_avisa_si_el_encode_hace_otras_cosas_ademas_de_agregar_items(nucleo):
    script = (
        "initial: DO\n    on activate A1\n\n"
        "A1: DO\n    reward.coin 1000\n    inventory.add 1 virtualGoods.agua\n    goto initial\n"
    )

    resultado = nucleo.importar_encode(codificar(script))

    assert resultado["ok"]
    assert resultado["otros_comandos"]
    assert resultado["items"] == [{"ruta": "virtualGoods.agua", "cantidad": 1}]


def test_los_items_con_formato_invalido_se_ignoran_y_se_informan(nucleo):
    script = "A1: DO\n    inventory.add 1 virtualGoods.agua\n    inventory.add 1 sinPunto\n"

    resultado = nucleo.importar_encode(codificar(script))

    assert resultado["items"] == [{"ruta": "virtualGoods.agua", "cantidad": 1}]
    assert resultado["ignorados"] == ["sinPunto"]


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "   \n ",
        "esto no es base64!!",
        "no es un encode",  # sin espacios es Base64 válido, pero decodifica a bytes sin sentido
        "EXACT:https://cdn-ar.mundogaturro.com/juego/npc/lola.npc?cache=no%20cache",
        "ñandú",
    ],
)
def test_un_texto_que_no_es_un_encode_devuelve_error(nucleo, texto):
    resultado = nucleo.importar_encode(texto)

    assert not resultado["ok"]
    assert resultado["error"]


def test_un_encode_que_no_agrega_items_devuelve_error(nucleo):
    resultado = nucleo.importar_encode(codificar("initial: DO\n    reward.coin 1000\n"))

    assert not resultado["ok"]
    assert "ningún Item" in resultado["error"]


def test_importa_un_encode_desde_un_archivo(nucleo, tmp_path):
    encode = nucleo.generar_encode([{"ruta": "virtualGoods.agua", "cantidad": 5}])["encode"]
    archivo = tmp_path / "agua.txt"
    archivo.write_text(encode + "\n", encoding="ascii")

    resultado = nucleo.importar_encode_de_archivo(str(archivo))

    assert resultado["items"] == [{"ruta": "virtualGoods.agua", "cantidad": 5}]


def test_importar_un_archivo_inexistente_devuelve_error(nucleo, tmp_path):
    resultado = nucleo.importar_encode_de_archivo(str(tmp_path / "no-existe.txt"))

    assert not resultado["ok"]
    assert resultado["error"]

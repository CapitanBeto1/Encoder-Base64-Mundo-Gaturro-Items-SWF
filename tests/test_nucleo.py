import base64

import pytest

from mgitems.nucleo import Nucleo


@pytest.fixture
def nucleo():
    return Nucleo()


def decodificar(encode: str) -> str:
    return base64.b64decode(encode).decode("utf-8")


def test_encode_de_un_item_contiene_el_script_esperado(nucleo):
    resultado = nucleo.generar_encode("clothes1.remera5")

    assert resultado["ok"]
    assert resultado["items"] == [{"ruta": "clothes1.remera5", "cantidad": 1}]
    assert decodificar(resultado["encode"]) == (
        "INICIO: DO\n"
        "    on activate A1\n"
        "    \n"
        "A1: DO\n"
        "    user.state get\n"
        "    inventory.add 1 clothes1.remera5\n"
        "    after 1 INICIO\n"
        "\n"
    )


def test_encode_de_varios_items_encadena_un_bloque_por_item(nucleo):
    resultado = nucleo.generar_encode("clothes1.remera5\ncostumes.costumeUnicornio\ncarnival2/mascaras.antifaz")

    assert resultado["ok"]
    assert decodificar(resultado["encode"]) == (
        "INICIO: DO\n"
        "    on activate A1\n"
        "    \n"
        "A1: DO\n"
        "    user.state get\n"
        "    inventory.add 1 clothes1.remera5\n"
        "    after 1 A2\n"
        "\n"
        "A2: DO\n"
        "    user.state get\n"
        "    inventory.add 1 costumes.costumeUnicornio\n"
        "    after 1 A3\n"
        "\n"
        "A3: DO\n"
        "    user.state get\n"
        "    inventory.add 1 carnival2/mascaras.antifaz\n"
        "    after 1 INICIO\n"
        "\n"
    )


def test_el_script_devuelto_es_el_que_contiene_el_encode(nucleo):
    resultado = nucleo.generar_encode("clothes1.remera5")

    assert decodificar(resultado["encode"]) == resultado["script"]


@pytest.mark.parametrize(
    "texto",
    [
        "clothes1.remera5, costumes.costumeUnicornio",
        "  clothes1.remera5  \r\n\r\n costumes.costumeUnicornio \n",
        "clothes1.remera5,\ncostumes.costumeUnicornio,",
    ],
)
def test_acepta_items_por_linea_o_separados_por_coma(nucleo, texto):
    resultado = nucleo.generar_encode(texto)

    assert resultado["ok"]
    assert [i["ruta"] for i in resultado["items"]] == ["clothes1.remera5", "costumes.costumeUnicornio"]


def test_un_item_repetido_se_agrega_una_sola_vez(nucleo):
    resultado = nucleo.generar_encode("clothes1.remera5, clothes1.remera5")

    assert resultado["items"] == [{"ruta": "clothes1.remera5", "cantidad": 1}]


@pytest.mark.parametrize("texto", ["", "   ", "\n , \n"])
def test_sin_items_devuelve_error(nucleo, texto):
    resultado = nucleo.generar_encode(texto)

    assert not resultado["ok"]
    assert resultado["error"]


def test_items_con_formato_invalido_devuelven_error_y_no_generan_encode(nucleo):
    resultado = nucleo.generar_encode("clothes1.remera5\nremera5\nclothes1 remera5\nclothes1.remera-5\ncámara.foto")

    assert not resultado["ok"]
    assert "encode" not in resultado
    assert resultado["invalidas"] == ["remera5", "clothes1 remera5", "clothes1.remera-5", "cámara.foto"]
    assert "remera5" in resultado["error"]


def test_guardar_encode_escribe_el_archivo(nucleo, tmp_path):
    encode = nucleo.generar_encode("clothes1.remera5")["encode"]
    destino = tmp_path / "items.txt"

    resultado = nucleo.guardar_encode(encode, str(destino))

    assert resultado == {"ok": True, "ruta": str(destino)}
    assert destino.read_text(encoding="ascii") == encode


def test_guardar_encode_en_una_carpeta_inexistente_devuelve_error(nucleo, tmp_path):
    resultado = nucleo.guardar_encode("QUJD", str(tmp_path / "no-existe" / "items.txt"))

    assert not resultado["ok"]
    assert resultado["error"]

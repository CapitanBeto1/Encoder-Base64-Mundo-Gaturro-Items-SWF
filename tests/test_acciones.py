"""Acciones: un Item de mochila que, al usarlo, hace una animación del juego mostrando una Pieza."""
import base64

import pytest

from mgitems.acciones import ANIMACIONES, motivo_pieza_sin_accion, motivo_sin_accion
from mgitems.nucleo import Nucleo
from mgitems.prendas import USOS_ILIMITADOS, leer_item_base
from procesos_falso import ProcesosFalso
from test_mochila import BRUJA, fuente, ffdec, sistema  # noqa: F401 (fixtures)
from test_prendas import reglas


@pytest.fixture
def nucleo(sistema, fuente, ffdec):
    return Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)


def test_las_animaciones_del_juego_en_el_orden_en_que_se_ofrecen(nucleo):
    resultado = nucleo.animaciones()

    assert resultado["ok"]
    filas = resultado["animaciones"]
    assert len(filas) == len(ANIMACIONES) == 106
    grupos = [f["grupo"] for f in filas]
    assert grupos == sorted(grupos, key=["accion", "no_se_dibuja", "otras"].index)  # de verdad, sin dibujo, otras
    mostrar = next(f for f in filas if f["id"] == "showObject")
    assert mostrar == {"id": "showObject", "nombre": "Mostrar en la mano", "grupo": "accion", "se_dibuja": True}
    assert next(f for f in filas if f["id"] == "fortnite1")["grupo"] == "no_se_dibuja"
    assert next(f for f in filas if f["id"] == "transportStand_moto")["grupo"] == "otras"
    de_verdad = [f["nombre"] for f in filas if f["grupo"] == "accion"]
    assert de_verdad.index("Agarrar") < de_verdad.index("Bailar") < de_verdad.index("Tomar")


def test_una_accion_que_muestra_una_pieza_de_otro_swf(nucleo, sistema, ffdec):
    # Como `drink.bruja.pocima1_on` de los Items del juego: la acción va en `adds.action`.
    resultado = nucleo.aplicar_accion({"animacion": "showObject", "pieza": "costumes.coronaRey_on", "base": "bruja.pocima1"})

    assert resultado["ok"], resultado
    item = leer_item_base(ffdec.trucos[0][1])
    assert item.partes == {"action": "showObject.costumes.coronaRey_on"}
    assert item.usos == USOS_ILIMITADOS
    assert "inventory.add 1 bruja.pocima1\n" in base64.b64decode(resultado["encode"]).decode()
    assert resultado["avisos"] == []
    assert nucleo.entregar_encode(resultado["encode"])["ok"]
    assert any(r["Match"].endswith(f"bruja.swf?{len(BRUJA)}") for r in reglas(sistema))


def test_una_accion_sin_pieza_y_otra_con_una_pieza_del_mismo_swf(nucleo, ffdec):
    assert nucleo.aplicar_accion({"animacion": "dance5", "base": "bruja.pocima1"})["ok"]
    assert nucleo.aplicar_accion({"animacion": "drink", "pieza": "bruja.pocima1_on", "base": "bruja.jugo1"})["ok"]

    assert leer_item_base(ffdec.trucos[0][1]).partes == {"action": "dance5"}
    assert leer_item_base(ffdec.trucos[1][1]).partes == {"action": "drink.bruja.pocima1_on"}


def test_una_accion_con_algo_en_la_cabeza(nucleo, ffdec):
    resultado = nucleo.aplicar_accion({"animacion": "flag", "pieza": "clothes1.gorra1_on", "efecto": "costumes.coronaRey_on",
                                       "base": "bruja.pocima1"})

    assert resultado["ok"], resultado
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"action": "flag.clothes1.gorra1_on", "effect": "head.costumes.coronaRey_on"}


def test_una_prenda_no_hace_acciones(nucleo, ffdec):
    resultado = nucleo.aplicar_accion({"animacion": "showObject", "pieza": "costumes.coronaRey_on", "base": "clothes1.buzo1"})

    assert not resultado["ok"]
    assert "Prenda" in resultado["error"]
    assert ffdec.trucos == []


@pytest.mark.parametrize("accion", [
    {"animacion": "volar", "base": "bruja.pocima1"},  # no es una animación del juego
    {"animacion": "showObject", "base": None},
    {"animacion": "showObject", "pieza": "costumes.noExiste_on", "base": "bruja.pocima1"},
    {"animacion": "phone", "pieza": "costumes.coronaRey_on", "base": "bruja.pocima1"},  # solo con teléfonos
    {"animacion": "run", "base": "bruja.pocima1"},  # el juego no hace las que dicen «run»
])
def test_lo_que_no_se_puede_truca_nada(nucleo, ffdec, accion):
    resultado = nucleo.aplicar_accion(accion)

    assert not resultado["ok"]
    assert ffdec.trucos == []


def test_las_reglas_del_juego_para_las_acciones():
    assert motivo_sin_accion("showObject.appTecno.motoTecno_on") is None
    assert motivo_sin_accion("showObject.gatoons.trunk_on")  # dice «run»: el juego la ignora
    assert motivo_sin_accion("eat.granja.zanahoria_on")  # prohibida en acciones
    assert motivo_sin_accion("phone.phones.celu_on") is None
    assert motivo_sin_accion("phone")  # sin Pieza, el teléfono tampoco anda
    assert motivo_sin_accion("football.gatoons.pelota_on")
    assert motivo_sin_accion("football.mundial.pelota_on") is None


def test_lo_que_una_accion_no_muestra_por_su_tamano():
    assert motivo_pieza_sin_accion("casa.pared_on", {"accion": "grande"})
    assert motivo_pieza_sin_accion("casa.nada_on", {"accion": "vacia"})
    assert motivo_pieza_sin_accion("appTecno.motoTecno_on", {"solo_en": "transport"}) is None  # un vehículo, sí
    assert motivo_pieza_sin_accion("petClothes.collar_on", {"no_se_ve": "es ropa de mascota"}) is None  # no pasa por el Gaturro


def test_el_indice_anota_el_tamano_que_mira_una_accion():
    from mgitems.se_ve import donde_se_ve

    assert donde_se_ve("casa.mesa_on", (0, 0, 200, 100))["accion"] == "grande"  # más de 150
    assert "accion" not in donde_se_ve("casa.mesa_on", (0, 0, 150, 150))  # 150 justo, sí
    assert donde_se_ve("casa.nada_on", (0, 0, 0, 0))["accion"] == "vacia"
    assert donde_se_ve("petClothes.collar_on", (0, 0, 400, 10))["accion"] == "grande"  # aunque el Gaturro no la dibuje


def test_la_vista_previa_no_inventa_una_animacion_que_no_puede_leer(nucleo):
    resultado = nucleo.animacion_de_accion({"animacion": "fortnite1"})

    assert resultado["ok"]
    assert resultado["imagenes"] == []
    assert "no se puede mostrar" in resultado["aviso"]
    assert not nucleo.animacion_de_accion({"animacion": "volar"})["ok"]


# --- Mis acciones ---

MOTO = {"nombre": "Moto en la mano", "base": "bruja.pocima1", "animacion": "showObject",
        "partes": {"action": "appTecno.motoTecno_on", "effect": "costumes.coronaRey_on"}}


def test_guardar_duplicar_y_borrar_acciones(nucleo):
    guardada = nucleo.guardar_accion(MOTO)

    assert guardada["ok"], guardada
    accion = guardada["accion"]
    assert accion["id"] and accion["animacion"] == "showObject"
    copia = nucleo.duplicar_accion(accion["id"])["accion"]
    assert copia["nombre"] == "Moto en la mano (copia)" and copia["animacion"] == "showObject"
    assert [a["nombre"] for a in nucleo.acciones()["acciones"]] == ["Moto en la mano", "Moto en la mano (copia)"]
    assert nucleo.looks()["looks"] == []  # aparte de los Looks
    assert nucleo.borrar_accion(accion["id"])["ok"]
    assert [a["nombre"] for a in nucleo.acciones()["acciones"]] == ["Moto en la mano (copia)"]


@pytest.mark.parametrize("accion", [
    MOTO | {"nombre": ""},
    MOTO | {"animacion": "volar"},
    MOTO | {"partes": {"hats": "costumes.coronaRey_on"}},  # una acción no viste
])
def test_una_accion_que_no_se_puede_guardar(nucleo, accion):
    assert not nucleo.guardar_accion(accion)["ok"]
    assert nucleo.acciones()["acciones"] == []


def test_exportar_e_importar_una_accion(nucleo, tmp_path):
    archivo = tmp_path / "moto.mgaccion"

    assert nucleo.exportar_accion(MOTO, str(archivo))["ok"]
    importada = nucleo.importar_accion_de_archivo(str(archivo))

    assert importada["ok"], importada
    assert {k: importada["accion"][k] for k in ("nombre", "base", "animacion", "partes")} == {k: MOTO[k] for k in ("nombre", "base", "animacion", "partes")}
    assert not nucleo.importar_look_de_archivo(str(archivo))["ok"]  # no es un Look
    otra = nucleo.importar_accion_de_archivo(str(archivo))
    assert otra["accion"]["nombre"] == "Moto en la mano (2)"

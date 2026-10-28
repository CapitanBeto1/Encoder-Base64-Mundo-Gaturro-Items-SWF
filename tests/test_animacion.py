"""La animación de una acción: el Gaturro reproducido como Flash Player, con el código de sus cuadros."""
import struct

import pytest

from mgitems.animacion import Linea, NoSeReproduce, Simulador, alinear, congelar, espejar, simular_accion
from mgitems.swf import leer_simbolos
from swf_de_ejemplo import _rect, _tag


def colocar(profundidad: int, simbolo: int | None = None, nombre: str | None = None, mueve: bool = False) -> bytes:
    banderas = (0x01 if mueve else 0) | (0x02 if simbolo is not None else 0) | (0x20 if nombre else 0)
    cuerpo = bytes([banderas]) + struct.pack("<H", profundidad)
    cuerpo += struct.pack("<H", simbolo) if simbolo is not None else b""
    cuerpo += nombre.encode() + b"\0" if nombre else b""
    return _tag(26, cuerpo)


def sacar(profundidad: int) -> bytes:
    return _tag(28, struct.pack("<H", profundidad))


def sprite(id_sprite: int, cuadros: list[list[bytes]], rotulos: dict[int, str] | None = None) -> bytes:
    tags = b""
    for numero, cuadro in enumerate(cuadros, 1):
        if rotulos and numero in rotulos:
            tags += _tag(43, rotulos[numero].encode() + b"\0")
        tags += b"".join(cuadro) + _tag(1, b"")
    return _tag(39, struct.pack("<HH", id_sprite, len(cuadros)) + tags + _tag(0, b""))


def swf(tags: bytes, clases: dict[int, str]) -> bytes:
    clase = struct.pack("<H", len(clases)) + b"".join(struct.pack("<H", i) + c.encode() + b"\0" for i, c in clases.items())
    cuerpo = _rect(0, 800, 0, 800) + struct.pack("<HH", 24 << 8, 1) + tags + _tag(76, clase) + _tag(1, b"") + _tag(0, b"")
    return b"FWS" + struct.pack("<BI", 10, 8 + len(cuerpo)) + cuerpo


def codigo(clase: str, cuadros: dict[int, str], metodos: str = "") -> str:
    """Código AS3 como el que exporta FFDec, con `addFrameScript`."""
    registro = ",".join(f"{n - 1},frame{n}" for n in cuadros)
    funciones = "".join(f"\n      internal function frame{n}() : *\n      {{\n{cuerpo}\n      }}\n" for n, cuerpo in cuadros.items())
    return (f"package\n{{\n   public dynamic class {clase} extends MovieClip\n   {{\n      public function {clase}()\n      {{\n"
            f"         super();\n         addFrameScript({registro});\n      }}\n{metodos}{funciones}   }}\n}}\n")


# Un Gaturro chico: quieto en el cuadro 1 (`standBy`); `flag` del 2 al 4, que vuelve a `standBy`; `dance` del
# 5 al 7, que se repite. La cabeza (`head`) tiene un ojo (`eye1`) que avanza solo y se frena, y que cerrado
# (`closed`) muestra un dibujo (el símbolo 99); `objects_ph`, vacío. Un cuadro con código que salta a otro no
# llega a verse, como en Flash.
OJO = sprite(12, [[], [], [colocar(1, 99)]], {1: "reseted", 3: "closed"})
CABEZA = sprite(11, [[colocar(1, 12, "eye1")]])
LUGAR = sprite(13, [[]])
GATURRO = sprite(10, [
    [colocar(1, 11, "head"), colocar(2, 13, "objects_ph")], [colocar(1, mueve=True)], [], [], [], [], [],
], {1: "standBy", 2: "flag", 5: "dance"})
CODIGO_GATURRO = codigo("GaturroMC", {
    1: "         stop();",
    3: '         eyes("closed");',
    4: '         gotoAndStop("standBy");',
    7: '         gotoAndPlay("dance");',
}, metodos='''
      public function eyes(param1:String) : void
      {
         head.eye1.gotoAndStop(param1);
      }
''')
CODIGO_OJO = codigo("eye_12", {2: "         stop();"})
DATOS_GATURRO = swf(OJO + CABEZA + LUGAR + GATURRO, {10: "assets.GaturroMC", 11: "fla.Head_11", 12: "fla.eye_12", 13: "fla.lugar_13"})

# La Pieza de la acción: tres cuadros sin código.
DATOS_OBJETO = swf(sprite(1, [[], [], []]), {1: "moto_on"})


@pytest.fixture
def gaturro():
    return Linea(DATOS_GATURRO, {"GaturroMC": CODIGO_GATURRO, "eye_12": CODIGO_OJO})


def test_el_codigo_del_cuadro_frena_y_los_clips_de_adentro_siguen(gaturro):
    simulador = Simulador()
    raiz = simulador.nuevo(gaturro, "assets.GaturroMC")
    simulador.correr_codigo()
    ojo = raiz.hijo("head").hijo("eye1")

    simulador.avanzar(raiz)
    simulador.avanzar(raiz)

    assert (raiz.cuadro, raiz.anda) == (1, False)  # stop() en su cuadro 1
    assert (ojo.cuadro, ojo.anda) == (2, False)  # avanzó solo y se frenó con su propio stop()


def test_una_accion_que_vuelve_a_quedarse_quieto(gaturro):
    accion = simular_accion(gaturro, "assets.GaturroMC", "flag")

    # Cuadros 2, 3 (cierra los ojos) y standBy (el 4 salta ahí antes de verse): queda quieto y termina.
    assert len(accion.cuadros) == 3
    assert accion.repite_desde is None
    assert len({c.gaturro for c in accion.cuadros}) == 3


def test_una_accion_que_se_repite(gaturro):
    accion = simular_accion(gaturro, "assets.GaturroMC", "dance")

    assert accion.repite_desde == 0  # el 7 vuelve al principio antes de verse: 5, 6, 5, 6…
    assert len(accion.cuadros) == 2


def test_el_metodo_lleva_el_ojo_a_su_cuadro(gaturro):
    simulador = Simulador()
    raiz = simulador.nuevo(gaturro, "assets.GaturroMC")
    simulador.correr_codigo()
    simulador.llamar(raiz, "gotoAndPlay", ["flag"])
    simulador.correr_codigo()

    simulador.avanzar(raiz)  # cuadro 3: eyes("closed")

    assert raiz.hijo("head").hijo("eye1").cuadro == 3


def test_saltar_para_atras_conserva_lo_que_sigue_igual(gaturro):
    simulador = Simulador()
    raiz = simulador.nuevo(gaturro, "assets.GaturroMC")
    simulador.correr_codigo()
    cabeza = raiz.hijo("head")
    simulador.llamar(raiz, "gotoAndStop", ["dance"])
    simulador.llamar(raiz, "gotoAndStop", ["standBy"])

    assert raiz.hijo("head") is cabeza  # la misma cabeza: no vuelve a empezar


def test_la_pieza_de_la_accion_se_frena_en_su_ultimo_cuadro(gaturro):
    objeto = Linea(DATOS_OBJETO, {})

    accion = simular_accion(gaturro, "assets.GaturroMC", "dance", objeto=(objeto, "moto_on"))

    claves = [c.objeto for c in accion.cuadros]
    assert all(claves)
    assert accion.repite_desde is not None
    assert claves[-1] == claves[accion.repite_desde]  # quedó en su último cuadro mientras el baile se repite


def test_el_codigo_que_no_se_entiende_no_se_adivina():
    datos = swf(sprite(10, [[], []], {1: "standBy", 2: "rara"}), {10: "assets.GaturroMC"})
    linea = Linea(datos, {"GaturroMC": codigo("GaturroMC", {1: "         stop();", 2: "         this.x = 5;"})})

    with pytest.raises(NoSeReproduce):
        simular_accion(linea, "assets.GaturroMC", "rara")


def test_una_animacion_que_el_gaturro_no_tiene(gaturro):
    with pytest.raises(NoSeReproduce):
        simular_accion(gaturro, "assets.GaturroMC", "fortnite1")


def test_los_cuadros_congelados_son_sprites_de_un_cuadro(gaturro):
    simulador = Simulador()
    raiz = simulador.nuevo(gaturro, "assets.GaturroMC")
    simulador.correr_codigo()

    clave = congelar(raiz)

    id_congelado = gaturro.congelados[clave][0]
    con_congelados = gaturro.swf_con_congelados()
    assert dict(leer_simbolos(con_congelados))[10] == "assets.GaturroMC"  # el SWF se sigue leyendo
    assert Linea(con_congelados, {}).sprites[id_congelado].total == 1
    assert congelar(raiz) == clave  # lo mismo, la misma clave


def test_los_cuadros_quedan_alineados_y_la_pieza_se_da_vuelta():
    chico = '<svg height="10.0px" width="20.0px"><g transform="matrix(1.0, 0.0, 0.0, 1.0, 5.0, 5.0)"><use/></g><defs></defs></svg>'
    grande = '<svg height="30.0px" width="20.0px"><g transform="matrix(1.0, 0.0, 0.0, 1.0, 5.0, 25.0)"><use/></g><defs></defs></svg>'

    a, b = alinear([chico, grande])

    assert 'height="30.0px"' in a and 'height="30.0px"' in b
    assert "5.0, 25.0)" in a  # el punto de registro en el mismo lugar
    assert '<g transform="scale(-1, 1)"><use/></g>' in espejar(chico)

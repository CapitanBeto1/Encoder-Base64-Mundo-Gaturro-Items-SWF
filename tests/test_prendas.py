import base64
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mgitems.entrega import URL_LOLA
from mgitems.ffdec import FFDec, FFDecNoDisponible
from mgitems.fuente import URL_ASSETS, FuenteCDN
from mgitems.nucleo import Nucleo
from mgitems.prendas import USOS_ILIMITADOS, ItemsBaseFFDec, TruqueoFallido, leer_item_base, reescribir_partes
from fuente_falsa import FuenteFalsa
from procesos_falso import ProcesosFalso
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf


def codigo_prenda(clase: str, partes: dict[str, str], simbolo: str = "symbol1") -> str:
    """Código AS3 como el que exporta FFDec para una Prenda del juego."""
    pares = ",\n".join(f'            "{p}":"{v}"' for p, v in partes.items())
    clothes = "{\n" + pares + "\n         }" if len(partes) > 1 else "{" + ",".join(f'"{p}":"{v}"' for p, v in partes.items()) + "}"
    return f'''package
{{
   [Embed(source="/_assets/assets.swf", symbol="{simbolo}")]
   public dynamic class {clase} extends ClothMamboAsset
   {{

      public function {clase}()
      {{
         super();
         addFrameScript(0,this.frame1);
      }}

      internal function frame1() : *
      {{
         clothes = {clothes};
      }}
   }}
}}
'''


CODIGO_NO_PRENDA = '''package
{
   public dynamic class silla extends HouseDecorationMamboAsset
   {
   }
}
'''

PRENDAS = {
    "remera5": {"cloth": "remera5_on", "arm": "remera5_brazo_on"},
    "buzo1": {"cloth": "buzo1_on", "arm": "buzo1_brazo_on"},
    "gorra1": {"hats": "gorra1_on"},
    "capa1": {"capeExtra": "capa1_on"},  # Parte del cuerpo que no está en la lista conocida
}
CLASES = ["silla"] + [c for prenda, partes in PRENDAS.items() for c in [prenda, *partes.values()]]


class PrendasFalsas(ItemsBaseFFDec):
    """Lee el código AS3 de un diccionario y "truca" agregando una marca a los bytes (sin Java)."""

    def __init__(self):
        super().__init__()
        self.codigo = {c: codigo_prenda(c, p) for c, p in PRENDAS.items()} | {"silla": CODIGO_NO_PRENDA}
        self.analisis = 0
        self.trucos: list[tuple[str, str]] = []
        self.falla = False

    def analizar(self, data, clases):
        self.analisis += 1
        prendas = (leer_item_base(self.codigo[c]) for c in clases if c in self.codigo)
        return {p.clase: p for p in prendas if p}

    def fuentes(self, data, clases):
        self.analisis += 1
        return {c: self.codigo[c] for c in clases if c in self.codigo}

    def trucar(self, data, clase, fuente, partes):
        if self.falla:
            raise TruqueoFallido("El SWF trucado no quedó con las Piezas elegidas")
        self.trucos.append((clase, fuente))
        return data + b"#trucado:" + json.dumps(partes).encode()


@pytest.fixture
def sistema(tmp_path):
    sistema = SistemaFalso(tmp_path)
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    return sistema


@pytest.fixture
def swf():
    return crear_swf(CLASES)


COSTUMES = crear_swf(["coronaRey", "coronaRey_on", "capaRey_on", "castillo_so"])


@pytest.fixture
def fuente(swf):
    return FuenteFalsa({"clothes1": swf, "antro2017/wears": swf, "costumes": COSTUMES})


@pytest.fixture
def ffdec():
    return PrendasFalsas()


@pytest.fixture
def nucleo(sistema, fuente, ffdec):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("clothes1")
    return nucleo


def reglas(sistema) -> list[dict]:
    archivo = sistema.documentos / "Fiddler2" / "AutoResponder.xml"
    return [dict(r.attrib) for r in ET.parse(archivo).getroot().find("State").findall("ResponseRule")]


# --- Código AS3 ---

def test_leer_una_prenda_del_codigo_as3():
    prenda = leer_item_base(codigo_prenda("remera5", PRENDAS["remera5"]))

    assert prenda.clase == "remera5"
    assert prenda.partes == {"cloth": "remera5_on", "arm": "remera5_brazo_on"}


def test_una_clase_que_no_extiende_cloth_mambo_asset_no_es_prenda():
    assert leer_item_base(CODIGO_NO_PRENDA) is None


def test_reescribir_las_partes_conserva_el_resto_del_codigo():
    original = codigo_prenda("remera5", PRENDAS["remera5"], simbolo="symbol889")

    nuevo = reescribir_partes(leer_item_base(original), {"cloth": "buzo1_on", "arm": "buzo1_brazo_on", "hats": "gorra1_on"})

    assert leer_item_base(nuevo).partes == {"cloth": "buzo1_on", "arm": "buzo1_brazo_on", "hats": "gorra1_on"}
    assert 'symbol="symbol889"' in nuevo
    assert "addFrameScript(0,this.frame1);" in nuevo
    assert nuevo.replace(nuevo[nuevo.index("clothes ="):nuevo.index("};") + 2], "") == \
        original.replace(original[original.index("clothes ="):original.index("};") + 2], "")


@pytest.mark.parametrize("partes", [{"cloth": 'x"; hackear(); "'}, {"cl oth": "remera5_on"}, {"cloth": ""}])
def test_reescribir_rechaza_nombres_que_no_son_identificadores(partes):
    with pytest.raises(ValueError):
        reescribir_partes(leer_item_base(codigo_prenda("remera5", PRENDAS["remera5"])), partes)


def test_reescribir_una_prenda_sin_clothes_falla():
    sin_clothes = codigo_prenda("remera5", PRENDAS["remera5"]).replace("clothes =", "otraCosa =")

    with pytest.raises(TruqueoFallido):
        reescribir_partes(leer_item_base(sin_clothes), {"cloth": "buzo1_on"})


# --- Prendas del SWF abierto ---

def test_lista_las_prendas_del_swf_con_sus_partes(nucleo):
    resultado = nucleo.prendas()

    assert resultado["ok"]
    assert resultado["swf"] == "clothes1"
    assert [p["ruta"] for p in resultado["prendas"]] == [
        "clothes1.buzo1", "clothes1.capa1", "clothes1.gorra1", "clothes1.remera5",
    ]
    remera = next(p for p in resultado["prendas"] if p["clase"] == "remera5")
    assert remera["partes"] == {"cloth": "remera5_on", "arm": "remera5_brazo_on"}


def test_las_partes_del_cuerpo_tienen_nombre_en_espanol(nucleo):
    partes = {p["id"]: p["nombre"] for p in nucleo.prendas()["partes_del_cuerpo"]}

    assert partes["hats"] == "Sombrero"
    assert partes["cloth"] == "Torso"
    assert partes["arm"] == "Brazos"
    assert partes["leg"] == "Piernas"
    assert partes["foot"] == "Pies"
    assert partes["capeExtra"] == "capeExtra"  # una Parte que aparece en el SWF pero no conocemos


def test_las_prendas_se_leen_una_sola_vez_por_version_del_swf(sistema, fuente, ffdec):
    for _ in range(2):
        nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
        nucleo.abrir_swf_del_cdn("clothes1")
        nucleo.prendas()
        nucleo.prendas()

    assert ffdec.analisis == 1


def test_prendas_sin_swf_abierto_devuelve_error(sistema, ffdec):
    assert not Nucleo(sistema, catalogo=[], prendas_ffdec=ffdec).prendas()["ok"]


def test_prendas_sin_java_devuelve_error(sistema, fuente):
    class SinJava(ItemsBaseFFDec):
        def analizar(self, data, clases):
            raise FFDecNoDisponible("No se encontró Java")

    nucleo = Nucleo(sistema, fuente=fuente, catalogo=[], prendas_ffdec=SinJava())
    nucleo.abrir_swf_del_cdn("clothes1")

    resultado = nucleo.prendas()

    assert not resultado["ok"]
    assert "Java" in resultado["error"]


# --- Piezas ---

def test_lista_todas_las_piezas_del_swf(nucleo):
    resultado = nucleo.piezas()

    assert resultado["ok"]
    assert [p["clase"] for p in resultado["piezas"]] == [
        "buzo1_brazo_on", "buzo1_on", "capa1_on", "gorra1_on", "remera5_brazo_on", "remera5_on",
    ]
    assert resultado["piezas"][0]["ruta"] == "clothes1.buzo1_brazo_on"


def test_piezas_sin_swf_abierto_devuelve_error(sistema, ffdec):
    assert not Nucleo(sistema, catalogo=[], prendas_ffdec=ffdec).piezas()["ok"]


# --- Trucar: una Pieza en una Parte del cuerpo ---

def test_trucar_pone_una_sola_pieza_en_la_parte_elegida(nucleo, ffdec):
    resultado = nucleo.trucar_prenda("remera5", "grip", "gorra1_on")  # una gorra en la mano

    assert resultado["ok"], resultado
    assert resultado["prenda"] == {"ruta": "clothes1.remera5", "tipo": "prenda", "partes": {"grip": "gorra1_on"}}
    script = base64.b64decode(resultado["encode"]).decode()
    assert "inventory.add 1 clothes1.remera5\n" in script
    clase, fuente = ffdec.trucos[0]
    assert clase == "remera5"
    # Solo esa Pieza: la remera deja de mostrar lo suyo y no se completa nada más.
    assert leer_item_base(fuente).partes == {"grip": "gorra1_on"}


@pytest.mark.parametrize("parte, pieza", [("foot", "remera5_brazo_on"), ("hats", "buzo1_on"), ("cloth", "gorra1_on"), ("capeExtra", "remera5_on")])
def test_cualquier_pieza_va_en_cualquier_parte_del_cuerpo(nucleo, ffdec, parte, pieza):
    resultado = nucleo.trucar_prenda("remera5", parte, pieza)

    assert resultado["ok"], resultado
    assert leer_item_base(ffdec.trucos[0][1]).partes == {parte: pieza}


@pytest.mark.parametrize(
    "base, parte, pieza, error",
    [
        ("silla", "hats", "gorra1_on", "no es una Prenda"),
        ("noExiste", "hats", "gorra1_on", "no es una Prenda"),
        ("remera5", "inventada", "gorra1_on", "no es una Parte del cuerpo"),
        ("remera5", "hats", "noExiste_on", "no es una Pieza"),
        ("remera5", "hats", "gorra1", "no es una Pieza"),  # un Item, no una Pieza
    ],
)
def test_trucar_con_datos_invalidos_no_llama_a_ffdec(nucleo, ffdec, base, parte, pieza, error):
    resultado = nucleo.trucar_prenda(base, parte, pieza)

    assert not resultado["ok"]
    assert error in resultado["error"]
    assert ffdec.trucos == []


def test_si_el_truco_falla_se_informa(nucleo, ffdec):
    ffdec.falla = True

    resultado = nucleo.trucar_prenda("remera5", "hats", "gorra1_on")

    assert not resultado["ok"]
    assert "No se pudo trucar" in resultado["error"]


# --- Piezas de otro SWF ---

def test_lista_las_piezas_de_otro_swf_sin_cambiar_el_abierto(nucleo):
    resultado = nucleo.piezas("costumes")

    assert resultado["ok"]
    assert [p["ruta"] for p in resultado["piezas"]] == ["costumes.capaRey_on", "costumes.coronaRey_on"]
    assert nucleo.piezas()["swf"] == "clothes1"
    assert nucleo.prendas()["swf"] == "clothes1"


def test_piezas_de_un_swf_inexistente_devuelve_error(nucleo):
    resultado = nucleo.piezas("noExiste")

    assert not resultado["ok"]
    assert "no existe" in resultado["error"]


def test_trucar_con_una_pieza_de_otro_swf_la_escribe_con_el_nombre_del_swf(nucleo, ffdec):
    resultado = nucleo.trucar_prenda("remera5", "hats", "costumes.coronaRey_on")

    assert resultado["ok"], resultado
    assert resultado["prenda"]["partes"] == {"hats": "costumes.coronaRey_on"}
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"hats": "costumes.coronaRey_on"}


def test_una_pieza_del_mismo_swf_con_su_nombre_completo_se_escribe_sin_el_swf(nucleo, ffdec):
    resultado = nucleo.trucar_prenda("remera5", "grip", "clothes1.gorra1_on")

    assert resultado["ok"], resultado
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"grip": "gorra1_on"}


@pytest.mark.parametrize(
    "pieza, error",
    [
        ("costumes.noExiste_on", "no es una Pieza de costumes"),
        ("costumes.coronaRey", "no es una Pieza de costumes"),  # un Item, no una Pieza
        ("noExiste.algo_on", "no existe"),
    ],
)
def test_una_pieza_de_otro_swf_que_no_sirve_se_avisa_antes_de_trucar(nucleo, ffdec, pieza, error):
    resultado = nucleo.trucar_prenda("remera5", "hats", pieza)

    assert not resultado["ok"]
    assert error in resultado["error"]
    assert ffdec.trucos == []


def test_una_pieza_de_un_swf_en_subcarpeta_conserva_la_carpeta(sistema, fuente, ffdec):
    fuente.publicar("animales2018/wears", crear_swf(["orejas", "orejas_on"]), '"v1"')
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("clothes1")

    resultado = nucleo.trucar_prenda("remera5", "hats", "animales2018/wears.orejas_on")

    assert resultado["ok"], resultado
    assert leer_item_base(ffdec.trucos[0][1]).partes == {"hats": "animales2018/wears.orejas_on"}


def test_con_una_pieza_de_otro_swf_solo_se_entrega_trucado_el_swf_de_la_prenda_base(nucleo, sistema):
    truco = nucleo.trucar_prenda("remera5", "hats", "costumes.coronaRey_on")

    assert nucleo.entregar_encode(truco["encode"])["ok"]

    assert [r["Match"].split("/")[-1] for r in reglas(sistema)] == [URL_LOLA.split("/")[-1], f"clothes1.swf?{len(crear_swf(CLASES))}"]


# --- Entregar la Prenda trucada ---

def test_entregar_una_prenda_trucada_escribe_las_reglas_de_lola_y_del_swf(nucleo, sistema, swf):
    truco = nucleo.trucar_prenda("remera5", "hats", "gorra1_on")

    resultado = nucleo.entregar_encode(truco["encode"])

    assert resultado["ok"], resultado
    lola, swf_trucado, *_ = reglas(sistema)
    assert lola["Match"] == "EXACT:" + URL_LOLA
    assert swf_trucado["Match"] == f"EXACT:{URL_ASSETS}clothes1.swf?{len(swf)}"
    assert Path(swf_trucado["Action"]).read_bytes() == swf + b'#trucado:{"hats": "gorra1_on"}'
    assert any("SWF trucado" in p["nombre"] for p in resultado["pasos"])


def test_un_encode_comun_no_entrega_swf(nucleo, sistema):
    encode = nucleo.generar_encode(["clothes1.remera5"])["encode"]

    nucleo.entregar_encode(encode)

    assert [r["Match"] for r in reglas(sistema)] == ["EXACT:" + URL_LOLA]


def test_una_entrega_nueva_reemplaza_las_reglas_del_truco_anterior(nucleo, sistema):
    nucleo.entregar_encode(nucleo.trucar_prenda("remera5", "hats", "gorra1_on")["encode"])

    nucleo.entregar_encode(nucleo.generar_encode(["clothes1.buzo1"])["encode"])

    assert [r["Match"] for r in reglas(sistema)] == ["EXACT:" + URL_LOLA]


def test_el_swf_trucado_de_una_subcarpeta_usa_la_carpeta_en_la_url_y_en_el_archivo(sistema, fuente, ffdec, swf):
    nucleo = Nucleo(sistema, ProcesosFalso(), fuente=fuente, catalogo=[], prendas_ffdec=ffdec)
    nucleo.abrir_swf_del_cdn("antro2017/wears")

    nucleo.entregar_encode(nucleo.trucar_prenda("remera5", "hats", "gorra1_on")["encode"])

    regla = reglas(sistema)[1]
    assert regla["Match"] == f"EXACT:{URL_ASSETS}antro2017/wears.swf?{len(swf)}"
    assert Path(regla["Action"]).parts[-2:] == ("antro2017", "wears.swf")


def test_sin_conexion_no_se_puede_entregar_una_prenda_trucada(nucleo, fuente, sistema):
    truco = nucleo.trucar_prenda("remera5", "hats", "gorra1_on")
    fuente.sin_conexion = True

    resultado = nucleo.entregar_encode(truco["encode"])

    assert not resultado["ok"]
    assert "conexión" in resultado["error"]
    assert not (sistema.documentos / "Fiddler2" / "AutoResponder.xml").exists()


# --- Con FFDec y el servidor del juego de verdad ---

def _hay_ffdec_y_red() -> bool:
    try:
        FFDec().programas()
        FuenteCDN().version("clothes1")
    except (FFDecNoDisponible, OSError):
        return False
    return True


@pytest.mark.skipif(not _hay_ffdec_y_red(), reason="Hace falta Java, FFDec e internet")
def test_con_ffdec_real_el_swf_trucado_declara_las_piezas_elegidas(sistema):
    nucleo = Nucleo(sistema, ProcesosFalso(), catalogo=[])
    assert nucleo.abrir_swf_del_cdn("clothes1")["ok"]
    prendas = {p["clase"]: p for p in nucleo.prendas()["prendas"]}
    assert prendas["remera5"]["partes"] == {"cloth": "remera5_on", "arm": "remera5_brazo_on"}
    partes = {"grip": "anteojo1_on"}  # unos anteojos en la mano

    resultado = nucleo.trucar_prenda("remera5", "grip", "anteojo1_on")

    assert resultado["ok"], resultado
    assert nucleo.entregar_encode(resultado["encode"])["ok"]
    trucado = Path(reglas(sistema)[1]["Action"]).read_bytes()
    assert ItemsBaseFFDec().analizar(trucado, ["remera5"])["remera5"].partes == partes

    # Y con una Pieza de otro SWF (la corona de rey de costumes, probada en el juego).
    resultado = nucleo.trucar_prenda("remera5", "hats", "costumes.coronaRey_on")

    assert resultado["ok"], resultado
    assert nucleo.entregar_encode(resultado["encode"])["ok"]
    trucado = Path(reglas(sistema)[1]["Action"]).read_bytes()
    assert ItemsBaseFFDec().analizar(trucado, ["remera5"])["remera5"].partes == {"hats": "costumes.coronaRey_on"}

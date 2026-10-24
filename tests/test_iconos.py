import base64

import pytest

from mgitems.ffdec import FFDec, FFDecNoDisponible
from mgitems.iconos import ExportadorFFDec
from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf

PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
CLASES = ["remera5", "remera5_on", "remera5_brazo_on", "gorra1", "silla_so", "clothes1_fla.MainTimeline", "Remera6"]


class ExportadorFalso(ExportadorFFDec):
    """Escribe un PNG por símbolo pedido y registra cada llamada (sin Java)."""

    def __init__(self):
        super().__init__()
        self.llamadas: list[dict[int, str]] = []

    def exportar(self, swf, simbolos, destino, formato="png"):
        assert swf.is_file()
        self.llamadas.append(dict(simbolos))
        destino.mkdir(parents=True, exist_ok=True)
        for clase in simbolos.values():
            if formato == "svg":
                (destino / f"{clase}.svg").write_text(svg_como_ffdec(clase), encoding="utf-8")
            else:
                (destino / f"{clase}.png").write_bytes(PNG_MINIMO)


def svg_como_ffdec(clase: str) -> str:
    """Un SVG como los que exporta FFDec: el punto de anclaje en el <g transform> de afuera."""
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns:ffdec="https://www.free-decompiler.com/flash" xmlns:xlink="http://www.w3.org/1999/xlink" height="20.0px" width="30.0px" xmlns="http://www.w3.org/2000/svg">
  <g transform="matrix(1.0, 0.0, 0.0, 1.0, 15.0, 12.5)">
    <use ffdec:characterId="7" height="20.0" transform="matrix(1.0, 0.0, 0.0, 1.0, -15.0, -12.5)" width="30.0" xlink:href="#shape0"/>
  </g>
  <defs>
    <g id="shape0">
      <path d="M0.0 0.0 L30.0 0.0 30.0 20.0 0.0 20.0 Z" fill="url(#gradient0)" data-clase="{clase}"/>
    </g>
    <linearGradient id="gradient0"><stop offset="0" stop-color="#ff0000"/></linearGradient>
  </defs>
</svg>
'''


class SinJava(ExportadorFFDec):
    def exportar(self, swf, simbolos, destino, formato="png"):
        raise FFDecNoDisponible("No se encontró Java")


@pytest.fixture
def sistema(tmp_path):
    return SistemaFalso(tmp_path)


@pytest.fixture
def exportador():
    return ExportadorFalso()


@pytest.fixture
def nucleo(sistema, exportador, tmp_path):
    nucleo = Nucleo(sistema, catalogo=[], exportador=exportador)
    swf = tmp_path / "clothes1.swf"
    swf.write_bytes(crear_swf(CLASES))
    nucleo.abrir_swf(str(swf))
    return nucleo


def test_se_exportan_las_imagenes_de_los_items_y_las_piezas(nucleo, exportador):
    assert nucleo.preparar_iconos() == {"ok": True, "swf": "clothes1"}

    assert len(exportador.llamadas) == 1
    assert sorted(exportador.llamadas[0].values()) == ["Remera6", "gorra1", "remera5", "remera5_brazo_on", "remera5_on"]


def test_cada_item_encontrado_tiene_su_imagen(nucleo):
    nucleo.preparar_iconos()
    encontrados = nucleo.buscar_items("remera, gorra")["items"]

    iconos = nucleo.iconos(encontrados)["iconos"]

    assert set(iconos) == set(encontrados)
    assert all(icono == "data:image/png;base64," + base64.b64encode(PNG_MINIMO).decode() for icono in iconos.values())


def test_un_item_sin_imagen_devuelve_none(nucleo):
    nucleo.preparar_iconos()

    iconos = nucleo.iconos(["clothes1.noExiste", "otroSwf.remera"])["iconos"]

    assert iconos == {"clothes1.noExiste": None, "otroSwf.remera": None}


def test_las_imagenes_no_se_vuelven_a_exportar(nucleo, exportador, sistema, tmp_path):
    nucleo.preparar_iconos()
    nucleo.preparar_iconos()
    otra_vez = Nucleo(sistema, catalogo=[], exportador=exportador)
    otra_vez.abrir_swf(str(tmp_path / "clothes1.swf"))
    otra_vez.preparar_iconos()

    assert len(exportador.llamadas) == 1


def test_si_el_swf_cambio_se_vuelven_a_exportar(nucleo, exportador, tmp_path):
    nucleo.preparar_iconos()
    nuevo = tmp_path / "nuevo" / "clothes1.swf"
    nuevo.parent.mkdir()
    nuevo.write_bytes(crear_swf(["remera5", "zapato1"]))
    nucleo.abrir_swf(str(nuevo))

    nucleo.preparar_iconos()

    assert len(exportador.llamadas) == 2
    assert nucleo.iconos(["clothes1.zapato1"])["iconos"]["clothes1.zapato1"]
    assert nucleo.iconos(["clothes1.gorra1"])["iconos"]["clothes1.gorra1"] is None  # de la versión anterior


def test_imagenes_guardadas_por_una_version_anterior_del_programa_se_vuelven_a_exportar(nucleo, exportador, sistema):
    # Antes solo se exportaban los Items y la marca guardaba solo la versión del SWF.
    nucleo.preparar_iconos()
    carpeta = sistema.base / "Local" / "MGItems" / "iconos" / "clothes1"
    marca = carpeta / "version"
    marca.write_text(marca.read_text(encoding="utf-8").split()[0], encoding="utf-8")
    (carpeta / "remera5_on.png").unlink()

    nucleo.preparar_iconos()

    assert len(exportador.llamadas) == 2
    assert (carpeta / "remera5_on.png").exists()


def test_las_imagenes_quedan_en_la_carpeta_del_programa_y_no_hay_temporales(nucleo, sistema):
    nucleo.preparar_iconos()

    carpeta = sistema.base / "Local" / "MGItems" / "iconos" / "clothes1"
    assert sorted(p.name for p in carpeta.iterdir()) == [
        "Remera6.png", "gorra1.png", "remera5.png", "remera5_brazo_on.png", "remera5_on.png", "version",
    ]


def test_sin_java_se_informa_y_no_se_rompe_nada(sistema, tmp_path):
    nucleo = Nucleo(sistema, catalogo=[], exportador=SinJava())
    swf = tmp_path / "clothes1.swf"
    swf.write_bytes(crear_swf(CLASES))
    nucleo.abrir_swf(str(swf))

    resultado = nucleo.preparar_iconos()

    assert not resultado["ok"]
    assert resultado["sin_exportador"]
    assert "Java" in resultado["error"]
    assert nucleo.buscar_items("remera")["ok"]
    assert nucleo.iconos(["clothes1.remera5"])["iconos"] == {"clothes1.remera5": None}


def test_preparar_sin_swf_abierto_devuelve_error(sistema, exportador):
    assert not Nucleo(sistema, catalogo=[], exportador=exportador).preparar_iconos()["ok"]


def test_sugiere_items_por_lo_ultimo_que_se_escribio(nucleo):
    nucleo.preparar_iconos()

    resultado = nucleo.sugerir_items("gorra, rem")

    assert [i["ruta"] for i in resultado["items"]] == ["clothes1.remera5", "clothes1.Remera6"]
    assert all(i["icono"] for i in resultado["items"])
    assert resultado["total"] == 2


def test_las_sugerencias_funcionan_aunque_las_imagenes_no_esten_listas(nucleo):
    resultado = nucleo.sugerir_items("g")

    assert resultado["items"] == [{"ruta": "clothes1.gorra1", "icono": None}]


@pytest.mark.parametrize("texto", ["", "  ", "gorra, ", ","])
def test_sin_texto_no_hay_sugerencias(nucleo, texto):
    assert nucleo.sugerir_items(texto)["items"] == []


def test_sin_swf_abierto_no_hay_sugerencias(sistema, exportador):
    assert Nucleo(sistema, catalogo=[], exportador=exportador).sugerir_items("remera")["items"] == []


def test_las_sugerencias_tienen_un_limite(sistema, exportador, tmp_path):
    nucleo = Nucleo(sistema, catalogo=[], exportador=exportador)
    swf = tmp_path / "muchos.swf"
    swf.write_bytes(crear_swf([f"remera{i}" for i in range(80)]))
    nucleo.abrir_swf(str(swf))

    resultado = nucleo.sugerir_items("remera", limite=50)

    assert len(resultado["items"]) == 50
    assert resultado["total"] == 80


def test_se_preparan_las_imagenes_de_otro_swf_sin_cambiar_el_abierto(exportador, sistema, tmp_path):
    fuente = FuenteFalsa({"costumes": crear_swf(["coronaRey", "coronaRey_on"])})
    nucleo = Nucleo(sistema, catalogo=[], exportador=exportador, fuente=fuente)
    swf = tmp_path / "clothes1.swf"
    swf.write_bytes(crear_swf(CLASES))
    nucleo.abrir_swf(str(swf))

    assert nucleo.preparar_iconos("costumes")["ok"]

    assert sorted(exportador.llamadas[-1].values()) == ["coronaRey", "coronaRey_on"]
    assert nucleo.iconos(["costumes.coronaRey_on"])["iconos"]["costumes.coronaRey_on"]
    assert nucleo.piezas()["swf"] == "clothes1"


# --- Con FFDec de verdad ---

def _ffdec_disponible() -> bool:
    try:
        FFDec().programas()
    except FFDecNoDisponible:
        return False
    return True


@pytest.mark.skipif(not _ffdec_disponible(), reason="Hace falta Java y FFDec (scripts/obtener_binarios.py)")
def test_con_ffdec_real_cada_item_tiene_una_imagen_png(sistema, tmp_path):
    nucleo = Nucleo(sistema, catalogo=[])
    swf = tmp_path / "clothes1.swf"
    swf.write_bytes(crear_swf(["remera5", "remera5_on", "gorra1"], con_dibujos=True))
    nucleo.abrir_swf(str(swf))

    assert nucleo.preparar_iconos()["ok"]

    iconos = nucleo.iconos(["clothes1.remera5", "clothes1.gorra1"])["iconos"]
    for icono in iconos.values():
        png = base64.b64decode(icono.removeprefix("data:image/png;base64,"))
        assert png.startswith(b"\x89PNG")
    carpeta = sistema.base / "Local" / "MGItems" / "iconos" / "clothes1"
    assert (carpeta / "remera5_on.png").read_bytes().startswith(b"\x89PNG")  # la Pieza también


@pytest.mark.skipif(not _ffdec_disponible(), reason="Hace falta Java y FFDec (scripts/obtener_binarios.py)")
def test_con_ffdec_real_un_item_con_imagen_jpeg_no_corta_la_exportacion(sistema, tmp_path):
    # Con Java 9+, FFDec necesita acceso a un módulo interno para leer JPEG; sin él, el primer
    # JPEG aborta la exportación de todo el SWF.
    nucleo = Nucleo(sistema, catalogo=[])
    swf = tmp_path / "clothes1.swf"
    swf.write_bytes(crear_swf(["foto", "remera5", "gorra1"], con_dibujos=True, con_jpeg=("foto",)))
    nucleo.abrir_swf(str(swf))

    assert nucleo.preparar_iconos()["ok"]

    iconos = nucleo.iconos(["clothes1.foto", "clothes1.remera5", "clothes1.gorra1"])["iconos"]
    assert all(iconos.values()), iconos

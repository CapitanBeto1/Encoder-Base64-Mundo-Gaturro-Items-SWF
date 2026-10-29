"""Los dibujos del juego para las ventanas que imitan las suyas: se bajan de los banners del CDN, no vienen en el repo."""
import pytest

from mgitems.interfaz import BANNERS, DIBUJOS
from mgitems.nucleo import Nucleo
from fuente_falsa import FuenteFalsa
from sistema_falso import SistemaFalso
from swf_de_ejemplo import crear_swf
from test_iconos import ExportadorFalso


class ExportadorDeFormas(ExportadorFalso):
    def __init__(self):
        super().__init__()
        self.formas: list[dict[int, str]] = []

    def exportar_formas(self, swf, formas, destino):
        assert swf.is_file()
        self.formas.append(dict(formas))
        destino.mkdir(parents=True, exist_ok=True)
        for nombre in formas.values():
            (destino / f"{nombre}.svg").write_text(f'<svg height="70.0px" width="368.0px"><g>{nombre}</g></svg>', encoding="utf-8")


def banner(tamano: int) -> bytes:
    """Un SWF de ese tamaño (la versión del banner que se miró)."""
    swf = crear_swf(["asset"], "FWS")
    return swf + b"\0" * (tamano - len(swf))


@pytest.fixture
def exportador():
    return ExportadorDeFormas()


def nucleo_con(tmp_path, exportador, banners):
    fuente = FuenteFalsa({f"banners/{n}": data for n, data in banners.items()})
    return Nucleo(SistemaFalso(tmp_path), fuente=fuente, catalogo=[], exportador=exportador), fuente


def test_los_dibujos_se_bajan_del_juego_una_vez(tmp_path, exportador):
    nucleo, _ = nucleo_con(tmp_path, exportador, {n: banner(t) for n, t in BANNERS.items()})

    resultado = nucleo.dibujos_de_la_interfaz()

    assert resultado["ok"]
    assert set(resultado["dibujos"]) == set(DIBUJOS)
    assert 'viewBox="0 10 31 31"' in resultado["dibujos"]["paleta"]  # solo la paleta, sin el Gaturro pintor
    assert 'viewBox="260 0 108 70"' in resultado["dibujos"]["pintor"]  # del mismo dibujo, el pintor
    assert len(exportador.formas) == len(BANNERS)
    nucleo.dibujos_de_la_interfaz()
    assert len(exportador.formas) == len(BANNERS)  # la segunda vez, de lo guardado


def test_con_otra_version_del_banner_no_se_usan_sus_dibujos(tmp_path, exportador):
    nucleo, _ = nucleo_con(tmp_path, exportador, {"AvatarSaverBanner": banner(BANNERS["AvatarSaverBanner"] + 10),
                                                  "ColorPickerBanner": banner(BANNERS["ColorPickerBanner"])})

    dibujos = nucleo.dibujos_de_la_interfaz()["dibujos"]

    # Los del banner cambiado podrían ser otros dibujos: quedan los del programa.
    assert set(dibujos) == {n for n, (banner, _, _) in DIBUJOS.items() if banner == "ColorPickerBanner"}


def test_sin_conexion_quedan_los_del_programa(tmp_path, exportador):
    nucleo, fuente = nucleo_con(tmp_path, exportador, {})
    fuente.sin_conexion = True

    assert nucleo.dibujos_de_la_interfaz() == {"ok": True, "dibujos": {}}

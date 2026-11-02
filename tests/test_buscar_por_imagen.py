"""Búsqueda por imagen en el núcleo: bajar los datos la primera vez y buscar (con un modelo y huellas falsos)."""
import base64
import hashlib
import io
import json

import numpy as np
import pytest
from PIL import Image

from mgitems.busqueda import DatosBusqueda, Huellas
from mgitems.categorias import IndicePiezas
from mgitems.nucleo import Nucleo
from procesos_falso import ProcesosFalso
from sistema_falso import SistemaFalso


class ModeloFalso:
    """Resume cada imagen por su color promedio (como un modelo de verdad, imágenes parecidas → huellas parecidas)."""

    def huellas(self, imagenes):
        v = np.array([np.asarray(i.convert("RGB"), np.float32).reshape(-1, 3).mean(0) for i in imagenes])
        return v / np.linalg.norm(v, axis=1, keepdims=True)


def unitario(*v):
    v = np.array(v, np.float32)
    return v / np.linalg.norm(v)


class DatosFalsos:
    def __init__(self, listos=True):
        self._listos = listos
        self.huellas = Huellas(
            ["muebles.silla", "ropa.remera_on", "muebles.rota", "ropa.suelta_on", "muebles.mesa"],
            np.stack([unitario(1, 0, 0), unitario(1, 0.04, 0), unitario(0, 1, 0), unitario(0, 0, 1), unitario(0.7, 0.7, 0)]),
            {"ropa.remera_on": ["ropa.remera"]},
        )

    def listos(self):
        return self._listos

    def bajar(self, progreso):
        progreso(50, 100)
        self._listos = True

    def cargar(self):
        return ModeloFalso(), self.huellas


INDICE = {"swfs": {
    "muebles": {"items": {"silla": {"tipo": "casa", "destino": "casa"}, "mesa": {"tipo": "casa", "destino": "casa"},
                          "rota": {"tipo": "casa", "destino": "descartado"}}},
    "ropa": {"items": {"remera": {"tipo": "prenda", "destino": "guardarropa"}}},
}}


@pytest.fixture
def sistema(tmp_path):
    sistema = SistemaFalso(tmp_path)
    sistema.instalar_juego()
    sistema.instalar_fiddler()
    return sistema


def nucleo_con(sistema, tmp_path, datos):
    (tmp_path / "indice.json").write_text(json.dumps(INDICE), encoding="utf-8")
    return Nucleo(sistema, ProcesosFalso(), catalogo=[], indice=IndicePiezas(tmp_path / "indice.json"), datos_busqueda=datos)


def captura(color, tamano=(40, 30)) -> str:
    salida = io.BytesIO()
    Image.new("RGB", tamano, color).save(salida, "PNG")
    return "data:image/png;base64," + base64.b64encode(salida.getvalue()).decode()


def test_encuentra_el_item_mas_parecido(sistema, tmp_path):
    nucleo = nucleo_con(sistema, tmp_path, DatosFalsos())

    resultado = nucleo.buscar_por_imagen(captura((255, 0, 0)))

    assert resultado["ok"], resultado
    primero = resultado["resultados"][0]
    assert (primero["ruta"], primero["swf"], primero["tipo"], primero["destino"]) == ("muebles.silla", "muebles", "casa", "casa")
    rutas = [r["ruta"] for r in resultado["resultados"]]
    assert "muebles.rota" not in rutas  # el juego lo descarta
    assert "ropa.suelta_on" not in rutas  # una Pieza que ningún Item viste no se recibe


def test_lo_que_se_ve_puesto_lleva_a_la_prenda(sistema, tmp_path):
    nucleo = nucleo_con(sistema, tmp_path, DatosFalsos())
    lienzo = Image.new("RGB", (100, 100), (0, 0, 255))
    lienzo.paste((255, 10, 0), (20, 20, 60, 60))  # lo de adentro del rectángulo es lo que importa
    salida = io.BytesIO()
    lienzo.save(salida, "PNG")

    resultado = nucleo.buscar_por_imagen(base64.b64encode(salida.getvalue()).decode(), [20, 20, 60, 60])

    remera = next(r for r in resultado["resultados"] if r["ruta"] == "ropa.remera")
    assert remera["por_pieza"] == "ropa.remera_on" and remera["tipo"] == "prenda"


def test_los_del_cache_del_juego_van_un_poco_mas_arriba(sistema, tmp_path):
    cache = sistema.base / "Roaming" / "MundoGaturro" / "Cache"
    (cache / "data_1").write_bytes(b"\x00https://cdn-ar.mundogaturro.com/juego/assets/ropa.swf?123\x00")
    nucleo = nucleo_con(sistema, tmp_path, DatosFalsos())

    resultados = nucleo.buscar_por_imagen(captura((255, 0, 0)))["resultados"]

    # La remera se parece casi igual que la silla, y su SWF lo bajó el juego (se vio hace poco).
    assert [r["ruta"] for r in resultados[:2]] == ["ropa.remera", "muebles.silla"]
    assert resultados[0]["en_cache"] and not resultados[1]["en_cache"]
    # Lo que se parece mucho menos no se adelanta por estar en el caché.
    assert resultados[-1]["ruta"] == "muebles.mesa" or "muebles.mesa" in [r["ruta"] for r in resultados[2:]]


def test_sin_los_datos_primero_hay_que_bajarlos(sistema, tmp_path):
    datos = DatosFalsos(listos=False)
    nucleo = nucleo_con(sistema, tmp_path, datos)

    antes = nucleo.buscar_por_imagen(captura((255, 0, 0)))
    estado = nucleo.estado_busqueda()
    preparado = nucleo.preparar_busqueda()

    assert not antes["ok"] and antes["faltan_datos"]
    assert estado["ok"] and not estado["listos"] and estado["tamano"] > 100_000_000
    assert preparado["ok"] and nucleo.estado_busqueda()["listos"]
    assert nucleo.progreso_busqueda() == {"ok": True, "bajando": False, "hechos": 50, "total": 100}
    assert nucleo.buscar_por_imagen(captura((255, 0, 0)))["ok"]


def test_una_imagen_que_no_se_puede_leer(sistema, tmp_path):
    nucleo = nucleo_con(sistema, tmp_path, DatosFalsos())

    assert "No se pudo leer la imagen" in nucleo.buscar_por_imagen("esto no es una imagen")["error"]
    assert "muy chico" in nucleo.buscar_por_imagen(captura((1, 2, 3)), [0, 0, 2, 2])["error"]


# --- Bajar los datos ---

def test_baja_los_datos_y_verifica_que_no_esten_danados(tmp_path):
    contenido = {"modelo.onnx": b"m" * 3000, "huellas.npz": b"h" * 500}
    archivos = {n: (len(c), hashlib.sha256(c).hexdigest()) for n, c in contenido.items()}
    pedidos = []

    def abrir(url):
        pedidos.append(url)
        return io.BytesIO(contenido[url.rsplit("/", 1)[1]])

    datos = DatosBusqueda(tmp_path / "busqueda", archivos, "https://ejemplo/datos/", abrir)
    avances = []

    assert not datos.listos()
    datos.bajar(lambda hechos, total: avances.append(hechos))
    assert datos.listos() and (tmp_path / "busqueda" / "modelo.onnx").read_bytes() == contenido["modelo.onnx"]
    assert pedidos == ["https://ejemplo/datos/modelo.onnx", "https://ejemplo/datos/huellas.npz"]
    assert avances[-1] == 3500
    datos.bajar()  # ya están: no se vuelven a pedir
    assert len(pedidos) == 2


def test_si_un_archivo_llega_danado_no_queda(tmp_path):
    archivos = {"modelo.onnx": (4, hashlib.sha256(b"bien").hexdigest())}
    datos = DatosBusqueda(tmp_path, archivos, "https://ejemplo/", lambda url: io.BytesIO(b"malo"))

    with pytest.raises(ValueError):
        datos.bajar()
    assert not datos.listos() and not list(tmp_path.glob("*.part"))

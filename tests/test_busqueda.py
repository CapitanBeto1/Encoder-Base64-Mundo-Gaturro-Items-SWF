"""Búsqueda por imagen: preparar las imágenes y comparar huellas (sin el modelo)."""
import io

import numpy as np
import pytest
from PIL import Image

from mgitems.busqueda import Huellas, abrir_captura, abrir_encuadres, con_fondo, espejada, preparar


def png(imagen: Image.Image) -> bytes:
    salida = io.BytesIO()
    imagen.save(salida, "PNG")
    return salida.getvalue()


def test_prepara_la_imagen_como_la_espera_el_modelo():
    x = preparar(Image.new("RGB", (300, 100), (255, 255, 255)))

    assert x.shape == (3, 224, 224) and x.dtype == np.float32
    assert np.allclose(x[0], (1 - 0.48145466) / 0.26862954)  # blanco, normalizado como en el entrenamiento


def test_una_referencia_se_recorta_a_su_dibujo_sobre_blanco():
    imagen = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    imagen.paste((255, 0, 0, 255), (10, 20, 30, 25))

    recortada = con_fondo(imagen)

    assert recortada.size == (20, 5) and recortada.getpixel((0, 0)) == (255, 0, 0)
    assert con_fondo(Image.new("RGBA", (5, 5), (0, 0, 0, 0))) is None  # vacía


def test_la_captura_se_recorta_al_rectangulo_marcado():
    captura = Image.new("RGB", (100, 80), (0, 0, 255))
    captura.paste((0, 255, 0), (40, 30, 60, 50))

    entera = abrir_captura(png(captura))
    marcada = abrir_captura(png(captura), (60, 50, 40, 30))  # al revés también sirve

    assert entera.size == (100, 80)
    assert marcada.size == (20, 20) and marcada.getpixel((5, 5)) == (0, 255, 0)
    assert espejada(marcada).size == (20, 20)
    with pytest.raises(ValueError):
        abrir_captura(b"esto no es una imagen")
    with pytest.raises(ValueError):
        abrir_captura(png(captura), (10, 10, 11, 11))  # muy chico


def test_las_huellas_se_guardan_y_ordenan_por_parecido(tmp_path):
    huellas = Huellas(["casa.silla", "ropa.remera_on", "ropa.remera"],
                      np.array([[1, 0, 0], [0, 1, 0], [0, 0.8, 0.6]], np.float32), {"ropa.remera_on": ["ropa.remera"]})
    archivo = tmp_path / "huellas.npz"

    huellas.guardar(archivo)
    leidas = Huellas.leer(archivo)
    # La captura y su espejo: cuenta el más parecido de los dos.
    parecidos = leidas.parecidos(np.array([[0, 1, 0], [0.9, 0, 0]], np.float32))

    assert [r for r, _ in parecidos] == ["ropa.remera_on", "casa.silla", "ropa.remera"]
    assert parecidos[0][1] == pytest.approx(1)
    assert leidas.prendas_de_pieza == {"ropa.remera_on": ["ropa.remera"]}



def test_con_rectangulo_tambien_se_compara_mas_amplio():
    captura = Image.new("RGB", (100, 100), (0, 0, 255))

    encuadres = abrir_encuadres(png(captura), (40, 40, 60, 60))
    entera = abrir_encuadres(png(captura))

    assert [e.size for e in encuadres] == [(20, 20), (30, 30), (44, 44)]  # el marcado, +25 % y +60 % por lado
    assert [e.size for e in entera] == [(100, 100)]
    assert abrir_encuadres(png(captura), (0, 0, 100, 100))[1].size == (100, 100)  # no se sale de la imagen

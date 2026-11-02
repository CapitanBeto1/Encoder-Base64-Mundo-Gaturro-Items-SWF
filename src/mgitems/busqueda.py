"""Búsqueda por imagen: qué Items y Piezas se parecen más a una captura del juego.

Cada imagen (el primer cuadro de un Item o una Pieza, o la captura) se resume en una huella: 512 números que
calcula la parte de imágenes de CLIP ViT-B/32 (OpenCLIP, entrenado por LAION), exportada a ONNX y comprimida.
Dos imágenes que se parecen tienen huellas parecidas (el producto entre ellas, cercano a 1). Las huellas de todas
las imágenes de referencia las arma `scripts/armar_busqueda.py`; el programa solo calcula la de la captura.

Probado con capturas reales (#116): el correcto quedó primero en 7 de 9. Comparar también la captura espejada
(en las casas los objetos se pueden girar) no empeora nada.
"""

import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ARCHIVO_MODELO = "clip_visual_int8.onnx"
ARCHIVO_HUELLAS = "huellas_busqueda.npz"
VERSION_DATOS = 1  # sube si cambia la forma de las huellas o el modelo

LADO = 224
# La normalización con la que se entrenó CLIP.
_MEDIA = np.array([0.48145466, 0.4578275, 0.40821073], np.float32)
_DESVIO = np.array([0.26862954, 0.26130258, 0.27577711], np.float32)


def preparar(imagen: Image.Image) -> np.ndarray:
    """La imagen como la espera el modelo: el lado corto a 224 (bicúbica), el centro de 224×224, normalizada,
    con los canales primero. Igual que `open_clip` (con el que se probó)."""
    imagen = imagen.convert("RGB")
    ancho, alto = imagen.size
    escala = LADO / min(ancho, alto)
    imagen = imagen.resize((max(LADO, round(ancho * escala)), max(LADO, round(alto * escala))), Image.BICUBIC)
    ancho, alto = imagen.size
    izquierda, arriba = (ancho - LADO) // 2, (alto - LADO) // 2
    x = np.asarray(imagen.crop((izquierda, arriba, izquierda + LADO, arriba + LADO)), np.float32) / 255
    return ((x - _MEDIA) / _DESVIO).transpose(2, 0, 1)


def con_fondo(imagen: Image.Image) -> Image.Image | None:
    """Una imagen de referencia (con transparencia) recortada a lo que tiene dibujo, sobre blanco; None si está
    vacía."""
    imagen = imagen.convert("RGBA")
    caja = imagen.getchannel("A").getbbox()
    if not caja:
        return None
    imagen = imagen.crop(caja)
    lienzo = Image.new("RGBA", imagen.size, (255, 255, 255, 255))
    lienzo.alpha_composite(imagen)
    return lienzo.convert("RGB")


def abrir_captura(data: bytes, recorte: tuple[int, int, int, int] | None = None) -> Image.Image:
    """La captura (PNG, JPG…) como imagen RGB, recortada al rectángulo que marcó el jugador si lo hay.
    ValueError si no es una imagen o el rectángulo no tiene nada."""
    try:
        imagen = Image.open(io.BytesIO(data))
        imagen.load()
    except (OSError, Image.DecompressionBombError) as e:
        raise ValueError("no es una imagen") from e
    imagen = imagen.convert("RGB")
    if recorte:
        x0, y0, x1, y1 = (int(v) for v in recorte)
        x0, x1 = sorted((max(0, x0), min(imagen.width, x1)))
        y0, y1 = sorted((max(0, y0), min(imagen.height, y1)))
        if x1 - x0 < 4 or y1 - y0 < 4:
            raise ValueError("el rectángulo es muy chico")
        imagen = imagen.crop((x0, y0, x1, y1))
    return imagen


def espejada(imagen: Image.Image) -> Image.Image:
    return ImageOps.mirror(imagen)


class Modelo:
    """La parte de imágenes de CLIP, con onnxruntime: imágenes → huellas (normalizadas)."""

    def __init__(self, archivo: Path):
        import onnxruntime  # tarda en importarse: solo cuando se busca

        opciones = onnxruntime.SessionOptions()
        opciones.log_severity_level = 3
        self._sesion = onnxruntime.InferenceSession(str(archivo), opciones, providers=["CPUExecutionProvider"])

    def huellas(self, imagenes: list[Image.Image]) -> np.ndarray:
        return self._sesion.run(None, {"imagen": np.stack([preparar(i) for i in imagenes])})[0].astype(np.float32)


class Huellas:
    """Las huellas de las imágenes de referencia (`scripts/armar_busqueda.py`): `rutas` ("swf.Clase", de Items
    y de Piezas), `huellas` (una fila cada una) y `prendas_de_pieza` (Pieza → las Prendas que la usan)."""

    def __init__(self, rutas: list[str], huellas: np.ndarray, prendas_de_pieza: dict[str, list[str]]):
        self.rutas, self.huellas, self.prendas_de_pieza = rutas, huellas, prendas_de_pieza

    @classmethod
    def leer(cls, archivo: Path) -> "Huellas":
        with np.load(archivo, allow_pickle=False) as datos:
            if int(datos["version"]) != VERSION_DATOS:
                raise ValueError("las huellas son de otra versión")
            return cls([str(r) for r in datos["rutas"]], datos["huellas"].astype(np.float32),
                       json.loads(str(datos["prendas_de_pieza"])))

    def guardar(self, archivo: Path) -> None:
        np.savez_compressed(archivo, version=np.array(VERSION_DATOS), rutas=np.array(self.rutas),
                            huellas=self.huellas.astype(np.float16),
                            prendas_de_pieza=np.array(json.dumps(self.prendas_de_pieza, ensure_ascii=False)))

    def parecidos(self, consultas: np.ndarray) -> list[tuple[str, float]]:
        """Todas las referencias de la más a la menos parecida a cualquiera de las `consultas` (la captura y su
        espejo), con su parecido (de -1 a 1)."""
        puntajes = (self.huellas @ consultas.T).max(axis=1)
        orden = np.argsort(-puntajes)
        return [(self.rutas[i], float(puntajes[i])) for i in orden]

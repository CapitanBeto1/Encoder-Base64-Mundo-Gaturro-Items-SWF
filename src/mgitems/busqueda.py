"""Búsqueda por imagen: qué Items y Piezas se parecen más a una captura del juego.

Cada imagen (un cuadro de un Item o una Pieza, o la captura) se resume en huellas: números que calcula un modelo de
imágenes, exportado a ONNX y comprimido. Dos imágenes que se parecen tienen huellas parecidas (el producto entre
ellas, cercano a 1). Las huellas de todas las imágenes de referencia las arma `scripts/armar_busqueda.py`; el
programa solo calcula las de la captura.

Son dos modelos, porque ven cosas distintas: CLIP ViT-B/32 (OpenCLIP, entrenado por LAION) ve de qué se trata el
dibujo, y DINOv2 (de Meta, el chico) ve sus detalles, aunque tenga otros colores o esté tapado en parte: los brackets
de `virtualGoods3.brackets` con anteojos encima, o el casco de `espacio.gorroGalactico` teñido de negro, que CLIP dejaba
más allá del puesto 100 y DINOv2 deja entre los 10 primeros. Cada uno ordena las referencias, y se juntan por puestos
(ver `Huellas.parecidos`): queda arriba lo que cualquiera de los dos ve muy parecido.

Probado con capturas reales (#116): el correcto quedó primero en 7 de 9. Comparar también la captura espejada
(en las casas los objetos se pueden girar) no empeora nada.
"""

import io
import json
from pathlib import Path

import importlib.util

import numpy as np
from PIL import Image, ImageOps

ARCHIVO_MODELO = "clip_visual_int8.onnx"
ARCHIVO_MODELO_DINO = "dinov2_small.onnx"
ARCHIVO_HUELLAS = "huellas_busqueda.npz"
# Sube si cambia la forma de las huellas o un modelo. 2: en int8, con los pedazos de los dibujos. 3: también DINOv2.
VERSION_DATOS = 3
# La fusión por puestos: cada modelo le suma a una referencia 1/(FUSION + su puesto en ese modelo). Con 5, lo primero
# de cada lista pesa mucho más que lo que viene después (medido con capturas de prueba y las reales que fallaban).
FUSION = 5

# «¿Qué es?»: a qué se limita la búsqueda. La ropa, por la Parte del cuerpo donde va (cuenta la Prenda y lo que se
# ve puesto): solo las Prendas que van únicamente ahí, porque el ícono de un disfraz es un Gaturro entero y se
# parece a cualquier captura de ropa puesta; los disfraces (3 Partes o más), aparte. Lo demás, por el tipo de Item.
QUE_ES = {
    "hats": ("Gorro o sombrero", {"partes": {"hats"}}),
    "hairs": ("Pelo", {"partes": {"hairs"}}),
    "mouths": ("Cara o boca", {"partes": {"mouths"}}),
    "accesories": ("Accesorio (anteojos, máscara…)", {"partes": {"accesories", "accesories2"}}),
    "neck": ("Cuello", {"partes": {"neck"}}),
    "cloth": ("Remera o torso", {"partes": {"cloth", "arm", "clothFront"}}),
    "clothBack": ("Espalda (alas, capa…)", {"partes": {"clothBack"}}),
    "grip": ("En la mano", {"partes": {"grip", "gripFore", "gripBack"}}),
    "leg": ("Pantalón o pollera", {"partes": {"leg"}}),
    "foot": ("Zapatos", {"partes": {"foot"}}),
    "disfraz": ("Disfraz (varias partes)", {"disfraz": True}),
    "transporte": ("Transporte", {"tipos": {"transporte"}}),
    # Por adónde llega (lo que dice cada resultado), no por su tipo: un dibujo del juego («Otro») llega a la casa, y
    # algunos objetos de la casa, a la mochila.
    "casa": ("De la casa", {"destinos": {"casa"}}),
    "mochila": ("De la mochila", {"destinos": {"mochila"}}),
    "mascota": ("De mascota", {"tipos": {"mascota", "ropa_mascota", "comida_mascota", "juguete_mascota", "cuidado_mascota"}}),
}

# Cuánto se acerca la búsqueda a lo que se marcó «Se parece» y cuánto se aleja de lo descartado (la huella de la
# captura vale 1).
PESO_SE_PARECE = 0.8
PESO_DESCARTADO = 0.25


def guiar(consultas: np.ndarray, se_parece: np.ndarray, descartados: np.ndarray) -> np.ndarray:
    """Las huellas de la captura (y su espejo) corridas hacia lo que se parece y lejos de lo descartado."""
    guiadas = consultas.astype(np.float32).copy()
    if len(se_parece):
        guiadas += PESO_SE_PARECE * se_parece.mean(axis=0)
    if len(descartados):
        guiadas -= PESO_DESCARTADO * descartados.mean(axis=0)
    return guiadas / np.linalg.norm(guiadas, axis=1, keepdims=True)


LADO = 224
# La normalización con la que se entrenó CLIP.
_MEDIA = np.array([0.48145466, 0.4578275, 0.40821073], np.float32)
_DESVIO = np.array([0.26862954, 0.26130258, 0.27577711], np.float32)


def preparar_dino(imagen: Image.Image) -> np.ndarray:
    """La imagen como la espera DINOv2: el lado corto a 256 (bicúbica), el centro de 224×224, normalizada como ImageNet,
    con los canales primero."""
    imagen = imagen.convert("RGB")
    ancho, alto = imagen.size
    escala = 256 / min(ancho, alto)
    imagen = imagen.resize((max(256, round(ancho * escala)), max(256, round(alto * escala))), Image.BICUBIC)
    ancho, alto = imagen.size
    izquierda, arriba = (ancho - LADO) // 2, (alto - LADO) // 2
    x = np.asarray(imagen.crop((izquierda, arriba, izquierda + LADO, arriba + LADO)), np.float32) / 255
    return ((x - _MEDIA_IMAGENET) / _DESVIO_IMAGENET).transpose(2, 0, 1)


_MEDIA_IMAGENET = np.array([0.485, 0.456, 0.406], np.float32)
_DESVIO_IMAGENET = np.array([0.229, 0.224, 0.225], np.float32)


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


def con_fondo(imagen: Image.Image, fondo: tuple[int, int, int] = (255, 255, 255)) -> Image.Image | None:
    """Una imagen de referencia (con transparencia) recortada a lo que tiene dibujo, sobre `fondo` (blanco); None si
    está vacía."""
    imagen = imagen.convert("RGBA")
    caja = imagen.getchannel("A").getbbox()
    if not caja:
        return None
    imagen = imagen.crop(caja)
    lienzo = Image.new("RGBA", imagen.size, (*fondo, 255))
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


# Además del rectángulo que marcó el jugador, el mismo rectángulo más grande: una captura de ropa puesta se parece a
# su Pieza dibujada puesta solo si se ve un poco del Gaturro alrededor (como en las referencias), y es difícil marcarlo
# justo así. Con los tres, el pantalón de un traje quedó 1.º o 2.º con cualquier rectángulo (#125).
AMPLIACIONES = (0.25, 0.6)


def abrir_encuadres(data: bytes, recorte: tuple[int, int, int, int] | None = None) -> list[Image.Image]:
    """Las imágenes a comparar de una captura: el rectángulo marcado y el mismo más grande (ver `AMPLIACIONES`), o
    la captura entera si no se marcó ninguno. ValueError como `abrir_captura`."""
    marcada = abrir_captura(data, recorte)
    if not recorte:
        return [marcada]
    entera = abrir_captura(data)
    x0, x1 = sorted(int(v) for v in (recorte[0], recorte[2]))
    y0, y1 = sorted(int(v) for v in (recorte[1], recorte[3]))
    ancho, alto = x1 - x0, y1 - y0
    return [marcada] + [entera.crop((max(0, round(x0 - ancho * f)), max(0, round(y0 - alto * f)),
                                     min(entera.width, round(x1 + ancho * f)), min(entera.height, round(y1 + alto * f))))
                        for f in AMPLIACIONES]


def espejada(imagen: Image.Image) -> Image.Image:
    return ImageOps.mirror(imagen)


FALTA_ONNXRUNTIME = (
    "La búsqueda por imagen necesita onnxruntime, que no está instalado. Instalalo con "
    "«python -m pip install onnxruntime». Si pip no lo encuentra, este Python no lo admite: hace falta uno de "
    "64 bits y de una versión que onnxruntime ya admita. El resto del programa funciona igual sin él."
)


def hay_onnxruntime() -> bool:
    """Si está onnxruntime, sin importarlo (tarda)."""
    return importlib.util.find_spec("onnxruntime") is not None


class Modelo:
    """La parte de imágenes de CLIP, con onnxruntime: imágenes → huellas (normalizadas)."""

    ENTRADA = "imagen"

    def __init__(self, archivo: Path):
        try:
            import onnxruntime  # tarda en importarse: solo cuando se busca
        except ImportError as e:
            raise RuntimeError(FALTA_ONNXRUNTIME) from e

        opciones = onnxruntime.SessionOptions()
        opciones.log_severity_level = 3
        self._sesion = onnxruntime.InferenceSession(str(archivo), opciones, providers=["CPUExecutionProvider"])

    def huellas(self, imagenes: list[Image.Image]) -> np.ndarray:
        return self._sesion.run(None, {self.ENTRADA: np.stack([preparar(i) for i in imagenes])})[0].astype(np.float32)


class ModeloDino(Modelo):
    """DINOv2 (el chico), con onnxruntime: la huella es su token de clase, normalizado. Sin comprimir: comprimido a
    int8 pierde justo los detalles por los que está."""

    ENTRADA = "pixel_values"

    def huellas(self, imagenes: list[Image.Image]) -> np.ndarray:
        salida = self._sesion.run(None, {self.ENTRADA: np.stack([preparar_dino(i) for i in imagenes])})[0]
        clase = salida[:, 0].astype(np.float32)
        return clase / np.linalg.norm(clase, axis=1, keepdims=True)


# Los modelos, en el orden de sus huellas en `Huellas`.
MODELOS = ((ARCHIVO_MODELO, Modelo), (ARCHIVO_MODELO_DINO, ModeloDino))


# Lo que vale menos un pedazo de un dibujo que el dibujo entero: así, si se parecen igual, gana el entero, y un
# pedazo solo gana cuando lo que se ve en la captura es de verdad un pedazo (el cartel de pruebas.caballo).
PENALIDAD_PEDAZO = 0.02


class Huellas:
    """Las huellas de las imágenes de referencia (`scripts/armar_busqueda.py`): `rutas` ("swf.Clase", de Items
    y de Piezas; una misma ruta puede estar varias veces: suelta, dibujada puesta en el Gaturro y en pedazos),
    `huellas` (las de cada modelo de `MODELOS`, una fila por imagen; en float32 o, como en el archivo, en int8 con
    `escalas`, una por fila), `prendas_de_pieza` (Pieza → las Prendas que la usan) y `pedazos` (qué filas son de un
    pedazo de un dibujo)."""

    # Filas que se comparan por vez: las huellas en int8 se pasan a float32 de a pedazos (enteras serían ~280 MB más).
    BLOQUE = 16384

    def __init__(self, rutas: list[str], huellas: list[np.ndarray], prendas_de_pieza: dict[str, list[str]],
                 pedazos: np.ndarray | None = None, escalas: list[np.ndarray] | None = None):
        self.rutas, self.huellas, self.prendas_de_pieza = rutas, list(huellas), prendas_de_pieza
        self.escalas = list(escalas) if escalas is not None else [None] * len(self.huellas)
        self.pedazos = np.zeros(len(rutas), bool) if pedazos is None else pedazos.astype(bool)
        self._unicas = list(dict.fromkeys(rutas))
        indice = {r: i for i, r in enumerate(self._unicas)}
        self._de_ruta = np.array([indice[r] for r in rutas], np.int64)

    @classmethod
    def leer(cls, archivo: Path) -> "Huellas":
        with np.load(archivo, allow_pickle=False) as datos:
            if int(datos["version"]) != VERSION_DATOS:
                raise ValueError("las huellas son de otra versión")
            cuantas = sum(1 for clave in datos.files if clave.startswith("huellas_"))
            return cls([str(r) for r in datos["rutas"]], [datos[f"huellas_{n}"] for n in range(cuantas)],
                       json.loads(str(datos["prendas_de_pieza"])), datos["pedazos"],
                       [datos[f"escalas_{n}"].astype(np.float32) for n in range(cuantas)])

    def _de_modelo(self, n: int, filas=slice(None)) -> np.ndarray:
        """Las huellas del modelo `n` (solo esas `filas`) en float32."""
        huellas = self.huellas[n][filas].astype(np.float32)
        if self.escalas[n] is not None:
            np.multiply(huellas, self.escalas[n][filas][:, None], out=huellas)
        return huellas

    def guardar(self, archivo: Path) -> None:
        """En int8, con una escala por fila (la mitad que en float16): para comparar parecidos alcanza y sobra."""
        por_modelo = {}
        for n in range(len(self.huellas)):
            huellas = self._de_modelo(n)
            escalas = np.maximum(np.abs(huellas).max(axis=1), 1e-8) / 127
            por_modelo |= {f"huellas_{n}": np.round(huellas / escalas[:, None]).astype(np.int8), f"escalas_{n}": escalas.astype(np.float16)}
        np.savez_compressed(archivo, version=np.array(VERSION_DATOS), rutas=np.array(self.rutas), **por_modelo,
                            prendas_de_pieza=np.array(json.dumps(self.prendas_de_pieza, ensure_ascii=False)),
                            pedazos=self.pedazos)

    def de_items(self, items: set[str]) -> list[np.ndarray]:
        """Las huellas (de cada modelo) de las imágenes de estos Items: la suya y las de las Piezas que visten."""
        filas = [i for i, r in enumerate(self.rutas) if r in items or items & set(self.prendas_de_pieza.get(r, ()))]
        return [self._de_modelo(n, filas) if filas else np.zeros((0, h.shape[1]), np.float32) for n, h in enumerate(self.huellas)]

    def parecidos(self, consultas: list[np.ndarray]) -> list[tuple[str, float]]:
        """Cada ruta, de la más a la menos parecida a las `consultas` (las de cada modelo: la captura y su espejo), con
        su parecido (de -1 a 1, el mejor de sus imágenes y de los modelos; un pedazo, con `PENALIDAD_PEDAZO` de menos).

        Con un modelo, en el orden de su parecido. Con varios, por sus puestos: cada uno le suma a cada ruta
        1/(`FUSION` + el puesto que le da), así queda arriba lo que cualquiera ve muy parecido."""
        por_ruta = []
        for n, consulta in enumerate(consultas):
            puntajes = np.zeros(len(self.rutas), np.float32)
            for desde in range(0, len(self.rutas), self.BLOQUE):
                hasta = desde + self.BLOQUE
                puntajes[desde:hasta] = (self._de_modelo(n, slice(desde, hasta)) @ consulta.T).max(axis=1)
            puntajes -= PENALIDAD_PEDAZO * self.pedazos
            mejor = np.full(len(self._unicas), -np.inf, np.float32)
            np.maximum.at(mejor, self._de_ruta, puntajes)
            por_ruta.append(mejor)
        parecido = np.max(por_ruta, axis=0)
        if len(por_ruta) == 1:
            orden = np.argsort(-parecido, kind="stable")
        else:
            fusion = np.zeros(len(self._unicas))
            for mejor in por_ruta:
                puesto = np.empty(len(mejor), np.int64)
                puesto[np.argsort(-mejor, kind="stable")] = np.arange(1, len(mejor) + 1)
                fusion += 1 / (FUSION + puesto)
            orden = np.argsort(-fusion, kind="stable")
        return [(self._unicas[i], float(parecido[i])) for i in orden]


# Dónde se publican los datos (el release de datos del repositorio) y cómo se reconocen.
URL_DATOS = "https://github.com/CapitanBeto1/Encoder-Base64-Mundo-Gaturro-Items-SWF/releases/download/datos-busqueda-v4/"
ARCHIVOS = {  # archivo → (tamaño, sha256)
    ARCHIVO_MODELO: (88890796, "02f827b5fa300a3013b9e077314098e5f02a2449afdf1900b3712fce22432e8a"),
    ARCHIVO_MODELO_DINO: (88459888, "83141175ec78b4ff9a2bb58a4c7c264ba0054d1c2e122e5a8114b79a8d4179ea"),
    ARCHIVO_HUELLAS: (53558810, "da60c360ddb256c40b77d323338133257fcb3b1a25c8b116d61170eac6210608"),  # v4: de los dos modelos
}


class DatosBusqueda:
    """Los modelos y las huellas en la carpeta del programa: se bajan del release de datos la primera vez."""

    def __init__(self, carpeta: Path, archivos: dict[str, tuple[int, str]] = ARCHIVOS, url: str = URL_DATOS, abrir=None):
        self._carpeta, self._archivos, self._url = carpeta, archivos, url
        self._abrir = abrir or _abrir_url
        self._cargados: tuple[list[Modelo], Huellas] | None = None

    def _falta(self, nombre: str, tamano: int) -> bool:
        archivo = self._carpeta / nombre
        return not (archivo.is_file() and archivo.stat().st_size == tamano)

    def listos(self) -> bool:
        """Si están todos los archivos, completos (el hash se verifica al bajarlos)."""
        return not self.por_bajar()

    def por_bajar(self) -> int:
        """Los bytes que falta bajar: todo la primera vez; con los datos de una versión anterior, solo lo que cambió."""
        return sum(t for n, (t, _) in self._archivos.items() if self._falta(n, t))

    def bajar(self, progreso=lambda hechos, total: None) -> None:
        """Baja lo que falta y verifica su hash; `progreso` va de 0 a `por_bajar`. OSError si no se pudo; ValueError si
        llegó dañado."""
        import hashlib

        self._carpeta.mkdir(parents=True, exist_ok=True)
        hechos, total = 0, self.por_bajar()
        for nombre, (tamano, sha) in self._archivos.items():
            if not self._falta(nombre, tamano):
                continue
            destino = self._carpeta / nombre
            parcial, suma = destino.with_suffix(destino.suffix + ".part"), hashlib.sha256()
            with self._abrir(self._url + nombre) as respuesta, parcial.open("wb") as salida:
                while bloque := respuesta.read(1 << 20):
                    salida.write(bloque)
                    suma.update(bloque)
                    hechos += len(bloque)
                    progreso(hechos, total)
            if suma.hexdigest() != sha:
                parcial.unlink(missing_ok=True)
                raise ValueError(f"{nombre} llegó dañado")
            parcial.replace(destino)
        self._cargados = None

    def cargar(self) -> tuple[list["Modelo"], Huellas]:
        """Los modelos (en el orden de `MODELOS`) y las huellas (se leen una vez)."""
        if self._cargados is None:
            self._cargados = ([clase(self._carpeta / archivo) for archivo, clase in MODELOS],
                              Huellas.leer(self._carpeta / ARCHIVO_HUELLAS))
        return self._cargados

    def soltar(self) -> None:
        """Deja de tener cargados los modelos y las huellas (unos 300 MB): se vuelven a leer en la próxima búsqueda."""
        self._cargados = None


def _abrir_url(url: str):
    import ssl
    import urllib.request

    pedido = urllib.request.Request(url, headers={"User-Agent": "MGItems"})
    return urllib.request.urlopen(pedido, timeout=60, context=ssl.create_default_context())

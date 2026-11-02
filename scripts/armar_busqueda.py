"""Arma los datos de la búsqueda por imagen: el modelo comprimido y las huellas de todas las imágenes del juego.

1. Exporta la parte de imágenes de CLIP ViT-B/32 (OpenCLIP, pesos de LAION) a ONNX y la comprime a int8.
   Necesita torch y open_clip, solo para este paso: `pip install -e ".[busqueda]"`.
2. Exporta con FFDec el primer cuadro de cada Item y cada Pieza de los SWF del índice.
3. Anota qué Items visten cada Pieza (sus `clothes` o sus `adds`), para mostrar el Item cuando lo más parecido
   es una Pieza (lo que se ve puesto en un Gaturro).
4. Calcula la huella de cada imagen con el mismo modelo y preprocesamiento que usa el programa (`mgitems.busqueda`).

Escribe en `<trabajo>/datos/` los dos archivos que se publican en el release de datos del repositorio
(`clip_visual_int8.onnx` y `huellas_busqueda.npz`). Lo exportado se guarda en la carpeta de trabajo: si se corta,
al volver a correrlo solo se hace lo que falta o lo que cambió en el CDN. Tarda (unos 30 minutos la primera vez).

Uso:
    python scripts/armar_busqueda.py [--hilos 4] [--trabajo CARPETA]
"""

import argparse
import concurrent.futures
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from PIL import Image  # noqa: E402

from mgitems.busqueda import ARCHIVO_HUELLAS, ARCHIVO_MODELO, Huellas, Modelo, con_fondo  # noqa: E402
from mgitems.categorias import ARCHIVO_INDICE  # noqa: E402
from mgitems.fuente import FuenteCDN  # noqa: E402
from mgitems.iconos import ExportadorFFDec, IconosItems, version_de  # noqa: E402
from mgitems.items import items_del_swf, orden_natural  # noqa: E402
from mgitems.nucleo import _simbolos_con_imagen  # noqa: E402
from mgitems.prendas import ACCION, EFECTO, ItemsBaseFFDec  # noqa: E402
from mgitems.swf import leer_clases, leer_simbolos  # noqa: E402

MODELO_CLIP, PESOS_CLIP = "ViT-B-32", "laion2b_s34b_b79k"


def exportar_modelo(destino: Path) -> None:
    """La parte de imágenes de CLIP en ONNX, comprimida a int8 (de 352 MB a unos 89 MB)."""
    import open_clip
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic

    modelo, _, _ = open_clip.create_model_and_transforms(MODELO_CLIP, pretrained=PESOS_CLIP)
    modelo.eval()

    class Imagenes(torch.nn.Module):
        def __init__(self, visual):
            super().__init__()
            self.visual = visual

        def forward(self, x):
            huella = self.visual(x)
            return huella / huella.norm(dim=-1, keepdim=True)

    with tempfile.TemporaryDirectory() as temporal:
        completo = Path(temporal) / "completo.onnx"
        torch.onnx.export(Imagenes(modelo.visual), torch.randn(1, 3, 224, 224), str(completo), input_names=["imagen"],
                          output_names=["huella"], dynamic_axes={"imagen": {0: "n"}, "huella": {0: "n"}}, opset_version=17,
                          dynamo=False)
        quantize_dynamic(str(completo), str(destino), weight_type=QuantType.QUInt8)


def preparar_swf(fuente: FuenteCDN, iconos: IconosItems, ffdec: ItemsBaseFFDec, trabajo: Path, swf: str):
    """(swf, {Pieza: [Items que la visten]}, error): exporta sus imágenes y lee qué visten sus Items."""
    try:
        data = fuente.descargar(swf)
        iconos.preparar(swf, data, _simbolos_con_imagen(leer_simbolos(data)))
        guardado = trabajo / "visten" / (swf.replace("/", "__") + ".json")
        if guardado.is_file():
            datos = json.loads(guardado.read_text(encoding="utf-8"))
            if datos.get("version") == version_de(data):
                return swf, datos["visten"], ""
        visten: dict[str, list[str]] = {}
        for item in ffdec.analizar(data, items_del_swf(leer_clases(data))).values():
            for parte, pieza in item.partes.items():
                if parte in (ACCION, EFECTO):
                    continue  # no se ven puestas: se ven al usar el Item
                ruta = pieza if "." in pieza else f"{swf}.{pieza}"
                visten.setdefault(ruta, []).append(f"{swf}.{item.clase}")
        guardado.parent.mkdir(parents=True, exist_ok=True)
        guardado.write_text(json.dumps({"version": version_de(data), "visten": visten}, ensure_ascii=False), encoding="utf-8")
        return swf, visten, ""
    except Exception as e:  # la red o FFDec pueden fallar con un SWF: se sigue con los demás
        return swf, {}, str(e)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hilos", type=int, default=4)
    parser.add_argument("--trabajo", type=Path, default=Path(tempfile.gettempdir()) / "mgitems-busqueda")
    args = parser.parse_args()
    salida = args.trabajo / "datos"
    salida.mkdir(parents=True, exist_ok=True)
    t = time.time()

    modelo = salida / ARCHIVO_MODELO
    if not modelo.is_file():
        print("1. modelo…", flush=True)
        exportar_modelo(modelo)

    swfs = list(json.loads(ARCHIVO_INDICE.read_text(encoding="utf-8"))["swfs"])
    fuente, ffdec = FuenteCDN(), ItemsBaseFFDec()
    imagenes = args.trabajo / "imagenes"
    iconos = IconosItems(imagenes, ExportadorFFDec())
    prendas_de_pieza: dict[str, list[str]] = {}
    errores = []
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as hilos:
        trabajos = hilos.map(lambda s: preparar_swf(fuente, iconos, ffdec, args.trabajo, s), swfs)
        for n, (swf, visten, error) in enumerate(trabajos, 1):
            if error:
                errores.append(f"{swf}: {error}")
            for pieza, items in visten.items():
                prendas_de_pieza.setdefault(pieza, []).extend(items)
            print(f"\r2-3. imágenes y Prendas: {n}/{len(swfs)} {swf:40}", end="", flush=True)
    print()

    rutas, lote, huellas = [], [], []
    clip = Modelo(modelo)
    pngs = sorted(imagenes.rglob("*.png"))
    for n, png in enumerate(pngs, 1):
        with Image.open(png) as imagen:
            dibujo = con_fondo(imagen)
        if dibujo is None:
            continue
        lote.append(dibujo)
        rutas.append("/".join(png.relative_to(imagenes).parts[:-1]) + "." + png.stem)
        if len(lote) == 64:
            huellas.append(clip.huellas(lote))
            lote = []
            print(f"\r4. huellas: {n}/{len(pngs)}", end="", flush=True)
    if lote:
        huellas.append(clip.huellas(lote))
    print()

    import numpy as np

    prendas_de_pieza = {p: sorted(set(i), key=orden_natural) for p, i in prendas_de_pieza.items()}
    Huellas(rutas, np.concatenate(huellas), prendas_de_pieza).guardar(salida / ARCHIVO_HUELLAS)
    for archivo in (modelo, salida / ARCHIVO_HUELLAS):
        print(f"{archivo.name}: {archivo.stat().st_size / 1e6:.1f} MB, sha256 {hashlib.sha256(archivo.read_bytes()).hexdigest()}")
    print(f"{len(rutas)} imágenes, {len(prendas_de_pieza)} Piezas con Prendas, {len(errores)} SWF con error, {time.time() - t:.0f} s")
    for e in errores:
        print("  " + e)


if __name__ == "__main__":
    main()

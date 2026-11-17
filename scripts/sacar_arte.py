"""Saca del juego el arte de la estética del programa (la del celular del juego, GatuPhone) a `src/mgitems/ui/arte/`, que
git ignora: el repositorio no lleva dibujos del juego. Lo corre `obtener_binarios.py` después de armar el Gaturro en
vivo, del que sale casi todo:

- de `vendor/gaturro/gaturro.swf` (el cliente del juego que arma `armar_gaturro.py`): sus letras (Fredoka y Cooper), el
  fondo violeta con estrellas del celular, las formas de sus íconos y las caras de las emociones;
- del juego (CDN): los fondos del perfil, que van detrás del Gaturro, y unas Piezas que hacen de ícono de las Partes del
  cuerpo que la interfaz del juego no dibuja (el pelo, la boca, la espalda…).

Además escribe `iconos.css` y `emociones.css` (qué forma va en cada ícono y en cada emoción) y `fondos.js` (cuántos
fondos hay). Si falta, el programa se ve igual con las letras y los íconos de siempre.

Uso: .venv/Scripts/python scripts/sacar_arte.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from mgitems.ffdec import FFDec  # noqa: E402
from mgitems.fuente import FuenteCDN  # noqa: E402
from mgitems.swf import leer_simbolos  # noqa: E402

CLIENTE = RAIZ / "vendor" / "gaturro" / "gaturro.swf"
SALIDA = RAIZ / "src" / "mgitems" / "ui" / "arte"
VERSION = "1"  # cambia con lo que se saca: `obtener_binarios.py` vuelve a sacarlo
ZOOM = 3

# Las letras del juego: archivo → id de la fuente en el cliente.
FUENTES = {"Fredoka SemiBold": 747, "Fredoka Medium": 1711, "Cooper Std Black": 251}
# El fondo violeta con estrellas del celular (`IphoneNewsMC`).
FONDO_DEL_CELULAR = 1730
# Los íconos del programa → (forma del cliente, cómo se usa). «mascara»: la silueta, pintada con el color del texto;
# «color»: tal cual; «espejo» y «doble»: dada vuelta o dos seguidas (las flechas).
ICONOS_DEL_JUEGO = {
    "x": (1942, "mascara"), "check": (1435, "mascara"), "magnifying-glass": (1248, "mascara"), "gear": (1489, "mascara"),
    "trash": (1779, "mascara"), "storefront": (1518, "mascara"), "plus-circle": (1689, "mascara"),
    "person-simple-run": (1950, "mascara"), "paint-brush": (1522, "mascara"), "magic-wand": (1848, "mascara"),
    "scissors": (1848, "mascara"), "lock-open": (671, "mascara"), "hand-pointing": (665, "mascara"),
    "game-controller": (1079, "mascara"), "door-open": (1876, "mascara"), "images-square": (1529, "mascara"),
    "image": (1529, "mascara"), "clipboard": (2020, "mascara"), "arrow-clockwise": (1819, "mascara"),
    "map-pin": (1446, "mascara"), "coin": (1348, "color"), "film-strip": (2041, "color"),
    "shopping-cart": (1460, "mascara"), "door": (1876, "mascara"), "question": (1502, "mascara"),
    "caret-left": (1618, "mascara"), "caret-right": (1618, "espejo"), "caret-double-left": (1618, "doble"),
    "caret-double-right": (1618, "doble-espejo"),
    "couch": (705, "mascara"), "t-shirt": (706, "mascara"), "backpack": (707, "mascara"), "scooter": (708, "mascara"),
    "baseball-cap": (1399, "mascara"), "eyeglasses": (1400, "mascara"), "hand-fist": (665, "mascara"),
    "sneaker": (1401, "mascara"), "sparkle": (1119, "mascara"), "mask-happy": (1458, "mascara"),
    "flask": (707, "mascara"), "dog": (1402, "mascara"), "gift": (1386, "mascara"), "bone": (1122, "mascara"),
}
# Las flechas del perfil del juego, que cambian el fondo detrás del Gaturro.
FLECHAS_DEL_FONDO = {"fondo-anterior": 2046, "fondo-siguiente": 2041}
# Las Partes del cuerpo que la interfaz del juego no dibuja: la silueta de una Pieza del juego (SWF, clase).
ICONOS_DE_PIEZAS = {
    "hair-dryer": ("aesthetic", "PeloSuelto_on"), "smiley": ("clothes1", "bigote1_on"),
    "coat-hanger": ("clothes1", "bufandag_on"), "alas": ("transport", "alasAngel_on"),
    "pants": ("anime", "pantalon_blanco"), "hand": ("clothesZero2", "guante1_on"),
}
# Las caras de las emociones, sin la celda del panel del juego: emoción → clase del cliente.
EMOCIONES = {"normal": "normalMC", "shy": "shyMC", "bored": "boredMC", "angry": "angryMC", "boring": "boringMC",
             "good": "goodMC", "smile": "LaughMC", "love": "loveMC", "money": "moneyMC", "devil": "devilMC"}
# Los fondos del perfil: un dibujo con un cuadro por fondo. En el juego se ven por una ventana vertical fija (196 × 280
# px del juego), centrada en el mismo punto del lienzo que comparten todos los cuadros: lo de afuera no se ve.
FONDOS_SWF, FONDOS_CLASE = "YoBackgrounds", "SocialNetBackgrounds"
FONDOS_CENTRO, FONDOS_VENTANA = (1619, 615), (196, 280)


def sacar() -> None:
    """Deja el arte en `SALIDA` (lo que había se borra). Lanza una excepción si algo no se pudo sacar."""
    ffdec = FFDec()
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    for carpeta in ("fuentes", "iconos", "emociones", "fondos"):
        (SALIDA / carpeta).mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _fuentes(ffdec, tmp)
        _fondo_del_celular(ffdec, tmp)
        _iconos(ffdec, tmp)
        _emociones(ffdec, tmp)
        _fondos_del_perfil(ffdec, tmp)
    (SALIDA / "VERSION").write_text(VERSION, encoding="utf-8")


def _exportar(ffdec: FFDec, formato: str, tipo: str, ids, carpeta: Path, swf: Path, zoom: int = ZOOM) -> None:
    ffdec.ejecutar("-format", formato, "-zoom", str(zoom), "-selectid", ",".join(map(str, ids)), "-export", tipo, str(carpeta), str(swf))


def _sprite(carpeta: Path, ident: int) -> Path:
    """El primer cuadro de un sprite que exportó FFDec."""
    return next(c for c in carpeta.iterdir() if c.name.startswith(f"DefineSprite_{ident}_")) / "1.png"


def _recortado(archivo: Path) -> Image.Image:
    imagen = Image.open(archivo).convert("RGBA")
    return imagen.crop(imagen.getbbox())


def _fuentes(ffdec: FFDec, tmp: Path) -> None:
    ffdec.ejecutar("-format", "font:ttf", "-selectid", ",".join(map(str, FUENTES.values())), "-export", "font",
                   str(tmp / "fuentes"), str(CLIENTE))
    for nombre, ident in FUENTES.items():
        shutil.copy(next((tmp / "fuentes").glob(f"{ident}_*.ttf")), SALIDA / "fuentes" / f"{nombre}.ttf")


def _fondo_del_celular(ffdec: FFDec, tmp: Path) -> None:
    _exportar(ffdec, "shape:png", "shape", [FONDO_DEL_CELULAR], tmp / "celular", CLIENTE)
    shutil.copy(tmp / "celular" / f"{FONDO_DEL_CELULAR}.png", SALIDA / "fondo-del-celular.png")


def _iconos(ffdec: FFDec, tmp: Path) -> None:
    """Las formas de los íconos a `iconos/`, y `iconos.css`: qué forma va en cada ícono y cómo."""
    ids = sorted({i for i, _ in ICONOS_DEL_JUEGO.values()} | set(FLECHAS_DEL_FONDO.values()))
    _exportar(ffdec, "shape:png", "shape", ids, tmp / "formas", CLIENTE, zoom=4)
    for ident in ids:
        shutil.copy(tmp / "formas" / f"{ident}.png", SALIDA / "iconos" / f"{ident}.png")
    for nombre, ident in FLECHAS_DEL_FONDO.items():
        shutil.copy(tmp / "formas" / f"{ident}.png", SALIDA / "iconos" / f"{nombre}.png")
    fuente = FuenteCDN()
    for nombre, (swf, clase) in ICONOS_DE_PIEZAS.items():
        datos = fuente.descargar(swf)
        ident = next(i for i, c in leer_simbolos(datos) if c == clase)
        archivo = tmp / f"{swf}.swf"
        archivo.write_bytes(datos)
        _exportar(ffdec, "sprite:png", "sprite", [ident], tmp / nombre, archivo)
        _recortado(_sprite(tmp / nombre, ident)).save(SALIDA / "iconos" / f"{nombre}.png")
    reglas = []
    iconos = {**ICONOS_DEL_JUEGO, **{n: (n, "mascara") for n in ICONOS_DE_PIEZAS}}
    for nombre, (forma, modo) in iconos.items():
        imagen = f'url("iconos/{forma}.png")'
        base = f'.ic[data-ic="{nombre}"]'
        reglas.append(f"{base} {{ position: relative; }} {base} > svg {{ visibility: hidden; }}")
        if modo == "color":
            reglas.append(f'{base}::after {{ content: ""; position: absolute; inset: 0; background: {imagen} center / contain no-repeat; }}')
        else:
            tamano, repetir = ("50% 100%", "repeat-x") if modo.startswith("doble") else ("contain", "no-repeat")
            vuelta = " transform: scaleX(-1);" if modo.endswith("espejo") else ""
            reglas.append(f'{base}::after {{ content: ""; position: absolute; inset: 0; background: currentColor; '
                          f"-webkit-mask: {imagen} center / {tamano} {repetir};{vuelta} }}")
    (SALIDA / "iconos.css").write_text("\n".join(reglas) + "\n", encoding="utf-8")


def _emociones(ffdec: FFDec, tmp: Path) -> None:
    ids = {c: i for i, c in leer_simbolos(CLIENTE.read_bytes())}
    elegidas = {emocion: ids[f"assets.emoticons.{clase}"] for emocion, clase in EMOCIONES.items()}
    _exportar(ffdec, "sprite:png", "sprite", elegidas.values(), tmp / "emociones", CLIENTE)
    reglas = []
    for emocion, ident in elegidas.items():
        _recortado(_sprite(tmp / "emociones", ident)).save(SALIDA / "emociones" / f"{emocion}.png")
        reglas.append(f'img[src$="emotes/{emocion}.png"] {{ content: url("emociones/{emocion}.png"); }}')
    (SALIDA / "emociones.css").write_text("\n".join(reglas) + "\n", encoding="utf-8")


def _dentro_del_dibujo(cuadro: Image.Image, caja: tuple[int, int, int, int]) -> Image.Image:
    """La ventana del perfil de un cuadro, sin lo que el cuadro no dibuja: algunos (la playa, la selva…) no llegan a
    cubrir toda la ventana, y lo transparente se vería negro. Se achica la ventana (con la misma forma, lo más
    centrada posible) hasta que entre en lo dibujado, y se agranda al tamaño de las demás."""
    recorte = cuadro.crop(caja)
    ancho, alto = recorte.size
    alfa = recorte.getchannel("A").load()
    filas = [y for y in range(alto) if all(alfa[x, y] > 250 for x in range(0, ancho, 2))]
    if not filas or (filas[0] == 0 and filas[-1] == alto - 1):
        return recorte
    arriba, abajo = filas[0], filas[-1] + 1
    nuevo_ancho = round((abajo - arriba) * ancho / alto)
    izquierda = (ancho - nuevo_ancho) // 2
    return recorte.crop((izquierda, arriba, izquierda + nuevo_ancho, abajo)).resize((ancho, alto), Image.LANCZOS)


def _fondos_del_perfil(ffdec: FFDec, tmp: Path) -> None:
    datos = FuenteCDN().descargar(FONDOS_SWF)
    ident = next(i for i, c in leer_simbolos(datos) if c == FONDOS_CLASE)
    archivo = tmp / "fondos.swf"
    archivo.write_bytes(datos)
    _exportar(ffdec, "sprite:png", "sprite", [ident], tmp / "fondos", archivo)
    cuadros = sorted(next((tmp / "fondos").iterdir()).glob("*.png"), key=lambda a: int(a.stem))
    (cx, cy), (w, h) = FONDOS_CENTRO, FONDOS_VENTANA
    caja = tuple(round(v * ZOOM) for v in (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    for cuadro in cuadros:
        _dentro_del_dibujo(Image.open(cuadro).convert("RGBA"), caja).convert("RGB").save(
            SALIDA / "fondos" / f"{cuadro.stem}.jpg", quality=90)
    (SALIDA / "fondos.js").write_text(f"window.FONDOS_DEL_PERFIL = {len(cuadros)};\n", encoding="utf-8")


def al_dia() -> bool:
    """Si el arte ya está y es de esta versión."""
    marca = SALIDA / "VERSION"
    return marca.exists() and marca.read_text(encoding="utf-8").strip() == VERSION


if __name__ == "__main__":
    sacar()
    print(f"Arte del juego en {SALIDA}")

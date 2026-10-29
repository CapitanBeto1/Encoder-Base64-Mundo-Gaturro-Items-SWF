"""Los dibujos del juego para las ventanas del programa que imitan las suyas («Guarda tu Look», «Elige tus colores»).

Están en dos banners del juego, sin cifrar en el CDN (`juego/banners/AvatarSaverBanner.swf` y
`ColorPickerBanner.swf`): el programa los descarga y los exporta con FFDec al usarse, como las Piezas, así
el repositorio no trae dibujos del juego. Dentro de un banner, cada dibujo es una forma con su número, que
puede cambiar si el juego lo vuelve a publicar: los dibujos se usan solo con la versión (el tamaño) del
banner en que se identificaron. Con otra, la pantalla sigue con los suyos.
"""

import re

CARPETA_BANNERS = "banners"
BANNERS = {"AvatarSaverBanner": 23409, "ColorPickerBanner": 24998}  # banner → tamaño de la versión que se miró

# Nombre → (banner, número de la forma, recorte (x, y, ancho, alto) o None).
DIBUJOS = {
    "martillo": ("AvatarSaverBanner", 14, None),  # el de «GUARDA TU LOOK»
    "cerrar_amarillo": ("AvatarSaverBanner", 10, None),  # la X amarilla en el círculo rojo
    "escenario": ("AvatarSaverBanner", 19, None),  # el telón con el piso, detrás del Gaturro
    "reiniciar": ("AvatarSaverBanner", 24, None),
    "eliminar": ("AvatarSaverBanner", 27, None),
    # La paleta de «ELIGE TUS COLORES»: en el juego es un solo dibujo con el Gaturro pintor de la derecha.
    "paleta": ("ColorPickerBanner", 10, (0, 10, 31, 31)),
}

_TAMANO = re.compile(r'height="[\d.]+px" width="[\d.]+px"')


def recortar(svg: str, recorte: tuple[float, float, float, float] | None) -> str:
    """El SVG de una forma (como lo exporta FFDec) mostrando solo el rectángulo `recorte`."""
    if not recorte:
        return svg
    x, y, ancho, alto = recorte
    return _TAMANO.sub(f'height="{alto}px" width="{ancho}px" viewBox="{x} {y} {ancho} {alto}"', svg, count=1)

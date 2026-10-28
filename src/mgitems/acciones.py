"""Las acciones: animaciones del Gaturro que un Item de mochila hace al usarlo, según el cliente del juego.

Un Item de mochila guarda la acción en `adds.action`: `"<animación>"` o `"<animación>.<swf>.<Pieza>"`.
Al usarlo, `BagGuiModal` la copia al Gaturro y `GaturroAnimationController.doRunAction` lo lleva al
cuadro de la animación (`gotoAndPlay`) y carga la Pieza en `objects_ph`, sin mirar si es un vehículo.
La Pieza queda en su último cuadro hasta la próxima acción. El juego no la hace:

- si su texto dice `run`, `zombieStand` o `zombieWalk` en cualquier lugar, también en la Pieza
  (`AttributeControl.isAllowedAnimation`);
- si tiene algo prohibido (`AttributeControl.isProhibitedInAction`: «Esta acción no está disponible»);
- si la animación solo anda con ciertas Piezas o no anda con otras (`validItems.action` de
  `cfgs/gameplay.json`, `Gaturro.validItems`).

La Pieza no se muestra si mide más de 150×150 o si es vacía (`whenAssetForPlaceholderIsLoaded`).
"""

import unicodedata

from mgitems.destinos import PROHIBIDOS

ACCION = "action"
TAMANO_MAXIMO_ACCION = 150  # `whenAssetForPlaceholderIsLoaded`: más grande que esto, la Pieza no se muestra

# Grupos, en el orden en que se ofrecen.
DE_VERDAD = "accion"
NO_SE_DIBUJA = "no_se_dibuja"  # el juego la hace, pero el Gaturro que el programa puede leer no la tiene
OTRAS = "otras"  # parte de otra animación (caminar, quieto, transportes, lo que se repite o la cierra)

# Los cuadros con nombre del `assets.GaturroMC` del juego de hoy, con su nombre en castellano.
ANIMACIONES = {
    "amazed": "Asombrarse", "celebrate": "Festejar", "colouredSpray": "Spray de color", "dance": "Bailar",
    "dance2": "Bailar 2", "dance3": "Bailar 3", "dance4": "Bailar 4", "dance5": "Bailar 5", "dig": "Cavar",
    "dormido": "Dormir", "dormido2": "Dormir 2", "drink": "Tomar", "eat": "Comer", "eructo": "Eructar",
    "estornudo": "Estornudar", "fish": "Pescar", "flag": "Bandera", "flotando": "Flotar", "football": "Fútbol",
    "fortnite1": "Fortnite 1", "fortnite2": "Fortnite 2", "free": "Liberar", "get": "Agarrar", "greet": "Saludar",
    "guitar": "Tocar la guitarra", "gym": "Hacer gimnasia", "horn": "Tocar la corneta", "icecream": "Tomar un helado",
    "idea": "Tener una idea", "inAHole": "Caer en un pozo", "joke": "Contar un chiste", "jueguito": "Hacer jueguito",
    "jump": "Saltar", "kick": "Patear", "laugh": "Reírse", "love": "Enamorarse", "nadando": "Nadar", "pedo": "Tirarse un pedo",
    "percussion": "Tocar la percusión", "phone": "Hablar por teléfono", "rayos": "Tirar rayos", "sad": "Ponerse triste",
    "showObject": "Mostrar en la mano", "showObjectUp": "Levantar", "shy": "Tener vergüenza", "sit": "Sentarse",
    "spellfighting": "Duelo de hechizos", "spray": "Tirar spray", "superjump": "Supersalto", "sweep": "Barrer",
    "throw": "Tirar", "throwDown": "Tirar para abajo", "throwUp": "Tirar para arriba", "vertical": "Hacer la vertical",
    "water": "Regar", "wink": "Guiñar el ojo",
    # Otras: partes de animaciones.
    "blank": "Vacío", "emote": "Emoción", "standBy": "Quieto", "walk": "Caminar", "run": "Correr",
    "zombieStand": "Zombi quieto", "zombieWalk": "Zombi caminando", "showObjectOn": "Mostrar en la mano (sigue)",
    "dormido_loop": "Dormir (se repite)", "dormido2_loop": "Dormir 2 (se repite)", "guitarLoop": "Tocar la guitarra (se repite)",
    "gymLoop": "Hacer gimnasia (se repite)", "loopInAHole": "Caer en un pozo (se repite)",
    "percussionLoop": "Tocar la percusión (se repite)", "phone_loop": "Hablar por teléfono (se repite)",
    "eructoEnd": "Eructar (final)", "estornudoEnd": "Estornudar (final)", "pedoEnd": "Tirarse un pedo (final)",
    "transportStand": "Transporte quieto", "transportMove": "Transporte andando",
}
_VEHICULOS = {"balloon": "globo", "bike": "bici", "bola": "bola", "colgante": "colgante", "escoba": "escoba", "esfera": "esfera",
              "gorro": "gorro", "horse": "caballo", "moto": "moto", "nube": "nube", "pogo": "pogo", "rollers": "patines",
              "surf": "surf", "vuela": "vuela", "walk": "a pie"}
for _tipo, _nombre in _VEHICULOS.items():
    ANIMACIONES[f"transportStand_{_tipo}"] = f"Transporte quieto: {_nombre}"
    ANIMACIONES[f"transportMove_{_tipo}"] = f"Transporte andando: {_nombre}"

# Las que el Gaturro de `superHeroesTrajes` (el que el programa puede leer) no tiene: solo están en el cliente.
NO_SE_DIBUJAN = {
    "blank", "dormido", "dormido2", "dormido2_loop", "dormido_loop", "emote", "flotando", "fortnite1", "fortnite2",
    "jueguito", "nadando", "run", "shy", "spellfighting", "transportMove_nube", "transportMove_walk",
    "transportStand_nube", "transportStand_walk", "wink", "zombieStand", "zombieWalk",
}
_OTRAS = {"blank", "emote", "standBy", "walk", "run", "zombieStand", "zombieWalk", "showObjectOn"}

# `AttributeControl.isAllowedAnimation`: si el texto de la acción dice esto, el juego no la hace.
NO_DESDE_UN_ITEM = ("run", "zombieStand", "zombieWalk")
# `AttributeControl.isProhibitedInAction`: además de `ItemControl.prohibitedAssets` (sin mayúsculas).
PROHIBIDOS_EN_ACCION = ["_so", "carscolors", "pisogorrorojo", "floor", "guardiannieve", "geocat", "nik.pancho", "granja.",
                        "medals.", "pruebas.test"]
# `validItems.action` (cfgs/gameplay.json): la animación anda solo con Piezas que digan esto…
SOLO_CON = {"phone": ["phones.", "transmisor"], "phone_loop": [" "]}
# …o no anda con las que digan esto.
NO_CON = {"football": ["magia.poder", "gatoons."]}


def grupo(animacion: str) -> str:
    if animacion in _OTRAS or animacion.startswith("transport") or animacion.lower().endswith(("loop", "end")) \
            or animacion == "loopInAHole":
        return OTRAS
    return NO_SE_DIBUJA if animacion in NO_SE_DIBUJAN else DE_VERDAD


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").casefold()


def animaciones() -> list[dict]:
    """Las animaciones en el orden en que se ofrecen: las de verdad, las que no se pueden dibujar y las otras,
    cada grupo de la A a la Z."""
    orden = [DE_VERDAD, NO_SE_DIBUJA, OTRAS]
    filas = [{"id": a, "nombre": n, "grupo": grupo(a), "se_dibuja": a not in NO_SE_DIBUJAN} for a, n in ANIMACIONES.items()]
    return sorted(filas, key=lambda f: (orden.index(f["grupo"]), _sin_tildes(f["nombre"])))


def valor_de_accion(animacion: str, pieza: str | None) -> str:
    """Cómo se escribe la acción en `adds.action` (`pieza` con su SWF)."""
    return f"{animacion}.{pieza}" if pieza else animacion


def motivo_sin_accion(valor: str) -> str | None:
    """Por qué el juego no haría esta acción (`valor`: lo de `adds.action`), o None."""
    animacion, _, pieza = valor.partition(".")
    if dice := next((n for n in NO_DESDE_UN_ITEM if n in valor), None):
        return f"el juego no hace una acción que diga «{dice}» (tampoco en el nombre de la Pieza o del SWF)"
    baja = valor.lower()
    if any(p.lower() in baja for p in PROHIBIDOS + PROHIBIDOS_EN_ACCION):
        return "el juego no la permite («Esta acción no está disponible»)"
    objeto = pieza or "undefined.undefined"  # lo que mira `validItems`
    if animacion in SOLO_CON and not any(v in objeto for v in SOLO_CON[animacion]):
        return f"«{ANIMACIONES.get(animacion, animacion)}» solo anda con " + (
            " o ".join(f"«{v}»" for v in SOLO_CON[animacion] if v.strip()) or "nada: el juego no la hace desde un Item")
    if any(v in objeto for v in NO_CON.get(animacion, [])):
        return f"«{ANIMACIONES.get(animacion, animacion)}» no anda con Piezas de " + " ni ".join(f"«{v}»" for v in NO_CON[animacion])
    return None


def motivo_pieza_sin_accion(ruta: str, donde: dict) -> str | None:
    """Por qué ninguna acción mostraría esta Pieza (`donde`: lo de `se_ve.donde_se_ve`), o None.
    Lo que depende de la animación lo dice `motivo_sin_accion`."""
    if donde.get("accion") == "grande":
        return f"una acción no muestra lo de más de {TAMANO_MAXIMO_ACCION}×{TAMANO_MAXIMO_ACCION}"
    if donde.get("accion") == "vacia":
        return "es vacía: una acción no la muestra"
    return motivo_sin_accion(f"showObject.{ruta}")

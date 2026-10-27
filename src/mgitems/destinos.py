"""Dónde llega un Item que se agrega con `inventory.add`, según las reglas del cliente del juego.

`inventory.add` llama a `GaturroRoomAPI.giveUser`, y de ahí a `InventoryUtil.acquireObject`. En el
camino, el juego descarta sin avisar algunos Items (por su nombre), crea las mascotas en vez de
guardarlas, elige el inventario por los atributos del Item (guardarropa, mochila o casa) y no le
pide al servidor los Items de sesión. Después, algunas pantallas no muestran ciertos Items. Las
listas y reglas de acá son copia de las del cliente (`ItemControl`, `AttributeControl`,
`GaturroInventory.isPocketExclusive`, `OwnedNpcFactory.VALID_PETS`, `GaturroRoomAPI.shouldAppear`,
`BagGuiModal` y `ClothMamboAsset`/`PetClothMamboAsset.process`).

Lo que decide el servidor después no se ve en el cliente.
"""

import re

# Llega bien.
GUARDARROPA, MOCHILA, CASA, MASCOTA = "guardarropa", "mochila", "casa", "mascota"
# Llega, pero solo se ve al personalizar una mascota.
PANTALLA_MASCOTA = "pantalla_mascota"
# Llega, pero se borra al salir del juego (el juego no se lo pide al servidor).
SESION = "sesion"
# Llega, pero el juego no lo muestra.
OCULTO = "oculto"
# El juego lo tira sin avisar.
DESCARTADO = "descartado"

# Los que se crean como mascota (`OwnedNpcFactory.VALID_PETS`).
MASCOTAS_VALIDAS = {
    "pet.koala", "pet.penguin", "pet.mulita", "pet.mono", "pet.dragon", "pet3.GaturroPet", "dailyQuest/wears.valijaAngel",
    "dailyQuest/wears.valijaConejo", "pet2.detective", "presidentes2019/wears.yetiGuardaespaldas",
    "sanValentin2021/final.angelGuardian", "animus.pioPet", "animus.yuyolPet", "christmas2021.muneco", "gatuPotter/wears.ghost",
    "gatuPotter/wears.snitch", "merlinaClothes.dedos", "eternautaClothes.escarabajoPet", "halloween2026.eyesPet",
    "halloween2026.catPet",
}
# Comportamientos con los que el juego deja salir a una mascota (`OwnedNpcFactory.VALID_BEHAVIORS`).
COMPORTAMIENTOS_VALIDOS = {
    "pets", "detective/detective", "sanValentin2021/angelGuardian", "presidentes2019/guardaespaldas",
    "dailyQuest/valijaAngelPet", "dailyQuest/valijaConejoPet", "animusPet", "gatuPotter/pets",
}
_NOMBRE_DE_MASCOTA = re.compile(r'\bnameOwnedNpc\s*=\s*"([^"]+)"')
_COMPORTAMIENTO_DE_MASCOTA = re.compile(r'\bbehaviorOwnedNpc\s*=\s*"([^"]+)"')
# `ItemControl.prohibitedAssets`: si la ruta los contiene (sin distinguir mayúsculas), se descarta.
PROHIBIDOS = [
    "main.", "acciones.", "geocat.", "medals.", "carsColors.", "butterflies.", "hiscore.", "espacio.npcGravedad", "signals.",
    "YoBackgrounds.", "bannersThumbs.", "photosOk.", "concursoRemeras2.img_", "concursoRemeras1.img_", "laboratorio2018/props",
    "hw20/props.stage_", "avatars/", "privateRoom/", "HomeBackgrounds", "gatubers/props.vendorGatubers", "_bitmap.carta", "::",
    "campamento/props.monstruon_on", "gatubers2018/props", "animales2018/props.explicacion", "_lvlUp", "_efecto", "bossFinal",
    "gatoons.poder", "achievements.", "banners/",
]
# `AttributeControl.isProhibitedItem`: si la ruta contiene las dos palabras, se descarta para los usuarios.
PROHIBIDOS_PARA_USUARIOS = [
    ("nik", "goma"), ("nik", "regla"), ("nik", "regla2"), ("nik", "donaNik"), ("nik", "sandiaNik"), ("nik", "bananaNik"),
    ("nik", "burgerNik"), ("nik", "panchoNik"), ("nik", "avionAzulNik"), ("nik", "perroInflableNik"), ("pruebas", "test_on"),
    ("clothes1", "remeraQB9"),
]
# `ItemControl.prohibitedAppear` y el resto de `shouldAppear`: llegan, pero no se muestran.
NO_SE_MUESTRAN = ["privateHome.edit", "navidad2015.navidadBehavior", "granja."]

# Partes del Gaturro donde se ve una Prenda (las que usan las Prendas del juego; `hat`, que usa una sola, no existe).
PARTES_DEL_GATURRO = {
    "hats", "hairs", "mouths", "accesories", "accesories2", "neck", "cloth", "clothFront", "clothBack", "arm", "armFore",
    "armBack", "grip", "gripFore", "gripBack", "glove", "gloveFore", "gloveBack", "leg", "foot", "transport",
    "customization", "special_ph", "medal_ph",
}
# `PassportControl.VIP_PACKS`: una Pieza (o un Item) que contenga alguno de estos nombres solo se la
# puede poner quien tiene pasaporte (sin pasaporte, el guardarropa dice «ESTE OBJETO REQUIERE PASAPORTE»
# y el Gaturro no la dibuja).
DE_PASAPORTE = [
    "invisibles/", "invisible_", "mime.disfrazMimo", "gatupacks/hw18.hide_hw18_on", "jeanMimo_on", "gorroMimo_on",
    "easter2021.disfrazBunny",
]
_VALOR_EN_MAPA = re.compile(r'"\w+"\s*:\s*"([^"]+)"')
_VEHICULO = re.compile(r'\bvehicle\s*=\s*"([^"]+)"')


def es_de_pasaporte(ruta: str) -> bool:
    """Si la Pieza o el Item `ruta` (`swf.Clase`) es de pasaporte (`PassportControl.isVipPack`)."""
    return "." in ruta and any(nombre in ruta for nombre in DE_PASAPORTE)


def requiere_pasaporte(ruta: str, fuente: str) -> bool:
    """Si para ponerse el Item hace falta pasaporte: él o alguna de las Piezas que muestra es de pasaporte."""
    swf = ruta.rpartition(".")[0]
    clothes = _CLOTHES.search(fuente)
    piezas = (_VALOR_EN_MAPA.findall(clothes.group("cuerpo")) if clothes else []) + _VEHICULO.findall(fuente)
    return es_de_pasaporte(ruta) or any(es_de_pasaporte(p if "." in p else f"{swf}.{p}") for p in piezas)


# Clases del juego que hacen al Item "agarrable" (`grabbable`: va a la mochila si no es ropa ni transporte).
_AGARRABLES = {
    "GrabbableMamboAsset", "ClothMamboAsset", "UsableMamboAsset", "ConsumableMamboAsset", "TransportMamboAsset",
    "TransportOnMamboAsset", "PetClothMamboAsset", "PetFoodMamboAsset", "PetToyMamboAsset",
}
_CLASE = re.compile(r"\bclass\s+\w+\s+extends\s+(\w+)")
_CLOTHES = re.compile(r"\bclothes\s*=\s*\{(?P<cuerpo>[^{}]*)\}")


def descarte_por_nombre(ruta: str) -> str | None:
    """Por qué el juego descarta este Item solo por su nombre, o None."""
    if ruta in MASCOTAS_VALIDAS:
        return None
    if "mundial2026/album" in ruta:
        return "el juego ignora los Items del álbum del Mundial 2026"
    if ruta.startswith("pocket") or (ruta.startswith("gatoonsClothes") and ruta.find("_npc") >= 1) or ruta.find("_catalog") >= 1:
        return "es exclusivo de un bolsillo o un catálogo"
    if ruta.find("_so") > 0:
        return "tiene «_so» en el nombre (el juego lo toma como parte del escenario)"
    if ruta.find("_on") > 0:
        return "tiene «_on» en el nombre (el juego lo toma como una Pieza)"
    baja = ruta.lower()
    if prohibido := next((p for p in PROHIBIDOS if p.lower() in baja), None):
        return f"el juego prohíbe los Items con «{prohibido}»"
    if any(a.lower() in baja and b.lower() in baja for a, b in PROHIBIDOS_PARA_USUARIOS):
        return "el juego lo prohíbe para los usuarios"
    return None


def destino_de_item(ruta: str, fuente: str) -> dict:
    """{"destino"} (y "motivo" si no llega bien) de un Item, con su código AS3."""
    if motivo := descarte_por_nombre(ruta):
        return {"destino": DESCARTADO, "motivo": motivo}
    clase = _CLASE.search(fuente)
    padre = clase.group(1) if clase else ""
    clothes = _CLOTHES.search(fuente)
    con_clothes = bool(clothes and re.search(r'"\w+"\s*:', clothes.group("cuerpo")))
    # Una mascota llega al perfil si trae su nombre (`nameOwnedNpc`) y un comportamiento válidos; si no,
    # el juego la borra al sacarla. Las mascotas comunes dadas directo (`pet.koala`) no traen nombre:
    # llegan a la casa como adorno (la mascota es su casita, `pet.koalaHouse`). Confirmado en el juego.
    if mascota := _NOMBRE_DE_MASCOTA.search(fuente):
        comportamiento = _COMPORTAMIENTO_DE_MASCOTA.search(fuente)
        if mascota.group(1) in MASCOTAS_VALIDAS and comportamiento and comportamiento.group(1) in COMPORTAMIENTOS_VALIDOS:
            return {"destino": MASCOTA}
        return {"destino": DESCARTADO, "motivo": "el juego borra esta mascota al sacarla: no es una mascota válida"}
    if ruta in MASCOTAS_VALIDAS:
        return {"destino": CASA, "motivo": f"llega a la casa como adorno, no como mascota (la mascota es {ruta}House)"}
    vehiculo = padre in ("TransportMamboAsset", "TransportOnMamboAsset") and re.search(r'\bvehicle\s*=\s*"[^"]+"', fuente)
    sesion = re.search(r"\bsession\s*=\s*true", fuente)
    # El guardarropa saca los Items de misión (`ClosetGuiModal` → `removeQuestItems`); la mochila no.
    if re.search(r"\bquestItem\s*=\s*true", fuente) and (vehiculo or (padre == "ClothMamboAsset" and con_clothes)):
        return {"destino": OCULTO, "motivo": "es de misión: llega al guardarropa, pero el guardarropa no muestra los Items de misión"
                + (" (y se borra al salir)" if sesion else "")}
    if sesion:
        return {"destino": SESION, "motivo": "es de sesión: el juego no lo guarda y se borra al salir"}
    if ruta.startswith(("penguin", "privateRoom")) or "_so" in ruta or any(n in ruta for n in NO_SE_MUESTRAN):
        return {"destino": OCULTO, "motivo": "el juego no muestra los Items con ese nombre"}
    if padre == "PetClothMamboAsset" and con_clothes:
        return {"destino": PANTALLA_MASCOTA, "motivo": "solo se ve al personalizar una mascota"}
    vehiculo = padre in ("TransportMamboAsset", "TransportOnMamboAsset") and re.search(r'\bvehicle\s*=\s*"[^"]+"', fuente)
    if vehiculo:
        return {"destino": GUARDARROPA}
    if padre == "ClothMamboAsset" and con_clothes:
        partes = set(re.findall(r'"(\w+)"\s*:', clothes.group("cuerpo")))
        if not partes & PARTES_DEL_GATURRO:
            raras = ", ".join(f"«{p}»" for p in sorted(partes))
            return {"destino": GUARDARROPA, "motivo": f"usa la Parte {raras}, que el Gaturro no tiene: al ponérsela no se ve"}
        return {"destino": GUARDARROPA}
    if padre == "ClothMamboAsset":
        return {"destino": MOCHILA, "motivo": "no declara Piezas: llega a la mochila, pero no se puede poner"}
    if padre in _AGARRABLES or re.search(r"\bquestItem\s*=\s*true", fuente):
        return {"destino": MOCHILA}
    return {"destino": CASA}

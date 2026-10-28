"""En qué Parte del cuerpo se ve una Pieza puesta en el Gaturro, según el cliente del juego.

Cuando el Gaturro se viste, el juego pone cada Pieza en su Parte (`Gaturro.setAsset` y `Gaturro.add`),
pero no dibuja algunas y saca otras:

- Las que el Gaturro no dibuja nunca:
  - la ropa de mascota (`AttributeControl.isProhibited`: `petClothes`);
  - las de más de 300×300 píxeles (paredes, pisos);
  - las prohibidas para los usuarios (`AttributeControl.isUserProhibited`).
- Las que van solo en una Parte. Están en la lista `troublesomeItems` de `cfgs/gameplay.json`: si se
  ponen en otra, el juego las saca del Gaturro. Con Parte vacía no van en ninguna; son instrumentos y
  objetos de acción, que solo sirven para la animación.
- Los vehículos: las Piezas con la propiedad `type`. Solo van en la Parte `transport` (`checkTransport`);
  ahí, una Pieza sin `type` se saca (`hasTransport`).

Las de pasaporte se ven solo con pasaporte (`destinos.es_de_pasaporte`).
"""

from mgitems.destinos import PROHIBIDOS_PARA_USUARIOS

TRANSPORTE = "transport"
TAMANO_MAXIMO = 300  # `Gaturro.add`: más grande que esto, no se dibuja
# `troublesomeItems` (cfgs/gameplay.json): si la ruta de la Pieza contiene la clave, solo va en esa Parte ("": en ninguna).
SOLO_EN = {
    "gatupacks/mar19.autoCarroza2_on": "transport", "gatupacks/mar19.autoCarroza1_on": "transport",
    "espacio.naveAlienigena_on": "transport", "espacio.naveAlienigenaPremium": "transport",
    "gatupacks/hw18.gorroMomo_on": "hats", "carnival2.vestidoCarnavalMujer": "cloth", "carnival2.remeraCarnaval": "cloth",
    "carnival2.gorroCarnaval": "hats", "christmasClothes.gorroReno_on": "hats", "virtualGoods3.cabezaMoai_on": "hats",
    "estaciones.gorroVerano_on": "hats", "campamento/props.monstruon_on": "special_ph",
    "transport.": "transport", "transport2.": "transport",
    "gatupacks/mar19.fireworks_on": "", "navidad2018/guerra.removeParalized_on": "", "navidad2018/guerra.roba_on": "",
    "navidad2018/guerra.paralized_on": "", "guitarraVioleta_on": "", "guitarraRoja_on": "", "bajoSerenito_on": "",
    "bajoAzul_on": "", "bateria": "", "guitarra": "", "ukelele": "", "bombo": "", "microfono": "", "picoDulce.": "",
    "papelPicado_on": "", "corneta_on": "", "petardo_on": "", "matraca_on": "", "saxo_on": "", "espantasuegra_on": "",
    "party.sprayRosa_on": "", "mundial.diabolica_on": "", "carnival.pomo1_on": "", "carnival2.agogo_on": "",
    "carnival2.chocalho_on": "", "carnival2.reco_on": "", "carnival2.repinique_on": "", "extraterrestres.antidotoSpray_on": "",
    "extraterrestres.pistola_on": "", "halloween2018/props4.rayoFulminador": "", "halloween2018/props2.captura": "",
    "halloween2018/props.moneda": "", "rancho.bocina_on": "", "vueltaCole2018/props.abuelurraBata_on": "",
}


def donde_se_ve(ruta: str, limites: tuple | None = None, es_vehiculo: bool = False) -> dict:
    """{} si la Pieza se ve en cualquier Parte; {"solo_en": Parte} si solo en una; {"no_se_ve": motivo}
    si el Gaturro no la dibuja en ninguna. `limites`: su rectángulo (x0, y0, x1, y1), si se sabe."""
    if "petClothes" in ruta:
        return {"no_se_ve": "es ropa de mascota: el Gaturro no la dibuja"}
    baja = ruta.lower()
    if any(a.lower() in baja and b.lower() in baja for a, b in PROHIBIDOS_PARA_USUARIOS):
        return {"no_se_ve": "el juego la prohíbe para los usuarios"}
    if limites:
        ancho, alto = limites[2] - limites[0], limites[3] - limites[1]
        if ancho > TAMANO_MAXIMO or alto > TAMANO_MAXIMO or not ancho or not alto:
            return {"no_se_ve": f"mide {round(ancho)}×{round(alto)}: el Gaturro no dibuja lo que pasa de {TAMANO_MAXIMO}×{TAMANO_MAXIMO}"}
    if parte := next((p for clave, p in SOLO_EN.items() if clave in ruta), None):
        return {"solo_en": parte}
    if clave_vacia := next((clave for clave, p in SOLO_EN.items() if clave in ruta and not p), None):
        return {"no_se_ve": f"el juego la saca del Gaturro («{clave_vacia}»): solo sirve como animación de una acción"}
    if es_vehiculo:
        return {"solo_en": TRANSPORTE}
    return {}


def se_ve_en(ruta: str, parte: str, limites: tuple | None = None, es_vehiculo: bool = False) -> str | None:
    """None si la Pieza se ve en esa Parte; si no, por qué no."""
    donde = donde_se_ve(ruta, limites, es_vehiculo)
    if "no_se_ve" in donde:
        return donde["no_se_ve"]
    if "solo_en" in donde and donde["solo_en"] != parte:
        return f"solo se ve en la Parte «{donde['solo_en']}»"
    if parte == TRANSPORTE and not es_vehiculo and donde.get("solo_en") != TRANSPORTE:
        return "en Transporte solo se ven los vehículos"
    return None

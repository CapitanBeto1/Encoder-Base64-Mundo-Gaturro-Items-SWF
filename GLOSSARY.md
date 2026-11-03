# Mundo Gaturro Items

Herramienta para que cualquier jugador de Mundo Gaturro obtenga, trucque y combine Items en su cuenta, sin conocimientos técnicos. Los términos del juego se toman tal como aparecen en el código y los datos de Mundo Gaturro.

## Items y ropa

**Item**:
Cualquier cosa que puede estar en el inventario de un jugador. Se identifica por su ruta `<swf>.<Clase>` (ej. `clothes1.remera5`, `costumes.costumeUnicornio`).
_Avoid_: Objeto, asset

**SWF de assets**:
Archivo del juego que agrupa muchos Items de una categoría (ej. `clothes1`, `costumes`, `virtualGoods`).
_Avoid_: archivo de ropa

**Prenda**:
Un Item que se viste: el juego lo modela como `ClothMamboAsset` y declara qué Pieza muestra en cada Parte del cuerpo.
_Avoid_: Ropa, objeto

**Pieza**:
El dibujo que se ve sobre el Gaturro cuando una Prenda está puesta; en el juego es la clase con sufijo `_on` (ej. `remera5_on`, `remera5_brazo_on`). Cualquier Pieza se puede mostrar en cualquier Parte del cuerpo.
_Avoid_: vestimenta (en la interfaz se aclara entre paréntesis)

**Parte del cuerpo**:
Un lugar del Gaturro donde va una Pieza. Nombres del juego: `hats`, `hairs`, `mouths`, `neck`, `accesories`, `accesories2`, `cloth`, `clothBack`, `leg`, `foot`, `arm`, `grip`, `gripFore` (y otras menos comunes).
_Avoid_: slot, zona

## Truqueo

**Prenda trucada**:
Un Item base modificado para mostrar una sola Pieza (cualquiera, de cualquier SWF) en una sola Parte del cuerpo (cualquiera); por ejemplo, una máscara en la mano. Si el Item base es una Prenda, se ve al ponérsela; si es un Item de mochila, al usarlo. Los demás jugadores la ven así y se puede intercambiar. Varias se reciben juntas en un mismo Encode, cada una con otro Item base.
_Avoid_: Item trucado, objeto trucado

**Prenda cortada**:
Una sola parte de una Prenda que tiene varias, usada sola: el pantalón de un traje, la remera sin sus mangas. Así se dice en el juego. La búsqueda por imagen la reconoce porque compara también con cada Pieza dibujada puesta, y muestra la Prenda entera con la marca «Cortado».
_Avoid_: parte suelta, pieza recortada

**Item base**:
El Item existente que se modifica para crear una Prenda trucada o materializar un Look; de él toma su nombre e ícono en el juego. Puede ser una Prenda (queda en el guardarropa) o un Item de mochila; para una acción, una tienda, un portal o un minijuego, cualquier Item, que se convierte en lo que hace falta (ADR 0007). No puede ser una Prenda de `clothes1`, la ropa personalizable del juego: el servidor no guarda lo trucado y, al volver a entrar, vuelve a ser la original.
_Avoid_: Prenda base (ya no es siempre una Prenda)

**Item de mochila**:
Un Item usable o consumible (poción, bebida, comida) que queda en la mochila; al usarlo aplica sus efectos al Gaturro. Como Item base, al usarlo te pone las Piezas.
_Avoid_: consumible (a secas), objeto de mochila

**Look** _(provisional)_:
Un conjunto de Piezas asignadas a varias Partes del cuerpo a la vez, con nombre, que se materializa en el juego como un Item base modificado (normalmente un Item de mochila). Se guarda y se comparte como archivo; con él se puede volver a generar. Guarda también los colores con los que se ve el Gaturro en el programa (solo para mostrarlo; no cambian lo que se recibe en el juego).
_Avoid_: Outfit, conjunto

**Archivo de Look**:
Un Look guardado en un archivo para pasárselo a otra persona, que lo importa a sus Looks y lo aplica (los SWF que le falten se descargan solos).
_Avoid_: Look exportado, preset

**NPC** (de la casa):
Un Item que, puesto en la casa, hace lo mismo que un personaje del juego al tocarlo: abrir una tienda (catálogo), llevar a otra sala (portal) o abrir un minijuego. Puede ser cualquier Item de cualquier SWF (menos las Prendas de `clothes1`): llega a la casa con su dibujo y su nombre. Es una tienda, un portal o un minijuego según su comportamiento.
_Avoid_: tienda trucada, NPC trucado

**Comportamiento**:
Lo que hace un NPC, por su nombre en el juego (`behavior`, ej. `brujaMesa`, `magia/portal`): el guion `npc/<comportamiento>.npc` que corre al tocarlo.
_Avoid_: behavior (en la interfaz), script de NPC

**Fondo**:
Un objeto de la casa cuyo dibujo tiene varios **cuadros** y muestra el que se eligió, para todos los que entran y para siempre (ej. `socialNetBackgrounds.SocialNetBackgrounds`, 23 fondos, dos de playa). Es un NPC con el comportamiento `painting` del juego: el dueño lo cambia al siguiente cuadro tocándolo. Solo sirven los dibujos que se quedan quietos en el primer cuadro; los demás son animaciones.
_Avoid_: painting (en la interfaz), cuadro trucado

## Entrega al juego

**Script**:
Un programa en el lenguaje de los NPC del juego (`INICIO: DO`, `inventory.add`, `after`, …) que el juego ejecuta al activar un NPC.

**Encode**:
Un Script codificado en Base64, listo para que el juego lo cargue. Es la unidad que se guarda, se importa y se comparte.
_Avoid_: Payload, txt

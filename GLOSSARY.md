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
Un Item base modificado para mostrar una sola Pieza (cualquiera, de cualquier SWF) en una sola Parte del cuerpo (cualquiera); por ejemplo, una máscara en la mano. Si el Item base es una Prenda, se ve al ponérsela; si es un Item de mochila, al usarlo. Los demás jugadores la ven así y se puede intercambiar. Varias se reciben juntas en un mismo Encode, cada una con otro Item base. Sigue trucada en las entregas siguientes (el SWF trucado de su Item base sigue activo) hasta que se quitan las reglas del programa.
_Avoid_: Item trucado, objeto trucado

**Item base**:
El Item existente que se modifica para crear una Prenda trucada o materializar un Look; de él toma su nombre e ícono en el juego. Puede ser una Prenda (queda en el guardarropa) o un Item de mochila.
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

## Entrega al juego

**Script**:
Un programa en el lenguaje de los NPC del juego (`INICIO: DO`, `inventory.add`, `after`, …) que el juego ejecuta al activar un NPC.

**Encode**:
Un Script codificado en Base64, listo para que el juego lo cargue. Es la unidad que se guarda, se importa y se comparte.
_Avoid_: Payload, txt

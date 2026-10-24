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
Una Prenda base modificada para que, al ponérsela, muestre una sola Pieza (cualquiera) en una sola Parte del cuerpo (cualquiera), en lugar de sus propias Piezas; por ejemplo, una máscara en la mano. Los demás jugadores la ven así y se puede intercambiar.
_Avoid_: Item trucado, objeto trucado

**Prenda base**:
La Prenda existente a partir de la cual se crea una Prenda trucada; de ella toma su nombre e ícono en el juego.

**Look** _(provisional)_:
Un conjunto de Piezas asignadas a varias Partes del cuerpo a la vez, con nombre, que se materializa en el juego como una Prenda base modificada. Se guarda y se comparte como archivo; con él se puede volver a generar.
_Avoid_: Outfit, conjunto

## Entrega al juego

**Script**:
Un programa en el lenguaje de los NPC del juego (`INICIO: DO`, `inventory.add`, `after`, …) que el juego ejecuta al activar un NPC.

**Encode**:
Un Script codificado en Base64, listo para que el juego lo cargue. Es la unidad que se guarda, se importa y se comparte.
_Avoid_: Payload, txt

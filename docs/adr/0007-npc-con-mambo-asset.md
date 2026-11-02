# 0007 — Un Item se convierte en NPC heredando de `MamboAsset` y escribiendo sus atributos

## Contexto

Las pestañas Tiendas y Portales convierten un Item en un NPC de la casa: al tocarlo abre un catálogo o lleva a otra sala. mg-tool-yt lo hace reemplazando la clase del Item por una que hereda de `NpcMamboAsset` y pone su `behavior`. Pero cada SWF de assets trae sus propias clases base, y muchos no traen `NpcMamboAsset` (por ejemplo, `costumes2`). FFDec `-importScript` no compila una clase que hereda de una clase que el SWF no tiene («not an existing type») y no puede agregar clases nuevas. Por eso mg-tool-yt solo deja usar `virtualGoods`, `virtualGoods2`, `virtualGoods3` y `cassettes`.

Lo que sí traen todos es `MamboAsset`, la clase de la que heredan las demás. Tiene un `attributes` público. Al recibir un Item, el juego llama a `process()` y manda esos atributos al servidor (`InventoryUtil.doAcquireObject`). El lugar adonde llega lo decide solo por ellos (`getInventoryFromAttributes`):
- con `wear_*` va al guardarropa;
- con `grabbable` o `questItem`, a la mochila;
- con cualquier otra cosa, a la casa.

Y `NpcMamboAsset.process()` solo hace `attributes.behavior = this.behavior` (más `monitorAttributes`).

## Decisión

La clase del Item se reemplaza por una que hereda de `MamboAsset`, con el mismo símbolo (el mismo dibujo), y en su primer cuadro escribe los atributos directamente:

```as3
attributes.behavior = "<comportamiento>";
attributes.monitorAttributes = false;
stop();
```

Así cualquier Item de cualquier SWF puede ser un NPC. Probado en el juego: una Prenda de `costumes2` llega a la casa como la tienda `brujaMesa`, y sigue así al volver a entrar sin Fiddler. Después de trucar, se vuelve a leer el código para verificar que quedó el comportamiento.

Lo que hace cada comportamiento se lee de su guion (`npc/<comportamiento>.npc`) con las órdenes del juego (`NpcActionRunner`):
- `catalog` y sus variantes: **tienda**;
- `room.change` y `room.random`: **portal**;
- `minigame` y `launch.html5`: **minijuego**.

## Alternativas descartadas

- **Heredar de `NpcMamboAsset` como mg-tool-yt**: solo sirve en los SWF que la traen.
- **Cambiar el padre de la clase en el bytecode (P-code)**: FFDec solo reemplaza el código de los métodos, no el padre de una clase. Habría que editar el ABC a mano.

## Consecuencias

- El mismo mecanismo sirve para otros destinos (`mgitems.mambo`). En Acciones, un Item que no es de mochila llega a la mochila con `attributes.grabbable` y hace la acción con `attributes.attr_action` (y `attr_effect`), como `UsableMamboAsset`, que no todos los SWF traen. Probado en el juego con la tostadora de `virtualGoods` (#108). Para Prendas, ver #109.
- Si el juego cambia `MamboAsset` o cómo decide adónde llega un Item, hay que revisarlo.

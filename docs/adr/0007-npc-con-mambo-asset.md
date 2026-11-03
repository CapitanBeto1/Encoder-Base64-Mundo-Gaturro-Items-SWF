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

## SWF que no traen ni siquiera `MamboAsset`

Unos pocos SWF son solo un envoltorio de un dibujo del gran `assets.swf` y no traen `MamboAsset` (por ejemplo `socialNetBackgrounds`, un fondo de 23 cuadros, o `YoBackgrounds`). Ahí no se puede heredar de `MamboAsset`.

Pero el juego lee los atributos por «duck typing», no por tipo: `InventoryUtil.doAcquireObject` hace `if("attributes" in item) customAttributes.mergeObject(item.attributes)`. No exige `MamboAsset`; alcanza con que el Item tenga una propiedad `attributes`. Así que la clase se deja heredando de su base original (`MovieClip`…) y se le pone lo mismo que trae `MamboAsset` (que es solo eso): sus campos (`blocks`, `sizeW`, `sizeH`, `attributes = {}`, `questItem`), `process()` y el `Security.allowDomain("*")` de su constructor, sin el cual el cliente del juego no puede leer un objeto de otro SWF.

Los atributos se escriben en el **constructor**, no en el primer cuadro: el juego crea el Item (`Library.getItem` hace `new`) y le pasa la instancia a `doAcquireObject` en el acto.

```as3
public function SocialNetBackgrounds()
{
   super();
   Security.allowDomain("*");
   Security.allowInsecureDomain("*");
   attributes.behavior = "<comportamiento>";
   attributes.monitorAttributes = false;
   addFrameScript(0,this.frame1);   // frame1: stop();
}
```

Primera prueba en el juego (sin `allowDomain`, sin los campos de `MamboAsset` y con los atributos en el primer cuadro): el SWF trucado llegó, pero el objeto quedó como decoración común, sin comportamiento.

Solo se usa para comportamiento (escribe únicamente en `attributes.*`, lo único que comparten todas las bases); para los demás destinos se sigue exigiendo `MamboAsset` (`mgitems.mambo.clase_mambo`, parámetro `sin_mambo_ok`).

Caso de uso: `socialNetBackgrounds.SocialNetBackgrounds` con comportamiento `painting` (un guion real del juego) es un objeto de la casa que muestra, de sus 23 fondos, el que se elija. `painting` guarda el cuadro en un atributo persistido del objeto (`self.attrPersist frame`), lo avisa a la sala (`room.message update`) y cada visitante lo aplica (`self.state $(self.attr.frame)`): el fondo elegido (p. ej. una playa) se ve en la casa, para todos, y sigue al volver a entrar. El dueño cambia de fondo tocándolo.

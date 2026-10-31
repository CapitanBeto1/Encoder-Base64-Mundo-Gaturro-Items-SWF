# Los Encodes y SWF trucados se entregan al juego interceptando sus pedidos por proxy

El juego (Mundo Gaturro Desktop, Electron + Pepper Flash) carga `lola.npc` y los SWF de assets desde `cdn-ar.mundogaturro.com`; el programa los reemplaza respondiendo esos pedidos a través de un proxy, como hace hoy el AutoResponder de Fiddler. Todas las funciones se construyen sobre Fiddler automatizado (escribir las reglas, borrar el caché del juego, reiniciar), porque ya está probado. Reemplazarlo por un proxy propio embebido (mitmproxy), para que el usuario no tenga que instalar ni configurar nada, queda para mucho más adelante, después del editor visual de Looks.

## Considered Options

- **Escribir el Encode directamente en el caché del juego**: descartado; es el formato blockfile de Chromium y está bloqueado mientras el juego corre.
- **Modificar el `app.asar` del juego**: descartado; se pierde con cada actualización del juego y es lo más invasivo.

## Consequences

- El caché HTTP del juego guarda `lola.npc` con una URL fija, así que hay que borrarlo antes de cada entrega.
- Una Prenda trucada queda guardada en el servidor al crearse: el proxy solo hace falta en ese momento, no mientras se juega. Salvo las Prendas de `clothes1`, la ropa personalizable del juego (`customization.includeList` en `cfgs/gameplay.json`): de esas el servidor no guarda lo trucado y, al volver a entrar, vuelven a ser las originales, con Fiddler o sin él (probado en el juego, también con otras herramientas). Por eso no sirven de Item base.

# 0006 — La animación de las acciones se reproduce con un simulador propio

## Contexto

La vista previa de la pestaña Acciones tiene que mostrar la animación entera, idéntica a la del juego. El Gaturro animado que se puede leer sin el cliente (`assets.GaturroMC` de `superHeroesTrajes`) tiene 84 de las 106 animaciones, iguales cuadro por cuadro a las del juego de hoy. Pero no es una película: en sus cuadros hay código (`addFrameScript`) que frena, salta a otro cuadro y lleva los ojos, la boca y la cabeza a otro cuadro (`eyes`, `mouth`, `headAction`). La cabeza, los ojos y la boca tienen su propia línea de tiempo, con sus propios `stop()`. FFDec exporta cuadros sin correr ese código, así que todo avanza aunque el juego lo haya frenado (por ejemplo, salen los ojos con «$»).

## Decisión

Se reproduce el Gaturro como Flash Player, en Python (`mgitems.animacion`):
- 24 cuadros por segundo, los de `MMO.swf`;
- cada clip que anda pasa al cuadro siguiente y arma lo que coloca o saca su línea de tiempo;
- después corre el código de los cuadros a los que se llegó;
- saltar para atrás conserva lo que sigue en la misma profundidad con el mismo símbolo;
- la Pieza de la acción va en `objects_ph` y se frena en su último cuadro (`stopObjectOnLastFrame`);
- la del efecto va en la cabeza.

El código se entiende solo si es una de las formas que aparecen en el Gaturro (frenar, seguir, saltar, llamar a un método de la clase, `getChildAt`, las condiciones de transporte). Un error de ActionScript corta el código de ese cuadro, como en el juego; un código que no se entiende no se adivina: la animación no se muestra.

Cada cuadro se dibuja «congelado»: un sprite de un solo cuadro, cuyos clips son a su vez sprites congelados en el cuadro en que están. FFDec los exporta a SVG de una vez y se guardan; las Piezas se ponen con las mismas reglas que la vista previa quieta (ADR 0003).

## Alternativas descartadas

- **Exportar los cuadros con FFDec tal cual**: adelanta los clips que el juego frena.
- **Un emulador de Flash (Ruffle)**: un programa más para descargar, que igual necesita copiar del cliente cómo pone las Piezas, y que no es idéntico al Flash original en todos los casos.

## Consecuencias

- Las 22 animaciones que el Gaturro legible no tiene no se muestran: se avisa.
- Si el juego cambia el código de sus cuadros con algo nuevo, esa animación deja de mostrarse (con aviso) hasta que el simulador lo entienda.

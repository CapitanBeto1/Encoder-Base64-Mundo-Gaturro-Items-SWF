# El Gaturro del editor de Looks es el original del juego, con las Piezas puestas como las pone el juego

El editor de Looks existe para que el jugador sepa exactamente cómo se va a ver en el juego. Por eso el Gaturro que muestra tiene que ser idéntico, 1:1, al del juego; si no se consigue el original, el editor no muestra ningún Gaturro. Un Gaturro dibujado "parecido" se probó y se rechazó: es una vista previa falsa.

El cuerpo es `assets.GaturroMC`, la clase que usa el cliente del juego. El cliente (`MMO.swf`) está cifrado y el programa no lo descifra, pero la misma clase viene sin cifrar en SWF de assets del juego (`fashion_nuevo`, de un cuadro, y `superHeroesTrajes`, el Gaturro completo con todas sus animaciones; los dos tienen el mismo dibujo). Se usa su primer cuadro, que en la versión animada tiene la etiqueta `standBy`, la del Gaturro quieto (`AvatarClipState.STAND`). FFDec lo exporta a SVG y conserva el nombre de instancia de cada clip como `id`.

Las Piezas (primer cuadro de cada una, en SVG con su punto de anclaje) se ponen con las reglas del cliente:

- `Gaturro.attempt`: la Pieza de la Parte del cuerpo `P` va en cada clip vacío llamado `P`, `PFore` o `PBack` (salvo `clothBack` para el Torso), con la transformación del clip; así quedan en la capa y el lugar exactos. Si dos Partes van al mismo clip, queda la del final de `AvatarBodyEnum.getList`.
- `setColor`: los clips `color1`, `color2` y `colorEye` (del cuerpo y de las Piezas) se pintan enteros del color del jugador, conservando la transparencia. Los colores de fábrica son `#FFF200`, `#DDB42D` y `#FFFFFF` (`ColorPickerModal`); el jugador elige los suyos.
- `lookForHideParts`: una Pieza cuya clase contiene `hide_` o `invisible_` esconde los clips hermanos de su hueco que no son huecos de Partes del cuerpo.

## Considered Options

- **Un Gaturro propio dibujado en SVG**: rechazado por el dueño del proyecto; no es el del juego.
- **Descifrar el cliente**: descartado; sería saltear una protección del juego y se rompería cada vez que la cambien.
- **Ruffle (reproductor de Flash)**: innecesario; el SVG reproduce el cuadro quieto con las reglas del juego, sin sumar 10 MB.

## Consequences

- Si el juego deja de publicar `assets.GaturroMC` sin cifrar en esos SWF, el editor no muestra ningún Gaturro y lo avisa; nunca una aproximación.
- Se ve el Gaturro quieto, de frente, sin animación. Las Partes del cuerpo que el juego no pone en el Gaturro (por ejemplo, `accesories2`) se avisan como "no se ven en el juego".
- `lookForHideParts` en el juego solo esconde partes del cuerpo de los Gaturros ciudadanos; el editor siempre las esconde.
- El repositorio no contiene arte del juego: el cuerpo y las Piezas se exportan en la computadora del jugador.

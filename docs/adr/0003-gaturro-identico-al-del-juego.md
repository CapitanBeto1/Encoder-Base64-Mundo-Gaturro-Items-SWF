# El Gaturro del editor de Looks tiene que ser idéntico al del juego; nunca una aproximación

El editor de Looks existe para que el jugador sepa exactamente cómo se va a ver en el juego. Por eso el Gaturro que muestra tiene que ser idéntico, 1:1, al del juego: mismo dibujo, proporciones, anclajes de cada Parte del cuerpo y orden de capas. Si no hay un Gaturro idéntico, el editor no muestra ningún Gaturro.

Las Piezas sí se pueden mostrar exactas: el primer cuadro de cada una, exportado a SVG con FFDec, conserva su punto de anclaje en el `<g transform>` de afuera.

El cuerpo del Gaturro común (`GaturroMC`, con un clip vacío y con nombre por cada Parte del cuerpo donde el juego mete cada Pieza) solo se encontró dentro del cliente del juego (`MMO.swf`), que está cifrado en la instalación y en el CDN. El programa no lo descifra: sería saltear una protección del juego y se rompería cada vez que el juego la cambie.

## Considered Options

- **Un Gaturro propio dibujado en SVG, con anclajes medidos sobre Piezas reales**: se probó y se rechazó. Un cuerpo "parecido" es una vista previa falsa; el dueño del proyecto prefiere no tener nada.
- **Ruffle (reproductor de Flash) con un SWF propio que instancia las clases del juego**: tiene el mismo problema del cuerpo, necesita compilar AS3 y suma unos 10 MB.
- **Cuerpos de transformación (`avatars/*.swf`, sin cifrar)**: son animales y disfraces, no el Gaturro común.

## Consequences

- El editor visual queda bloqueado hasta encontrar una fuente del Gaturro original que el programa pueda usar sin descifrar el cliente; buscarla es el trabajo pendiente.
- Lo que se conserva: exportar las Piezas a SVG con su anclaje y ponerlas en su Parte del cuerpo, en orden de capas. Los anclajes actuales son provisorios y se reemplazan por los del cuerpo original.
- El repositorio no contiene arte del juego: todo se exporta en la computadora del jugador.

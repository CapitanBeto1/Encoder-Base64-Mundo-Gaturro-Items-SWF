# El programa avisa dónde llega cada Item, con las reglas del cliente del juego

Algunos Items que se agregaban con un Encode "no aparecían en ningún lado". Para saber por qué con certeza se leyó el cliente del juego (`MMO<versión>.swf`). Viene cifrado con un XOR cuya clave el cargador recibe después de iniciar sesión, así que se sacó ya descifrado de la memoria del juego abierto, solo leyendo, en la computadora del usuario y con su permiso. `inventory.add` llama a `GaturroRoomAPI.giveUser` y de ahí a `InventoryUtil.acquireObject`, que:

- crea como mascota los de `OwnedNpcFactory.VALID_PETS`;
- descarta sin avisar, solo por el nombre:
  - los del álbum `mundial2026/album`;
  - los exclusivos de bolsillo o catálogo (`pocket…`, `…_catalog`, `gatoonsClothes…_npc`);
  - los que tienen `_so` u `_on` después del principio;
  - los de `ItemControl.prohibitedAssets` (`achievements.`, `acciones.`, `bannersThumbs.`, `medals.`, `_efecto`…);
  - unos pocos prohibidos para usuarios (`nik.*`, `clothes1.remeraQB9`, `pruebas.test_on`);
- elige el inventario por los atributos que arma la clase del Item:
  - `vehicle` o `wear_*` → guardarropa;
  - `grabbable` o `questItem` → mochila;
  - el resto → casa;
- no le pide al servidor los Items con `session = true`: viven solo hasta salir del juego.

Las mascotas: el juego crea las de `VALID_PETS`, pero solo aparecen en el perfil si su clase trae `nameOwnedNpc` y un `behaviorOwnedNpc` válido (si no, el juego la borra al sacarla). Las comunes dadas directo (`pet.koala`, `pet.dragon`…) no lo traen y llegan a la casa como adorno; la mascota de verdad es su casita (`pet.koalaHouse`). Las Prendas sin Piezas (`beach.collarCalavera`) llegan a la mochila y no se pueden poner, y las que usan una Parte que el Gaturro no tiene (`anime.gorroRigby`, `"hat"`) no se ven al ponérselas. El guardarropa (`ClosetGuiModal`) saca los Items de misión (`questItem`), como `bruja.pocimaAlas`.

Se confirmó en el juego con un Encode de prueba (`pet.koala`, `pet.koalaHouse`, `animus.pioPet`, `beach.collarCalavera`, `anime.gorroRigby`, `bruja.pocimaAlas`, `granja.PapaCrop`): cada uno llegó donde dicen estas reglas.

Después, la mochila no muestra la ropa de mascota (`attr_pet_*`): solo aparece al personalizar una mascota. Y `shouldAppear` oculta los `granja.*`, `penguin*` y `privateRoom*`. El inventario no tiene límite de lugar (`gameplay.json`: `"limit": false`).

Pasaporte (`PassportControl.VIP_PACKS`): las Piezas o Items con `invisibles/`, `invisible_`, `mime.disfrazMimo`, `jeanMimo_on`, `gorroMimo_on`, `gatupacks/hw18.hide_hw18_on` o `easter2021.disfrazBunny` solo se los puede poner quien tiene pasaporte: sin pasaporte, el guardarropa dice «ESTE OBJETO REQUIERE PASAPORTE» y el Gaturro no los dibuja. Se marcan con «Pasaporte» en «Agregar Items» y en Looks.

Puesta en el Gaturro, una Pieza no siempre se ve (`Gaturro.setAsset`/`add`; `mgitems.se_ve`):
- nunca se ven la ropa de mascota (`petClothes`), las de más de 300×300 (paredes, pisos) y las prohibidas para usuarios;
- `troublesomeItems` (`cfgs/gameplay.json`) fija la única Parte donde van algunas, y el juego las saca de cualquier otra; con Parte vacía (instrumentos, objetos de acción) no van en ninguna;
- los vehículos (Piezas con `type`) solo van en la Parte `transport`, y ahí no va nada más.

Looks tiene un casillero y una categoría Transporte, marca en rojo y al final lo que no se vería donde va, y la vista previa no dibuja lo que el juego no dibujaría. Un vehículo es una Pieza con `type` (propio, o heredado de `TransportOnMamboAsset`, que lo trae vacío). Con un transporte el juego pone al Gaturro en el cuadro `transportStand_<type>` (`transportStand` si está vacío) y al vehículo en `off`. La vista previa hace lo mismo con el Gaturro animado de `superHeroesTrajes` (sin cifrar, mismos cuadros que el del juego): congela los dos en ese cuadro (`swf.congelado_en`), para que cada clip de adentro quede en su cuadro 1 como con `gotoAndStop`. Si esa pose no está en ese Gaturro (`walk`, `nube`, más nuevas) o el vehículo tiene una parte `foreground`, no lo dibuja y avisa.

`mgitems.destinos` copia esas reglas. El índice guarda, para cada Item, su destino y, si no llega bien, el motivo. «Agregar Items» lo muestra debajo de cada Item (en rojo si no llega bien). «Agregar todos» saltea los descartados. Generar el Encode avisa cuáles no van a quedar bien.

## Considered Options

- **No dejar agregar los descartados** u **ocultarlos**: descartado por el usuario. Prefiere verlos marcados y que el programa avise.

## Consequences

- Lo que el servidor rechace por su cuenta no se ve en el cliente, así que no está en las reglas.
- Si el juego cambia esas listas, hay que volver a leer el cliente (con el juego abierto) y actualizar `destinos.py`.

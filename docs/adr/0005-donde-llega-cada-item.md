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

Transporte y efectos que duran (probado en el juego):
- Al entrar a una sala, el juego saca el transporte si en el guardarropa no hay un Item que se llame como la Pieza sin el final (`barbie.vacio_on` → `barbie.vacio`), salvo unos «mágicos» (`gatoonsClothes.`, `invisibles/`, `virtualGoods3.`…): `GaturroUserAvatarView.checkIfOwnsTransport`. Por eso un transporte puesto por una Prenda (aun la original `barbie.rollers`) o por `user.attr` se cae al cambiar de sala.
- El efecto de cabeza (`effect = "head.<swf>.<Pieza>"`, `GaturroEffectsManager.applyHead`) pone cualquier Pieza sobre la cabeza, donde va el sombrero, sin mirar si es un vehículo. No pone lo de `troublesomeItems` con otra Parte que `hats` ni lo de 150 o más. El servidor no lo guarda entre sesiones.
- Looks tiene el casillero «Cabeza (efecto)»: con un Item de mochila de base queda un Item de usos ilimitados que lo pone al usarlo, de nuevo cada vez que se entra.
- El comando de NPC `user.attr <clave> <valor>` cambia cualquier atributo del avatar, pero lo que no respalda un Item se pierde igual.

Acciones de mochila (probado en el juego con `showObject`, `showObjectUp` y `flag`):
- Un Item de mochila guarda la acción en `adds.action = "<animación>"` o `"<animación>.<swf>.<Pieza>"`. Al usarlo, `BagGuiModal` copia `adds` al Gaturro (antes rechaza lo de `isProhibitedInAction`: «Esta acción no está disponible»). `GaturroAnimationController.doRunAction` lo lleva al cuadro de la animación y carga la Pieza en `objects_ph` sin mirar si es un vehículo. La Pieza queda en su último cuadro hasta la próxima acción.
- No la hace si el texto dice `run`, `zombieStand` o `zombieWalk` en cualquier lugar (`isAllowedAnimation`), si la animación tiene reglas en `validItems.action` (teléfono solo con `phones.`/`transmisor`; fútbol no con `magia.poder` ni `gatoons.`) o si el Gaturro camina. La Pieza no se ve si mide más de 150×150 o si es vacía.
- Las 106 animaciones son los cuadros con nombre del `assets.GaturroMC` del cliente de hoy. El de `superHeroesTrajes`, que se puede leer sin el cliente, tiene 84 de ellas, iguales cuadro por cuadro.
- `mgitems.acciones` copia esas reglas; la pestaña Acciones solo acepta bases de mochila.
- La acción también muestra un objeto de la casa (`"<animación>.<swf>.<objeto>"`, sin `_on`): el juego lo carga igual que una Pieza (probado: fútbol con `greek.columna`). Rige el mismo límite de 150×150. La grilla de Acciones tiene la categoría Decoración (`Nucleo.decoracion_de_swfs`); el índice guarda el tamaño de los objetos de la casa que no entran.

`mgitems.destinos` copia esas reglas. El índice guarda, para cada Item, su destino y, si no llega bien, el motivo. «Agregar Items» lo muestra debajo de cada Item (en rojo si no llega bien). «Agregar todos» saltea los descartados. Generar el Encode avisa cuáles no van a quedar bien.

## Considered Options

- **No dejar agregar los descartados** u **ocultarlos**: descartado por el usuario. Prefiere verlos marcados y que el programa avise.

## Consequences

- Lo que el servidor rechace por su cuenta no se ve en el cliente, así que no está en las reglas.
- Si el juego cambia esas listas, hay que volver a leer el cliente (con el juego abierto) y actualizar `destinos.py`.

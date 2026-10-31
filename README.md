# MG Items

Programa para Windows que agrega Items de **Mundo Gaturro** a tu inventario, solo con clics.

Buscás los Items en los SWF del juego (el programa los descarga solo), armás una lista, y con **Agregar al juego** el programa prepara todo: Fiddler, el caché del juego y la regla para el NPC Lola. Después entrás al juego, hacés clic en Lola y recibís los Items.

> **Estado:** en desarrollo. Funcionan agregar Items, trucar Prendas, armar Looks y las acciones (ver la [spec](../../issues/1)).

## Qué hace

- **Catálogo de SWF del juego** con buscador: 445 SWF con Items, descargados del servidor del juego cuando hacen falta y guardados para la próxima vez.
- **Buscar Items** por el comienzo del nombre, con sugerencias e imágenes mientras escribís (por ejemplo `remera`, `zapa, campera`).
- **Lista de Items** con imagen y cantidad de cada uno; se pueden quitar o agregar a mano (`clothes1.remera5`).
- **Trucar Prenda**: un Item que, en vez de lo suyo, muestra una sola Pieza de cualquier SWF (por ejemplo, un «Otro») en la Parte del cuerpo que elijas; armás una lista y las recibís todas en un solo Encode. Las Prendas de `clothes1` no sirven de base: el juego no guarda lo trucado y vuelven a ser las originales.
- **Looks**: armás un Gaturro con Piezas de cualquier SWF y lo recibís en una sola Prenda o Item; se guardan y se pasan en archivos.
- **Acciones**: un Item de mochila que, al usarlo, hace una animación del juego mostrando cualquier Pieza; la vista previa la reproduce como el juego.
- **Encode**: generarlo, copiarlo, guardarlo como `.txt` o importar uno existente (pegado o desde archivo).
- **Agregar al juego**: cierra el juego y Fiddler, pone la regla de Lola en el AutoResponder de Fiddler (respetando tus reglas), borra el caché del juego y vuelve a abrir todo.
- **Configuración**: revisa que estén Mundo Gaturro Desktop y Fiddler, y explica paso a paso qué falta.

## Requisitos

- Windows 10 u 11.
- [Mundo Gaturro Desktop](https://www.mundogaturro.com) instalado.
- [Fiddler Classic](https://www.telerik.com/fiddler/fiddler-classic) (gratis) con el descifrado HTTPS activado y su certificado instalado. Si falta algo, el botón **Configuración** del programa dice cómo hacerlo.

No hace falta instalar Python ni Java: el instalador trae todo lo necesario.

## Instalación

1. Descargá `MGItems-Setup-<versión>.exe` y abrilo.
2. Si Windows muestra "Windows protegió su PC", tocá **Más información** → **Ejecutar de todas formas** (el instalador no está firmado digitalmente).
3. Seguí el asistente. Se instala para tu usuario, sin pedir permisos de administrador, y queda en el menú Inicio como **MG Items**.

Para desinstalarlo: Configuración de Windows → Aplicaciones → MG Items → Desinstalar.

> Todavía no hay una versión publicada para descargar: por ahora el instalador se arma desde el código (ver [Desarrollo](#desarrollo)).

## Cómo se usa

1. Abrí **Configuración** y fijate que esté todo en verde.
2. Elegí un SWF del juego en **Buscar en un SWF** (por ejemplo `clothes1`).
3. Escribí el comienzo del nombre de los Items y elegí de las sugerencias, o tocá **Buscar** para agregar todos los que coinciden.
4. Ajustá las cantidades y tocá **Generar Encode**.
5. Tocá **Agregar al juego** y, cuando cargue Mundo Gaturro, andá hasta **Lola** y hacé clic en ella.

Mientras la regla esté activa, Lola entrega ese Encode cada vez. Se puede quitar desde **Configuración → Quitar la regla de Fiddler** (tus otras reglas no se tocan).

## Aclaraciones

- Es un programa no oficial: no tiene relación con Mundo Gaturro ni con sus creadores. Usalo bajo tu responsabilidad.
- No todos los Items se pueden conseguir: algunos fueron quitados del juego o tienen errores, y eso no depende del programa.
- Todo lo que hace el programa se puede hacer a mano (FFDec, un Encode en Base64 y una regla de Fiddler); el programa lo automatiza.

## Desarrollo

Python 3.12 o más nuevo, en Windows.

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python scripts\obtener_binarios.py    # FFDec y Java en vendor\ (para las imágenes)
.venv\Scripts\python -m mgitems                      # abrir el programa
.venv\Scripts\python -m pytest                       # pruebas
```

- **Instalador:** `.venv\Scripts\python scripts\armar_instalador.py` arma `dist\MGItems\` con PyInstaller y, si está [Inno Setup 6](https://jrsoftware.org/isinfo.php), `dist\MGItems-Setup-<versión>.exe`.
- **Catálogo de SWF:** `.venv\Scripts\python scripts\armar_catalogo.py [nombres.txt]` lo vuelve a armar desde el servidor del juego.
- El lenguaje del proyecto está en [GLOSSARY.md](GLOSSARY.md) y las decisiones de arquitectura en [docs/adr](docs/adr).

## Software de terceros

El instalador incluye, sin modificarlos:

- **[JPEXS Free Flash Decompiler (FFDec)](https://github.com/jindrapetrik/jpexs-decompiler)** 26.3.0, licencia GPL v3. Se usa como programa aparte para exportar las imágenes de los Items. Su código fuente está en su repositorio.
- **[Eclipse Temurin](https://adoptium.net) JRE** 21, licencia GPL v2 con Classpath Exception. Lo necesita FFDec.
- **[Fraunces](https://github.com/undercasetype/Fraunces)**, licencia SIL Open Font License 1.1: la letra de la interfaz (alternativa libre a Cooper Black, la del juego). Va con su licencia en `src/mgitems/ui/fuentes/`.
- Bibliotecas de Python empaquetadas con PyInstaller, entre ellas [pywebview](https://github.com/r0x0r/pywebview) (BSD) y [pythonnet](https://github.com/pythonnet/pythonnet) (MIT).

Los textos de esas licencias van dentro de la carpeta del programa instalado.

## Licencia

[Apache 2.0](LICENSE).

"""Cualquier Item convertido en otra cosa, escribiendo sus atributos directamente (ADR 0007).

Cada SWF de assets trae sus propias clases base, pero todos traen `MamboAsset`, que tiene un `attributes` público.
Al recibir un Item, el juego le pide `process()` y manda esos atributos al servidor; según ellos, el Item llega al
guardarropa (`wear_*`), a la mochila (`grabbable`) o a la casa (lo demás), y hace lo que digan (`behavior`,
`attr_action`…). La clase del Item pasa a heredar de `MamboAsset`, con su mismo dibujo, y escribe los atributos en
su primer cuadro. Probado en el juego: una Prenda como tienda de la casa y un objeto de la casa como Item de
mochila que hace una acción, y siguen así al volver a entrar.
"""

import re

_CLASE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SIMBOLO = re.compile(r'\[Embed\(source="[^"]*",\s*symbol="([^"]+)"\)\]')
# Lo que se escribe entre comillas en el código: rutas de Piezas, animaciones, comportamientos ("magia/portal").
_VALOR = re.compile(r"^[A-Za-z0-9_./\-]+$")


class NoSePuedeConvertir(ValueError):
    """El Item no se puede convertir (su código no tiene la forma esperada, o un valor no es válido)."""


def clase_mambo(fuente: str, clase: str, lineas: list[str]) -> str:
    """El código AS3 de `clase` heredando de `MamboAsset`, con el mismo dibujo (`fuente`: su código) y `lineas` en
    su primer cuadro."""
    if not _CLASE.match(clase):
        raise NoSePuedeConvertir(f"clase no válida: {clase}")
    simbolo = _SIMBOLO.search(fuente)
    if not simbolo:
        raise NoSePuedeConvertir(f"{clase} no tiene dibujo")
    cuerpo = "\n".join(f"         {linea}" for linea in [*lineas, "stop();"])
    return f'''package
{{
   [Embed(source="/_assets/assets.swf", symbol="{simbolo.group(1)}")]
   public dynamic class {clase} extends MamboAsset
   {{
      public function {clase}()
      {{
         super();
         addFrameScript(0,this.frame1);
      }}

      internal function frame1() : *
      {{
{cuerpo}
      }}
   }}
}}
'''


def texto(valor: str) -> str:
    """`valor` entre comillas, para el código; NoSePuedeConvertir si tiene algo que no va."""
    if not isinstance(valor, str) or not _VALOR.match(valor):
        raise NoSePuedeConvertir(f"valor no válido: {valor}")
    return f'"{valor}"'


def clase_de_mochila(fuente: str, clase: str, adds: dict[str, str]) -> str:
    """`clase` convertida en un Item de mochila usable (sin límite de usos) que, al usarlo, le pone al Gaturro
    `adds` (`{"action": …, "effect": …}`), como `UsableMamboAsset`, que no todos los SWF traen."""
    return clase_mambo(fuente, clase, [
        "blocks = false;",
        "questItem = true;",
        "attributes.grabbable = true;",
        "attributes.session = false;",
        *(f"attributes.attr_{nombre} = {texto(valor)};" for nombre, valor in adds.items() if _CLASE.match(nombre)),
    ])


def atributo_en_codigo(fuente: str, nombre: str) -> str | None:
    """El valor que el código AS3 de un Item convertido escribe en `attributes.<nombre>`, o None."""
    encontrado = re.search(r"\battributes\." + re.escape(nombre) + r'\s*=\s*"([^"]*)"', fuente)
    return encontrado.group(1) if encontrado else None

"""Lo que usan varias partes del núcleo."""

from mgitems.items import items_del_swf, piezas_del_swf


def _cantidad(valor) -> int | None:
    """La cantidad como entero mayor que 0, o None si no es válida (la interfaz puede mandar texto)."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str) and valor.strip().isdigit():
        valor = int(valor)
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return valor if isinstance(valor, int) and valor > 0 else None


def _simbolos_con_imagen(simbolos: list[tuple[int, str]]) -> dict[int, str]:
    """Los símbolos de Items y Piezas (los que tienen imagen para mostrar): id → clase."""
    clases = [clase for _, clase in simbolos]
    con_imagen = set(items_del_swf(clases)) | set(piezas_del_swf(clases))
    return {id_: clase for id_, clase in simbolos if clase in con_imagen}

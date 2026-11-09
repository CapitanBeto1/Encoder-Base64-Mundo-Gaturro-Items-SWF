"""El núcleo del programa: lo que hace MG Items, sin la ventana. Es la única puerta para la interfaz y las pruebas.

Está repartido en una parte por función (`entrega`, `swfs`, `trucar`, `acciones`, `looks`, `npcs`, `busqueda`,
`imagenes`, `encodes`; los guardados están en `mgitems.guardados`); `Nucleo` las junta y arma el estado que comparten.
"""

import threading

from mgitems.animacion import Linea
from mgitems.busqueda import DatosBusqueda
from mgitems.catalogo import cargar_catalogo
from mgitems.categorias import IndicePiezas
from mgitems.entorno import Entorno, Sistema
from mgitems.entrega import Procesos
from mgitems.fondos import CuadrosFFDec, Fondos
from mgitems.fuente import FuenteCDN
from mgitems.guardados import Guardados
from mgitems.iconos import ExportadorFFDec
from mgitems.npcs import Comportamientos
from mgitems.nucleo.acciones import Acciones
from mgitems.nucleo.busqueda import Busqueda
from mgitems.nucleo.colores import Colores
from mgitems.nucleo.configuracion import Configuracion
from mgitems.nucleo.encodes import Encodes
from mgitems.nucleo.entrega import Entregar
from mgitems.nucleo.imagenes import Imagenes
from mgitems.nucleo.looks import Looks
from mgitems.nucleo.npcs import Npcs
from mgitems.nucleo.swfs import Swfs
from mgitems.nucleo.trucar import Trucar
from mgitems.prendas import ItemBase, ItemsBaseFFDec


class Nucleo(Entregar, Swfs, Trucar, Acciones, Looks, Npcs, Busqueda, Imagenes, Encodes, Configuracion, Colores):
    """Todo lo que hace el programa, para la interfaz (por `app.Puente`) y las pruebas. Cada parte vive en su módulo;
    acá se arma el estado que comparten (el SWF abierto, los SWF trucados de cada Encode, el entorno…)."""

    def __init__(
        self,
        sistema: Sistema | None = None,
        procesos: Procesos | None = None,
        fuente: FuenteCDN | None = None,
        catalogo: list[dict] | None = None,
        exportador: ExportadorFFDec | None = None,
        prendas_ffdec: ItemsBaseFFDec | None = None,
        indice: IndicePiezas | None = None,
        comportamientos: Comportamientos | None = None,
        datos_busqueda: DatosBusqueda | None = None,
        fondos: Fondos | None = None,
        cuadros: CuadrosFFDec | None = None,
    ):
        self._indice = indice or IndicePiezas()
        self._entorno = Entorno(sistema or Sistema())
        # Mis Looks, Mis acciones, Mis Prendas trucadas, Mis tiendas…: todos iguales (`mgitems.guardados`).
        self.guardados = Guardados(self._entorno.carpeta_programa)
        self._fondos = fondos or Fondos()
        self._cuadros = cuadros
        self._comportamientos = comportamientos or Comportamientos()
        self._comportamientos_a_mano: dict[str, dict] = {}  # los que no trae el programa, ya leídos del juego
        self._datos_busqueda = datos_busqueda
        self._progreso_busqueda = {"bajando": False, "hechos": 0, "total": 0}
        self._prendas_ffdec = prendas_ffdec or ItemsBaseFFDec()
        self._prendas: dict[tuple[str, str], dict[str, ItemBase]] = {}
        self._trucos: dict[str, dict[str, bytes]] = {}  # Encode → SWF trucados que necesita
        self._otros_swf: dict[str, bytes] = {}  # SWF de donde se sacan Piezas para trucar
        self._lineas: dict[tuple[str, str], Linea] = {}  # (SWF, versión) → sus líneas de tiempo, para las animaciones
        self._candado_ffdec = threading.Lock()
        self._swf_abierto: str | None = None
        self._items_del_swf: list[str] = []
        self._piezas_del_swf: list[str] = []
        self._simbolos_con_imagen: dict[int, str] = {}  # Items y Piezas: id del símbolo → clase
        self._data_swf: bytes = b""
        self._tamano_swf: int | None = None
        self._exportador = exportador or ExportadorFFDec()
        self._candado_iconos = threading.Lock()
        self._procesos = procesos or Procesos()
        self._fuente = fuente or FuenteCDN()
        self._catalogo = cargar_catalogo() if catalogo is None else catalogo

"""API del núcleo: lo único que usa la interfaz y lo único que prueban los tests.

Todas las operaciones devuelven diccionarios simples (serializables a JSON) con
`ok` y, si algo falla, un `error` en español listo para mostrar al jugador.
"""

import re
import subprocess
import threading
from dataclasses import asdict
from pathlib import Path

from mgitems.cache_swf import CacheSwf
from mgitems.catalogo import buscar_en_catalogo, cargar_catalogo
from mgitems.categorias import CacheCategorias, IndicePiezas, categorias, usos_de_piezas
from mgitems.entorno import Entorno, Sistema
from mgitems.entrega import PUERTO_FIDDLER_POR_DEFECTO, QUE_HACER_EN_EL_JUEGO, URL_LOLA, Entrega, PasoFallido, Procesos, SwfTrucado
from mgitems.ffdec import FFDecNoDisponible
from mgitems.fuente import URL_ASSETS, FuenteCDN, SinConexion, SwfNoEncontrado, Version
from mgitems.gaturro import (
    AVISO_VERSION_ANTERIOR, CLASE_CUERPO, CLASE_PLANTILLA, COLORES, SWF_CUERPO, SWF_PLANTILLA, ImagenesPiezas, componer,
    completar_con_plantilla, es_version_anterior, tiene_color_de_nariz, tiene_lugar,
)
from mgitems.iconos import ExportadorFFDec, IconosItems, version_de
from mgitems.items import (
    es_ruta_valida,
    filtrar_por_prefijos,
    items_del_swf,
    orden_natural,
    piezas_del_swf,
    separar_prefijos,
    separar_rutas,
)
from mgitems.looks import AlmacenLooks, Look, LookInvalido, archivo_de_look, look_de_archivo
from mgitems.prendas import MOCHILA, PARTES_DEL_CUERPO, PRENDA, CacheItemsBase, ItemBase, ItemsBaseFFDec, TruqueoFallido, reescribir_partes
from mgitems.script import EncodeInvalido, codificar, decodificar, generar_script, leer_script
from mgitems.swf import SwfInvalido, leer_simbolos

_NOMBRE_SWF = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*$")


class Nucleo:
    def __init__(
        self,
        sistema: Sistema | None = None,
        procesos: Procesos | None = None,
        fuente: FuenteCDN | None = None,
        catalogo: list[dict] | None = None,
        exportador: ExportadorFFDec | None = None,
        prendas_ffdec: ItemsBaseFFDec | None = None,
        indice: IndicePiezas | None = None,
    ):
        self._indice = indice or IndicePiezas()
        self._prendas_ffdec = prendas_ffdec or ItemsBaseFFDec()
        self._prendas: dict[tuple[str, str], dict[str, ItemBase]] = {}
        self._trucos: dict[str, dict[str, bytes]] = {}  # Encode → SWF trucados que necesita
        self._otros_swf: dict[str, bytes] = {}  # SWF de donde se sacan Piezas para trucar
        self._candado_ffdec = threading.Lock()
        self._swf_abierto: str | None = None
        self._items_del_swf: list[str] = []
        self._piezas_del_swf: list[str] = []
        self._simbolos_con_imagen: dict[int, str] = {}  # Items y Piezas: id del símbolo → clase
        self._data_swf: bytes = b""
        self._tamano_swf: int | None = None
        self._exportador = exportador or ExportadorFFDec()
        self._candado_iconos = threading.Lock()
        self._entorno = Entorno(sistema or Sistema())
        self._procesos = procesos or Procesos()
        self._fuente = fuente or FuenteCDN()
        self._catalogo = cargar_catalogo() if catalogo is None else catalogo

    def juego_abierto(self) -> bool:
        juego = self._entorno.ruta("juego")
        return bool(juego) and self._procesos.corriendo(juego)

    def entregar_encode(self, encode: str) -> dict:
        """Entrega el Encode al juego: regla de Fiddler para Lola, caché borrado, Fiddler y juego reabiertos.

        Si el Encode es de una Prenda trucada generada en esta sesión, también se entrega su SWF trucado.
        """
        try:
            decodificar(encode)
        except EncodeInvalido as e:
            return {"ok": False, "error": f"{e}."}
        entrega, error = self._preparar_entrega()
        if error:
            return error
        trucados, error = self._swf_trucados(encode)
        if error:
            return error
        try:
            entrega.entregar(encode, trucados)
        except PasoFallido as e:
            return self._resultado_fallido(entrega, e)
        return {"ok": True, "pasos": [asdict(p) for p in entrega.pasos], "que_hacer": QUE_HACER_EN_EL_JUEGO}

    # --- Prendas trucadas ---

    def prendas(self) -> dict:
        """Los Items base del SWF abierto: las Prendas, con la Pieza que muestra cada una en cada Parte
        del cuerpo, y los Items de mochila (`tipo`: "prenda" o "mochila").

        La primera vez para cada versión de un SWF tarda unos segundos (FFDec); después se lee guardado.
        """
        if self._swf_abierto is None:
            return {"ok": False, "error": "Primero abrí un SWF."}
        try:
            prendas = self._prendas_del_swf_abierto()
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden leer las Prendas."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron leer las Prendas: {e}"}

        presentes = {parte for p in prendas.values() if p.tipo == PRENDA for parte in p.partes}
        partes = [{"id": i, "nombre": n} for i, n in PARTES_DEL_CUERPO.items()]
        partes += [{"id": i, "nombre": i} for i in sorted(presentes - set(PARTES_DEL_CUERPO))]
        return {
            "ok": True,
            "swf": self._swf_abierto,
            "prendas": [
                {"ruta": f"{self._swf_abierto}.{p.clase}", "clase": p.clase, "tipo": p.tipo,
                 "partes": {parte: v for parte, v in p.partes.items() if p.tipo == PRENDA or parte in PARTES_DEL_CUERPO}}
                for p in sorted(prendas.values(), key=lambda p: orden_natural(p.clase))
            ],
            "partes_del_cuerpo": partes,
        }

    def piezas(self, swf: str | None = None) -> dict:
        """Todas las Piezas de un SWF (por defecto, el abierto): cualquiera va en cualquier Parte del cuerpo.

        Las de otro SWF del juego también sirven para trucar una Prenda del SWF abierto.
        """
        if swf in (None, self._swf_abierto):
            if self._swf_abierto is None:
                return {"ok": False, "error": "Primero abrí un SWF."}
            swf, piezas = self._swf_abierto, self._piezas_del_swf
        else:
            obtenido = self._datos_de_otro_swf(swf)
            if not obtenido["ok"]:
                return obtenido
            piezas = piezas_del_swf([clase for _, clase in leer_simbolos(obtenido["data"])])
        return {"ok": True, "swf": swf, "piezas": [{"ruta": f"{swf}.{p}", "clase": p} for p in piezas]}

    def items_base(self, swf: str) -> dict:
        """Los Items base (Prendas e Items de mochila) de cualquier SWF del juego: dónde se guarda un Look."""
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            return obtenido
        try:
            items = self._prendas_de(swf, obtenido["data"])
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden leer los Items base."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron leer los Items base: {e}"}
        return {"ok": True, "swf": swf, "items": [
            {"ruta": f"{swf}.{i.clase}", "clase": i.clase, "tipo": i.tipo}
            for i in sorted(items.values(), key=lambda i: orden_natural(i.clase))
        ]}

    def piezas_de_swfs(self, swfs: list | None = None) -> dict:
        """Las Piezas de varios SWF (None: todos los del juego) con su SWF y las Partes del cuerpo donde
        el juego las usa ([] si ninguna Prenda las usa: "Otros").

        Usa el índice que trae el programa. Un SWF que no está en el índice, o cuya copia descargada es
        de otra versión, se analiza acá (la primera vez tarda unos segundos) y se recuerda.
        """
        if swfs is None:
            swfs = list(dict.fromkeys([*self._indice.swfs(), *(s["swf"] for s in self._catalogo)]))
        if not isinstance(swfs, list) or not all(isinstance(s, str) for s in swfs):
            return {"ok": False, "error": "Los SWF no tienen la forma esperada."}
        piezas, errores = [], {}
        for swf in dict.fromkeys(swfs):
            obtenido = self._categorias_de(swf)
            if not obtenido["ok"]:
                errores[swf] = obtenido["error"]
                continue
            piezas += [{"ruta": f"{swf}.{clase}", "clase": clase, "swf": swf, "partes": partes}
                       for clase, partes in obtenido["piezas"].items()]
        return {"ok": True, "piezas": piezas, "errores": errores}

    def _categorias_de(self, swf: str) -> dict:
        """`{"ok", "piezas": {Pieza: [Partes]}}` de un SWF: del índice, o analizado acá si no está o cambió."""
        if not _NOMBRE_SWF.match(swf):
            return {"ok": False, "error": f"Nombre de SWF inválido: {swf}"}
        del_indice = self._indice.leer(swf)
        data = self._data_swf if swf == self._swf_abierto else self._otros_swf.get(swf)
        if data is None:
            try:
                guardado = CacheSwf(self._entorno.carpeta_cache() / "swf").leer(swf)
            except OSError:
                guardado = None
            data = guardado[0] if guardado else None
        if del_indice and (data is None or version_de(data) == del_indice.get("version")):
            return {"ok": True, "piezas": del_indice["piezas"]}
        if data is None:
            obtenido = self._datos_de_otro_swf(swf)
            if not obtenido["ok"]:
                return obtenido
            data = obtenido["data"]

        version = version_de(data)
        try:
            cache = CacheCategorias(self._entorno.carpeta_cache() / "categorias")
            guardadas = cache.leer(swf, version)
            if guardadas is not None:
                return {"ok": True, "piezas": guardadas}
            piezas = piezas_del_swf([clase for _, clase in leer_simbolos(data)])
            resultado = categorias(piezas, usos_de_piezas(swf, self._prendas_de(swf, data)).get(swf, {}))
            cache.guardar(swf, version, resultado)
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden clasificar las Piezas de {swf}."}
        except (OSError, SwfInvalido, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron clasificar las Piezas de {swf}: {e}"}
        return {"ok": True, "piezas": resultado}

    def _datos_de_otro_swf(self, swf: str) -> dict:
        """Un SWF del CDN que no es el abierto (se recuerda mientras dura el programa)."""
        if swf not in self._otros_swf:
            obtenido = self._obtener_del_cdn(swf)
            if not obtenido["ok"]:
                return obtenido
            self._otros_swf[swf] = obtenido["data"]
        return {"ok": True, "data": self._otros_swf[swf]}

    def trucar_prenda(self, base: str, parte: str, pieza: str) -> dict:
        """Genera la Prenda trucada: `base` (un Item base del SWF abierto) mostrando solo `pieza` en `parte`.

        `pieza` es una Pieza del SWF abierto o de otro (`costumes.coronaRey_on`).
        Devuelve el Encode que la agrega; al entregarlo se entrega también el SWF trucado.
        """
        resultado = self.prendas()
        if not resultado["ok"]:
            return resultado
        partes_validas = {p["id"] for p in resultado["partes_del_cuerpo"]}
        if parte not in partes_validas:
            return {"ok": False, "error": f"{parte} no es una Parte del cuerpo."}
        return self._trucar(self._swf_abierto, self._data_swf, base, {parte: pieza})

    def _trucar(self, swf: str, data: bytes, base: str, partes: dict[str, str]) -> dict:
        """Truca el Item base `base` del SWF `swf` para que muestre `partes` (Parte del cuerpo → Pieza de cualquier SWF)."""
        try:
            prendas = self._prendas_de(swf, data)
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden leer las Prendas."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron leer las Prendas: {e}"}
        if base not in prendas:
            return {"ok": False, "error": f"{base} no es una Prenda ni un Item de mochila de {swf}."}
        if not partes:
            return {"ok": False, "error": "Elegí al menos una Pieza."}

        item = prendas[base]
        piezas_propias = set(piezas_del_swf([clase for _, clase in leer_simbolos(data)]))
        valores = {}
        for parte, pieza in partes.items():
            valor, error = self._valor_de_pieza(swf, piezas_propias, pieza, con_swf=item.tipo == MOCHILA)
            if error:
                return {"ok": False, "error": error}
            valores[parte] = valor

        try:
            fuente = reescribir_partes(item, valores)
            trucado = self._prendas_ffdec.trucar(data, base, fuente, dict(valores))
        except TruqueoFallido as e:
            return {"ok": False, "error": f"No se pudo trucar la Prenda: {e}."}
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se puede trucar."}
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            return {"ok": False, "error": f"No se pudo trucar la Prenda: {e}"}

        ruta = f"{swf}.{base}"
        script = generar_script([(ruta, 1)])
        encode = codificar(script)
        self._trucos[encode] = {swf: trucado}
        return {
            "ok": True,
            "prenda": {"ruta": ruta, "tipo": item.tipo, "partes": dict(valores)},
            "items": [{"ruta": ruta, "cantidad": 1}],
            "script": script,
            "encode": encode,
        }

    def _valor_de_pieza(self, swf: str, piezas_propias: set[str], pieza: str, con_swf: bool = False) -> tuple[str | None, str | None]:
        """(cómo se escribe la Pieza en el Item base de `swf`, error).

        En una Prenda, una Pieza del mismo SWF va sin su nombre (el juego lo agrega). En un Item de
        mochila (`con_swf`) va siempre con él: se aplica tal cual al Gaturro.
        """
        swf_pieza, _, clase = pieza.rpartition(".")
        if swf_pieza in ("", swf):
            if clase not in piezas_propias:
                return None, f"{clase} no es una Pieza de {swf}."
            return (f"{swf}.{clase}" if con_swf else clase), None
        # De otro SWF se escribe "<swf>.<clase>": el juego la busca en ese SWF.
        otras = self.piezas(swf_pieza)
        if not otras["ok"]:
            return None, f"No se pudo usar una Pieza de {swf_pieza}: {otras['error']}"
        if clase not in {p["clase"] for p in otras["piezas"]}:
            return None, f"{clase} no es una Pieza de {swf_pieza}."
        return f"{swf_pieza}.{clase}", None

    def _prendas_del_swf_abierto(self) -> dict[str, ItemBase]:
        return self._prendas_de(self._swf_abierto, self._data_swf)

    def _prendas_de(self, swf: str, data: bytes) -> dict[str, ItemBase]:
        """Los Items base de un SWF, leídos con FFDec una vez por versión y guardados."""
        version = version_de(data)
        clave = (swf, version)
        if clave not in self._prendas:
            cache = CacheItemsBase(self._entorno.carpeta_cache() / "prendas")
            prendas = cache.leer(swf, version)
            if prendas is None:
                items = items_del_swf([clase for _, clase in leer_simbolos(data)])
                with self._candado_ffdec:
                    prendas = self._prendas_ffdec.analizar(data, items)
                cache.guardar(swf, version, prendas)
            self._prendas[clave] = prendas
        return self._prendas[clave]

    # --- Looks ---

    def partes_del_cuerpo(self) -> dict:
        """Las Partes del cuerpo conocidas, con su nombre en español (no hace falta un SWF abierto)."""
        return {"ok": True, "partes_del_cuerpo": [{"id": i, "nombre": n} for i, n in PARTES_DEL_CUERPO.items()]}

    def looks(self) -> dict:
        """Los Looks guardados, por nombre."""
        try:
            looks = self._almacen_looks().todos()
        except OSError as e:
            return {"ok": False, "error": f"No se pudieron leer los Looks: {e}"}
        return {"ok": True, "looks": [asdict(l) for l in sorted(looks, key=lambda l: orden_natural(l.nombre))]}

    def guardar_look(self, look: dict) -> dict:
        """Guarda un Look nuevo (sin id) o los cambios de uno guardado."""
        try:
            guardado = self._almacen_looks().guardar(Look.desde(look))
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el Look: {e}"}
        return {"ok": True, "look": asdict(guardado)}

    def duplicar_look(self, id_look: str) -> dict:
        """Una copia de un Look guardado, con otro nombre."""
        try:
            almacen = self._almacen_looks()
            original = next((l for l in almacen.todos() if l.id == id_look), None)
            if original is None:
                return {"ok": False, "error": "Ese Look ya no existe."}
            nombre = _nombre_libre(f"{original.nombre} (copia)", {l.nombre for l in almacen.todos()}, "copia ")
            copia = almacen.guardar(Look(nombre, original.base, dict(original.partes)))
        except OSError as e:
            return {"ok": False, "error": f"No se pudo duplicar el Look: {e}"}
        return {"ok": True, "look": asdict(copia)}

    def borrar_look(self, id_look: str) -> dict:
        try:
            borrado = self._almacen_looks().borrar(id_look)
        except OSError as e:
            return {"ok": False, "error": f"No se pudo borrar el Look: {e}"}
        return {"ok": True} if borrado else {"ok": False, "error": "Ese Look ya no existe."}

    def aplicar_look(self, look: dict) -> dict:
        """Genera la Prenda base modificada con todas las Piezas del Look y el Encode que la agrega.

        Si el Look no tiene Prenda base, se propone una: la primera Prenda del SWF de su primera Pieza.
        """
        try:
            look = Look.desde(look)
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        if not look.partes:
            return {"ok": False, "error": "Elegí al menos una Pieza para el Look."}

        base = look.base or self._proponer_base(look)
        if base is None:
            return {"ok": False, "error": "No se encontró una Prenda base para el Look: elegí una."}
        swf, _, clase = base.rpartition(".")
        if swf == self._swf_abierto:
            data = self._data_swf
        else:
            obtenido = self._datos_de_otro_swf(swf)
            if not obtenido["ok"]:
                return {"ok": False, "error": f"No se pudo usar la Prenda base: {obtenido['error']}"}
            data = obtenido["data"]
        resultado = self._trucar(swf, data, clase, look.partes)
        if resultado["ok"]:
            resultado["look"] = {"nombre": look.nombre, "base": base, "base_propuesta": look.base is None}
        return resultado

    def _proponer_base(self, look: Look) -> str | None:
        swf = next(iter(look.partes.values())).rpartition(".")[0]
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            return None
        try:
            prendas = self._prendas_de(swf, obtenido["data"])
        except (FFDecNoDisponible, OSError, subprocess.SubprocessError):
            return None
        candidatas = [c for c, p in prendas.items() if p.tipo == PRENDA]
        return f"{swf}.{min(candidatas, key=orden_natural)}" if candidatas else None

    def exportar_look(self, look: dict, ruta: str) -> dict:
        """Guarda el Look en un archivo de Look para pasárselo a otra persona."""
        try:
            Path(ruta).write_text(archivo_de_look(Look.desde(look)), encoding="utf-8")
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el archivo: {e.strerror or e}"}
        return {"ok": True, "ruta": ruta}

    def importar_look_de_archivo(self, ruta: str) -> dict:
        """Agrega a los Looks guardados el de un archivo de Look (con otro nombre si ya hay uno igual)."""
        try:
            contenido = Path(ruta).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo abrir el archivo: {e.strerror or e}"}
        try:
            look = look_de_archivo(contenido)
            almacen = self._almacen_looks()
            look.nombre = _nombre_libre(look.nombre, {l.nombre for l in almacen.todos()})
            guardado = almacen.guardar(look)
        except LookInvalido as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el Look: {e}"}
        return {"ok": True, "look": asdict(guardado)}

    def _almacen_looks(self) -> AlmacenLooks:
        return AlmacenLooks(self._entorno.carpeta_programa() / "looks.json")

    def _swf_trucados(self, encode: str) -> tuple[list[SwfTrucado], dict | None]:
        """Los SWF trucados que necesita un Encode generado en esta sesión, con el tamaño actual del original."""
        trucados = []
        for nombre, data in self._trucos.get(encode.strip(), {}).items():
            try:
                tamano = self._fuente.version(nombre).tamano
            except SwfNoEncontrado:
                return [], {"ok": False, "error": f"El SWF {nombre} no existe en el servidor del juego: solo se pueden trucar SWF del juego."}
            except OSError:
                return [], {"ok": False, "error": "Para usar una Prenda trucada hace falta conexión a internet (para saber el tamaño actual del SWF)."}
            trucados.append(SwfTrucado(nombre, data, tamano))
        return trucados, None

    def tiene_swf_trucado(self, encode: str) -> bool:
        """Si el Encode necesita un SWF trucado (se guarda en una carpeta, no en un solo archivo)."""
        return bool(self._trucos.get(encode.strip()))

    def exportar_truco(self, encode: str, carpeta: str) -> dict:
        """Guarda en `carpeta` el Encode, sus SWF trucados y cómo usarlos con Fiddler a mano."""
        try:
            decodificar(encode)
        except EncodeInvalido as e:
            return {"ok": False, "error": f"{e}."}
        trucados, error = self._swf_trucados(encode)
        if error:
            return error
        destino = Path(carpeta)
        reglas = [f"EXACT:{URL_LOLA}\n  → encode.txt"]
        try:
            destino.mkdir(parents=True, exist_ok=True)
            (destino / "encode.txt").write_text(encode.strip(), encoding="ascii")
            for trucado in trucados:
                archivo = trucado.nombre.replace("/", "_") + ".swf"
                (destino / archivo).write_bytes(trucado.data)
                reglas.append(f"EXACT:{URL_ASSETS}{trucado.nombre}.swf?{trucado.tamano_original}\n  → {archivo}")
            (destino / "LEEME.txt").write_text(_LEEME_TRUCO.format(reglas="\n\n".join(reglas)), encoding="utf-8")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar en la carpeta: {e.strerror or e}"}
        return {"ok": True, "ruta": str(destino)}

    def desactivar_reglas(self) -> dict:
        """Quita de Fiddler las reglas que puso el programa; las del jugador no se tocan."""
        entrega, error = self._preparar_entrega(necesita=("fiddler", "reglas"))
        if error:
            return error
        try:
            quitadas = entrega.desactivar()
        except PasoFallido as e:
            return self._resultado_fallido(entrega, e)
        return {"ok": True, "quitadas": quitadas, "pasos": [asdict(p) for p in entrega.pasos]}

    def _preparar_entrega(self, necesita=None) -> tuple[Entrega | None, dict | None]:
        componentes = self._entorno.componentes()
        faltan = [c for c in componentes if not c.ok and (necesita is None or c.id in necesita)]
        if faltan:
            return None, {
                "ok": False,
                "error": "Falta configurar: " + ", ".join(c.nombre for c in faltan) + ". Abrí Configuración para ver cómo.",
                "falta_configurar": True,
            }
        rutas = {c.id: Path(c.ruta) for c in componentes if c.ruta}
        try:
            carpeta_entregas = self._entorno.carpeta_programa() / "entregas"
        except OSError as e:
            return None, {"ok": False, "error": str(e)}
        return Entrega(
            juego=rutas.get("juego"),
            perfil=rutas.get("perfil"),
            fiddler=rutas["fiddler"],
            carpeta_reglas=rutas["reglas"],
            carpeta_entregas=carpeta_entregas,
            puerto_fiddler=self._entorno.puerto_fiddler(PUERTO_FIDDLER_POR_DEFECTO),
            procesos=self._procesos,
        ), None

    @staticmethod
    def _resultado_fallido(entrega: Entrega, e: PasoFallido) -> dict:
        fallido = entrega.pasos[-1].nombre
        return {
            "ok": False,
            "error": f"Falló el paso «{fallido}»: {e.detalle}",
            "que_hacer": e.que_hacer,
            "pasos": [asdict(p) for p in entrega.pasos],
        }

    def estado_entorno(self) -> dict:
        """Qué hay instalado y configurado para entregar Items al juego, con instrucciones para lo que falta."""
        componentes = self._entorno.componentes()
        return {
            "ok": True,
            "listo": all(c.ok for c in componentes),
            "componentes": [asdict(c) for c in componentes],
        }

    def corregir_ruta(self, id_componente: str, ruta: str) -> dict:
        """Usa una ruta elegida a mano para un componente; queda guardada para las próximas veces."""
        try:
            self._entorno.corregir_ruta(id_componente, ruta)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar la configuración: {e.strerror or e}"}
        return self.estado_entorno()

    def restablecer_ruta(self, id_componente: str) -> dict:
        """Vuelve a detectar automáticamente la ruta de un componente."""
        try:
            self._entorno.restablecer_ruta(id_componente)
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar la configuración: {e.strerror or e}"}
        return self.estado_entorno()

    def buscar_en_catalogo(self, texto: str) -> dict:
        """SWF de assets conocidos cuyo nombre contiene el texto, con cuántos Items tiene cada uno."""
        return {"ok": True, "swfs": buscar_en_catalogo(self._catalogo, texto)}

    def abrir_swf(self, ruta: str) -> dict:
        """Abre un SWF de assets de la computadora para buscar sus Items."""
        archivo = Path(ruta)
        try:
            data = archivo.read_bytes()
        except OSError as e:
            return {"ok": False, "error": f"No se pudo abrir el archivo: {e.strerror or e}"}
        # Un SWF guardado en su subcarpeta del CDN (antro2017/wears.swf) usa esa ruta en sus Items.
        conocidos = {s["swf"] for s in self._catalogo}
        con_carpeta = f"{archivo.parent.name}/{archivo.stem}"
        nombre = con_carpeta if con_carpeta in conocidos else archivo.stem
        return self._cargar_swf(nombre, data, archivo.name, {"tamano": len(data), "origen": "archivo"})

    def abrir_swf_del_cdn(self, nombre: str) -> dict:
        """Abre un SWF de assets del CDN del juego, descargándolo solo si cambió desde la última vez."""
        obtenido = self._obtener_del_cdn(nombre)
        if not obtenido["ok"]:
            return obtenido
        return self._cargar_swf(nombre, obtenido["data"], f"{nombre}.swf", obtenido["extra"])

    def _obtener_del_cdn(self, nombre: str) -> dict:
        """`{"ok", "data", "extra"}` de un SWF del CDN, usando la copia guardada si no cambió. No lo abre."""
        if not _NOMBRE_SWF.match(nombre):
            return {"ok": False, "error": f"Nombre de SWF inválido: {nombre}"}
        try:
            cache = CacheSwf(self._entorno.carpeta_cache() / "swf")
        except OSError as e:
            return {"ok": False, "error": str(e)}
        guardado = cache.leer(nombre)

        try:
            version = self._fuente.version(nombre)
        except SwfNoEncontrado:
            return {"ok": False, "error": f"El SWF {nombre} no existe en el servidor del juego."}
        except SinConexion:
            if guardado is None:
                return {"ok": False, "error": "No hay conexión a internet y este SWF todavía no se descargó."}
            data, version = guardado
            return {"ok": True, "data": data, "extra": {
                "tamano": version.tamano,
                "origen": "copia",
                "aviso": "Sin conexión: se usa la copia descargada antes, que puede no estar actualizada.",
            }}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo consultar el servidor del juego: {e}"}

        if guardado is not None and guardado[1] == version and len(guardado[0]) == version.tamano:
            return {"ok": True, "data": guardado[0], "extra": {"tamano": version.tamano, "origen": "copia"}}

        try:
            data = self._fuente.descargar(nombre)
        except SwfNoEncontrado:
            return {"ok": False, "error": f"El SWF {nombre} no existe en el servidor del juego."}
        except SinConexion:
            return {"ok": False, "error": "Se cortó la conexión mientras se descargaba el SWF. Probá de nuevo."}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo descargar el SWF: {e}"}
        try:
            leer_simbolos(data)
        except SwfInvalido as e:
            return {"ok": False, "error": f"{e}: {nombre}.swf"}
        try:
            cache.guardar(nombre, data, Version(len(data), version.etag))
        except OSError:
            pass  # sin copia local se vuelve a descargar la próxima vez
        return {"ok": True, "data": data, "extra": {"tamano": len(data), "origen": "descarga"}}

    def _cargar_swf(self, nombre: str, data: bytes, mostrado: str, extra: dict) -> dict:
        try:
            simbolos = leer_simbolos(data)
        except SwfInvalido as e:
            return {"ok": False, "error": f"{e}: {mostrado}"}
        clases = [clase for _, clase in simbolos]
        items = items_del_swf(clases)
        self._swf_abierto = nombre
        self._items_del_swf = items
        self._piezas_del_swf = piezas_del_swf(clases)
        self._simbolos_con_imagen = _simbolos_con_imagen(simbolos)
        self._data_swf = data
        self._tamano_swf = extra["tamano"]
        return {"ok": True, "swf": nombre, "cantidad_items": len(items), **extra}

    # --- Imágenes de los Items ---

    def preparar_iconos(self, swf: str | None = None) -> dict:
        """Exporta (una vez por versión) las imágenes de los Items y las Piezas de un SWF (por defecto, el abierto).

        Tarda unos segundos la primera vez.
        """
        if swf in (None, self._swf_abierto):
            if self._swf_abierto is None:
                return {"ok": False, "error": "Primero abrí un SWF."}
            swf, data, simbolos = self._swf_abierto, self._data_swf, dict(self._simbolos_con_imagen)
        else:
            obtenido = self._datos_de_otro_swf(swf)
            if not obtenido["ok"]:
                return obtenido
            data = obtenido["data"]
            simbolos = _simbolos_con_imagen(leer_simbolos(data))
        try:
            iconos = self._iconos()
            with self._candado_iconos:
                iconos.preparar(swf, data, simbolos)
        except FFDecNoDisponible as e:
            return {"ok": False, "sin_exportador": True, "error": f"{e}: no se pueden mostrar las imágenes de los Items."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron preparar las imágenes: {e}"}
        return {"ok": True, "swf": swf}

    def iconos(self, rutas_items: list[str]) -> dict:
        """Imagen (data URL PNG) de cada Item que la tenga exportada; None si no la tiene."""
        try:
            iconos = self._iconos()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "iconos": {ruta: iconos.icono(ruta) for ruta in rutas_items}}

    def sugerir_items(self, texto: str, limite: int = 50) -> dict:
        """Items del SWF abierto que empiezan con lo último que se escribió (después de la última coma), con su imagen."""
        if self._swf_abierto is None:
            return {"ok": True, "items": []}
        ultimo = texto.rsplit(",", 1)[-1].strip()
        if not ultimo:
            return {"ok": True, "items": []}
        rutas = [f"{self._swf_abierto}.{i}" for i in filtrar_por_prefijos(self._items_del_swf, [ultimo])]
        iconos = self.iconos(rutas[:limite]).get("iconos", {})
        return {
            "ok": True,
            "items": [{"ruta": ruta, "icono": iconos.get(ruta)} for ruta in rutas[:limite]],
            "total": len(rutas),
        }

    def gaturro(self, partes: dict, colores: dict | None = None) -> dict:
        """El Gaturro original del juego (SVG) con una Pieza de cualquier SWF en cada Parte del cuerpo de `partes`.

        `colores`: los del jugador (`color1` pelaje, `color2` panza, `color3` ojos, como "#RRGGBB");
        si faltan, los de fábrica del juego. El cuerpo y las Piezas de cada SWF se exportan una vez
        por versión (la primera vez tarda unos segundos). Las Piezas sin imagen se listan en
        `sin_imagen`, y las de Partes donde este Gaturro no tiene lugar, en `sin_lugar`. Si el Gaturro
        conseguido es una versión anterior a la del juego, `aviso` lo dice.
        """
        if not isinstance(partes, dict) or not isinstance(colores, (dict, type(None))):
            return {"ok": False, "error": "Las Partes del cuerpo no tienen la forma esperada."}
        try:
            cuerpo = self._cuerpo_gaturro()
        except FFDecNoDisponible as e:
            return {"ok": False, "sin_exportador": True, "error": f"{e}: no se puede dibujar al Gaturro."}
        if cuerpo is None:
            return {"ok": False, "sin_gaturro": True,
                    "error": "No se encontró el Gaturro original del juego, así que no se muestra ninguno."}

        con_lugar = {p for p in partes if tiene_lugar(cuerpo, p)}
        elegidas = {p: r for p, r in partes.items() if p in con_lugar and isinstance(r, str) and es_ruta_valida(r)}
        sin_lugar = [r for p, r in partes.items() if p not in con_lugar]
        sin_imagen = [r for p, r in partes.items() if p in con_lugar and r not in elegidas.values()]
        imagenes = ImagenesPiezas(self._entorno.carpeta_cache() / "piezas", self._exportador)
        for swf in sorted({r.rpartition(".")[0] for r in elegidas.values()}):
            try:
                self._preparar_svg(imagenes, swf, lambda clases: set(piezas_del_swf(clases)))
            except FFDecNoDisponible as e:
                return {"ok": False, "sin_exportador": True, "error": f"{e}: no se puede dibujar al Gaturro."}
        piezas = {}
        for parte, ruta in elegidas.items():
            swf, _, clase = ruta.rpartition(".")
            svg = imagenes.svg(swf, clase)
            if svg is None:
                sin_imagen.append(ruta)
            else:
                piezas[parte] = (clase, svg)
        return {"ok": True, "svg": componer(cuerpo, piezas, colores), "sin_imagen": sin_imagen, "sin_lugar": sin_lugar,
                "aviso": AVISO_VERSION_ANTERIOR if es_version_anterior(cuerpo) else None,
                "colores_de_fabrica": COLORES, "color_de_nariz": tiene_color_de_nariz(cuerpo)}

    def _cuerpo_gaturro(self) -> str | None:
        """El SVG de `assets.GaturroMC` del primer SWF del juego que lo traiga, con los huecos del torso
        de la plantilla de 2025 que le faltan (si se consigue)."""
        imagenes = ImagenesPiezas(self._entorno.carpeta_cache() / "gaturro", self._exportador)
        for swf in SWF_CUERPO:
            if self._preparar_svg(imagenes, swf, lambda clases: {CLASE_CUERPO} & set(clases)):
                cuerpo = imagenes.svg(swf, CLASE_CUERPO)
                if cuerpo:
                    break
        else:
            return None
        if self._preparar_svg(imagenes, SWF_PLANTILLA, lambda clases: {CLASE_PLANTILLA} & set(clases)):
            plantilla = imagenes.svg(SWF_PLANTILLA, CLASE_PLANTILLA)
            if plantilla:
                cuerpo = completar_con_plantilla(cuerpo, plantilla)
        return cuerpo

    def _preparar_svg(self, imagenes: ImagenesPiezas, swf: str, elegir) -> bool:
        """Exporta (una vez por versión) a SVG las clases de `swf` que `elegir(clases)` devuelve; False si no se pudo."""
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            return False
        try:
            simbolos = leer_simbolos(obtenido["data"])
            elegidas = elegir([clase for _, clase in simbolos])
            with self._candado_iconos:
                imagenes.preparar(swf, obtenido["data"], {i: c for i, c in simbolos if c in elegidas})
        except (OSError, SwfInvalido, subprocess.SubprocessError):
            return False
        return True

    def _iconos(self) -> IconosItems:
        return IconosItems(self._entorno.carpeta_cache() / "iconos", self._exportador)

    def buscar_items(self, texto_prefijos: str) -> dict:
        """Items del SWF abierto cuyo nombre empieza con alguno de los prefijos (separados por coma)."""
        if self._swf_abierto is None:
            return {"ok": False, "error": "Primero abrí un SWF."}
        prefijos = separar_prefijos(texto_prefijos)
        if not prefijos:
            return {"ok": False, "error": "Escribí al menos el comienzo de un nombre, por ejemplo: remera"}

        encontrados = filtrar_por_prefijos(self._items_del_swf, prefijos)
        return {"ok": True, "items": [f"{self._swf_abierto}.{i}" for i in encontrados]}

    def interpretar_items(self, texto: str) -> dict:
        """Rutas de Items escritas a mano (una por línea o separadas por coma), validadas."""
        rutas = separar_rutas(texto)
        if not rutas:
            return {"ok": False, "error": "Escribí al menos un Item, por ejemplo: clothes1.remera5"}

        invalidas = [r for r in rutas if not es_ruta_valida(r)]
        if invalidas:
            return {
                "ok": False,
                "error": "Estos Items no tienen el formato <swf>.<Clase>: " + ", ".join(invalidas),
                "invalidas": invalidas,
            }
        return {"ok": True, "items": rutas}

    def generar_encode(self, items: str | list[str | dict]) -> dict:
        """Encode que agrega los Items en su cantidad.

        `items` es texto como el de `interpretar_items` (cantidad 1 cada uno) o una
        lista donde cada elemento es una ruta (cantidad 1) o `{"ruta", "cantidad"}`.
        """
        if isinstance(items, str):
            interpretados = self.interpretar_items(items)
            if not interpretados["ok"]:
                return interpretados
            items = interpretados["items"]

        pedidos = [(i, 1) if isinstance(i, str) else (i.get("ruta", ""), i.get("cantidad", 1)) for i in items]
        if not pedidos:
            return {"ok": False, "error": "Agregá al menos un Item a la lista."}

        invalidas = [ruta for ruta, _ in pedidos if not es_ruta_valida(ruta)]
        if invalidas:
            return {
                "ok": False,
                "error": "Estos Items no tienen el formato <swf>.<Clase>: " + ", ".join(invalidas),
                "invalidas": invalidas,
            }
        cantidades_invalidas = [ruta for ruta, cantidad in pedidos if _cantidad(cantidad) is None]
        if cantidades_invalidas:
            return {
                "ok": False,
                "error": "La cantidad tiene que ser un número entero mayor que 0: " + ", ".join(cantidades_invalidas),
            }

        pedidos = [(ruta, _cantidad(cantidad)) for ruta, cantidad in pedidos]
        script = generar_script(pedidos)
        return {"ok": True, "items": _como_items(pedidos), "script": script, "encode": codificar(script)}

    def importar_encode(self, encode: str) -> dict:
        """Items y cantidades que agrega un Encode existente."""
        try:
            script = decodificar(encode)
        except EncodeInvalido as e:
            return {"ok": False, "error": f"{e}."}

        pedidos, otros_comandos = leer_script(script)
        validos = [(ruta, cantidad) for ruta, cantidad in pedidos if es_ruta_valida(ruta) and cantidad > 0]
        if not validos:
            return {"ok": False, "error": "Este Encode no agrega ningún Item."}
        return {
            "ok": True,
            "items": _como_items(validos),
            "ignorados": [ruta for ruta, cantidad in pedidos if (ruta, cantidad) not in validos],
            "otros_comandos": otros_comandos,
            "script": script,
        }

    def importar_encode_de_archivo(self, ruta: str) -> dict:
        try:
            contenido = Path(ruta).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo abrir el archivo: {e.strerror or e}"}
        return self.importar_encode(contenido)

    def guardar_encode(self, encode: str, ruta: str) -> dict:
        try:
            Path(ruta).write_text(encode, encoding="ascii")
        except OSError as e:
            return {"ok": False, "error": f"No se pudo guardar el archivo: {e.strerror or e}"}
        return {"ok": True, "ruta": ruta}


def _cantidad(valor) -> int | None:
    """La cantidad como entero mayor que 0, o None si no es válida (la interfaz puede mandar texto)."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str) and valor.strip().isdigit():
        valor = int(valor)
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return valor if isinstance(valor, int) and valor > 0 else None


def _nombre_libre(nombre: str, usados: set[str], sufijo: str = "") -> str:
    """`nombre`, o "nombre (2)", "nombre (3)"… (con `sufijo` dentro del paréntesis) si ya está usado."""
    if nombre not in usados:
        return nombre
    raiz = nombre.removesuffix(f" ({sufijo.strip()})") if sufijo else nombre
    n = 2
    while f"{raiz} ({sufijo}{n})" in usados:
        n += 1
    return f"{raiz} ({sufijo}{n})"


_LEEME_TRUCO = """Prenda trucada de MG Items, para usar con Fiddler a mano.

En Fiddler, pestaña AutoResponder: activá "Enable rules" y "Unmatched requests passthrough",
y agregá una regla por cada par: en el primer campo del "Rule Editor" va la línea EXACT:…
y en el segundo, la ruta completa del archivo de esta carpeta que se indica debajo.

{reglas}

Después cerrá el juego, borrá su caché (%APPDATA%\\MundoGaturro\\Cache), abrilo y tocá a Lola.
"""


def _como_items(pedidos: list[tuple[str, int]]) -> list[dict]:
    return [{"ruta": ruta, "cantidad": cantidad} for ruta, cantidad in pedidos]


def _simbolos_con_imagen(simbolos: list[tuple[int, str]]) -> dict[int, str]:
    """Los símbolos de Items y Piezas (los que tienen imagen para mostrar): id → clase."""
    clases = [clase for _, clase in simbolos]
    con_imagen = set(items_del_swf(clases)) | set(piezas_del_swf(clases))
    return {id_: clase for id_, clase in simbolos if clase in con_imagen}

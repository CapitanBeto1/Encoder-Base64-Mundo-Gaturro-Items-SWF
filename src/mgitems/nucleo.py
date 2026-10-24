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
from mgitems.entorno import Entorno, Sistema
from mgitems.entrega import PUERTO_FIDDLER_POR_DEFECTO, QUE_HACER_EN_EL_JUEGO, Entrega, PasoFallido, Procesos, SwfTrucado
from mgitems.ffdec import FFDecNoDisponible
from mgitems.fuente import FuenteCDN, SinConexion, SwfNoEncontrado, Version
from mgitems.iconos import ExportadorFFDec, IconosItems, version_de
from mgitems.items import (
    es_ruta_valida,
    filtrar_por_prefijos,
    items_del_swf,
    orden_natural,
    separar_prefijos,
    separar_rutas,
)
from mgitems.prendas import PARTES_DEL_CUERPO, CachePrendas, Prenda, PrendasFFDec, TruqueoFallido, reescribir_partes
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
        prendas_ffdec: PrendasFFDec | None = None,
    ):
        self._prendas_ffdec = prendas_ffdec or PrendasFFDec()
        self._prendas: dict[tuple[str, str], dict[str, Prenda]] = {}
        self._trucos: dict[str, dict[str, bytes]] = {}  # Encode → SWF trucados que necesita
        self._candado_ffdec = threading.Lock()
        self._swf_abierto: str | None = None
        self._items_del_swf: list[str] = []
        self._simbolos_items: dict[int, str] = {}
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
        trucados = []
        for nombre, data in self._trucos.get(encode.strip(), {}).items():
            try:
                tamano = self._fuente.version(nombre).tamano
            except SwfNoEncontrado:
                return {"ok": False, "error": f"El SWF {nombre} no existe en el servidor del juego: solo se pueden trucar SWF del juego."}
            except OSError:
                return {"ok": False, "error": "Para entregar una Prenda trucada hace falta conexión a internet (para saber el tamaño actual del SWF)."}
            trucados.append(SwfTrucado(nombre, data, tamano))
        try:
            entrega.entregar(encode, trucados)
        except PasoFallido as e:
            return self._resultado_fallido(entrega, e)
        return {"ok": True, "pasos": [asdict(p) for p in entrega.pasos], "que_hacer": QUE_HACER_EN_EL_JUEGO}

    # --- Prendas trucadas ---

    def prendas(self) -> dict:
        """Las Prendas del SWF abierto con la Pieza que muestra cada una en cada Parte del cuerpo.

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

        presentes = {parte for p in prendas.values() for parte in p.partes}
        partes = [{"id": i, "nombre": n} for i, n in PARTES_DEL_CUERPO.items()]
        partes += [{"id": i, "nombre": i} for i in sorted(presentes - set(PARTES_DEL_CUERPO))]
        return {
            "ok": True,
            "swf": self._swf_abierto,
            "prendas": [
                {"ruta": f"{self._swf_abierto}.{p.clase}", "clase": p.clase, "partes": p.partes}
                for p in sorted(prendas.values(), key=lambda p: orden_natural(p.clase))
            ],
            "partes_del_cuerpo": partes,
        }

    def trucar_prenda(self, base: str, partes: dict[str, str]) -> dict:
        """Genera la Prenda trucada: `base` (una Prenda del SWF abierto) mostrando `partes` (Parte del cuerpo → Pieza).

        Devuelve el Encode que la agrega; al entregarlo se entrega también el SWF trucado.
        """
        resultado = self.prendas()
        if not resultado["ok"]:
            return resultado
        swf, data = self._swf_abierto, self._data_swf
        prendas = self._prendas_del_swf_abierto()
        if base not in prendas:
            return {"ok": False, "error": f"{base} no es una Prenda de {swf}."}
        if not partes:
            return {"ok": False, "error": "Elegí al menos una Pieza para alguna Parte del cuerpo."}
        clases_del_swf = {clase for _, clase in leer_simbolos(data)}
        partes_validas = set(PARTES_DEL_CUERPO) | {p for prenda in prendas.values() for p in prenda.partes}
        invalidas = [f"{parte} → {pieza}" for parte, pieza in partes.items()
                     if parte not in partes_validas or pieza not in clases_del_swf]
        if invalidas:
            return {"ok": False, "error": f"Estas Piezas no existen en {swf}: " + ", ".join(invalidas)}

        try:
            fuente = reescribir_partes(prendas[base].fuente, partes)
            trucado = self._prendas_ffdec.trucar(data, base, fuente, dict(partes))
        except TruqueoFallido as e:
            return {"ok": False, "error": f"No se pudo trucar la Prenda: {e}."}
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se puede trucar."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudo trucar la Prenda: {e}"}

        ruta = f"{swf}.{base}"
        script = generar_script([(ruta, 1)])
        encode = codificar(script)
        self._trucos[encode] = {swf: trucado}
        return {
            "ok": True,
            "prenda": {"ruta": ruta, "partes": dict(partes)},
            "items": [{"ruta": ruta, "cantidad": 1}],
            "script": script,
            "encode": encode,
        }

    def _prendas_del_swf_abierto(self) -> dict[str, Prenda]:
        swf, data = self._swf_abierto, self._data_swf
        version = version_de(data)
        clave = (swf, version)
        if clave not in self._prendas:
            cache = CachePrendas(self._entorno.carpeta_cache() / "prendas")
            prendas = cache.leer(swf, version)
            if prendas is None:
                with self._candado_ffdec:
                    prendas = self._prendas_ffdec.analizar(data, self._items_del_swf)
                cache.guardar(swf, version, prendas)
            self._prendas[clave] = prendas
        return self._prendas[clave]

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
            return self._cargar_swf(nombre, data, f"{nombre}.swf", {
                "tamano": version.tamano,
                "origen": "copia",
                "aviso": "Sin conexión: se usa la copia descargada antes, que puede no estar actualizada.",
            })
        except OSError as e:
            return {"ok": False, "error": f"No se pudo consultar el servidor del juego: {e}"}

        if guardado is not None and guardado[1] == version and len(guardado[0]) == version.tamano:
            return self._cargar_swf(nombre, guardado[0], f"{nombre}.swf", {"tamano": version.tamano, "origen": "copia"})

        try:
            data = self._fuente.descargar(nombre)
        except SwfNoEncontrado:
            return {"ok": False, "error": f"El SWF {nombre} no existe en el servidor del juego."}
        except SinConexion:
            return {"ok": False, "error": "Se cortó la conexión mientras se descargaba el SWF. Probá de nuevo."}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo descargar el SWF: {e}"}
        version = Version(len(data), version.etag)
        resultado = self._cargar_swf(nombre, data, f"{nombre}.swf", {"tamano": version.tamano, "origen": "descarga"})
        if resultado["ok"]:
            try:
                cache.guardar(nombre, data, version)
            except OSError:
                pass  # sin copia local se vuelve a descargar la próxima vez
        return resultado

    def _cargar_swf(self, nombre: str, data: bytes, mostrado: str, extra: dict) -> dict:
        try:
            simbolos = leer_simbolos(data)
        except SwfInvalido as e:
            return {"ok": False, "error": f"{e}: {mostrado}"}
        items = items_del_swf([clase for _, clase in simbolos])
        es_item = set(items)
        self._swf_abierto = nombre
        self._items_del_swf = items
        self._simbolos_items = {id_: clase for id_, clase in simbolos if clase in es_item}
        self._data_swf = data
        self._tamano_swf = extra["tamano"]
        return {"ok": True, "swf": nombre, "cantidad_items": len(items), **extra}

    # --- Imágenes de los Items ---

    def preparar_iconos(self) -> dict:
        """Exporta (una vez por versión) las imágenes de los Items del SWF abierto. Puede tardar unos segundos."""
        if self._swf_abierto is None:
            return {"ok": False, "error": "Primero abrí un SWF."}
        swf, data, simbolos = self._swf_abierto, self._data_swf, dict(self._simbolos_items)
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


def _como_items(pedidos: list[tuple[str, int]]) -> list[dict]:
    return [{"ruta": ruta, "cantidad": cantidad} for ruta, cantidad in pedidos]

"""Los SWF del juego: abrirlos (del CDN o de un archivo), sus Items, Piezas y decoración, del índice o analizados."""

import re
import subprocess
from pathlib import Path

from mgitems.acciones import motivo_pieza_sin_accion
from mgitems.cache_swf import CacheSwf
from mgitems.catalogo import buscar_en_catalogo
from mgitems.categorias import (
    CASA, CacheCategorias, categorias, decoracion_en_acciones, donde_se_ven, es_decoracion, otros_usos, tipos_de_items,
    usos_de_piezas,
)
from mgitems.destinos import DESCARTADO, es_de_pasaporte, motivo_de
from mgitems.ffdec import FFDecNoDisponible
from mgitems.fuente import SinConexion, SwfNoEncontrado, Version
from mgitems.iconos import version_de
from mgitems.items import items_del_swf, orden_natural, piezas_del_swf
from mgitems.nucleo._comun import _simbolos_con_imagen
from mgitems.prendas import (
    EFECTO, PARTES_DEL_CUERPO, PREFIJO_EFECTO, PRENDA, CacheItemsBase, ItemBase, leer_item_base, no_sirve_de_base,
)
from mgitems.swf import SwfInvalido, leer_simbolos, limites_de_simbolos


_NOMBRE_SWF = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*$")


class Swfs:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

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
                 "partes": {parte: v for parte, v in p.partes.items()
                            if p.tipo == PRENDA or (parte in PARTES_DEL_CUERPO and (parte != EFECTO or v.startswith(PREFIJO_EFECTO)))}}
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
        """Los Items base (Prendas e Items de mochila) de cualquier SWF del juego: dónde se guarda un Look.
        Sin los que no sirven (ver `no_sirve_de_base`); si se sacó alguno, `aviso` dice por qué."""
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            return obtenido
        try:
            items = self._prendas_de(swf, obtenido["data"])
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden leer los Items base."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron leer los Items base: {e}"}
        sirven = [i for i in items.values() if not no_sirve_de_base(f"{swf}.{i.clase}", i.tipo)]
        motivos = {no_sirve_de_base(f"{swf}.{i.clase}", i.tipo) for i in items.values()} - {None}
        return {"ok": True, "swf": swf, "items": [
            {"ruta": f"{swf}.{i.clase}", "clase": i.clase, "tipo": i.tipo}
            for i in sorted(sirven, key=lambda i: orden_natural(i.clase))
        ], "aviso": f"Sus Prendas no sirven de Item base: {next(iter(motivos))}." if motivos else None}

    def piezas_de_swfs(self, swfs: list | None = None) -> dict:
        """Las Piezas de varios SWF (None: todos los del juego) con su SWF, las Partes del cuerpo donde
        el juego las usa ([] si ningún Item las viste: "Otros") y, si no visten, para qué las usa el
        juego (`uso`: "transporte", "accion", "casa", "mascota", o None si no se sabe) y si es de pasaporte
        (`pasaporte`: sin pasaporte, el juego no la dibuja).

        Usa el índice que trae el programa. Un SWF que no está en el índice, o cuya copia descargada es
        de otra versión, se analiza acá (la primera vez tarda unos segundos) y se recuerda.
        """
        def piezas(swf, obtenido):
            otros = obtenido["otros_usos"]
            return [{"ruta": f"{swf}.{clase}", "clase": clase, "swf": swf, "partes": partes,
                     "uso": None if partes else otros.get(clase), "pasaporte": es_de_pasaporte(f"{swf}.{clase}"),
                     "sin_accion": motivo_pieza_sin_accion(f"{swf}.{clase}", obtenido["se_ve"].get(clase, {})),
                     **obtenido["se_ve"].get(clase, {})}
                    for clase, partes in obtenido["piezas"].items()]

        return self._de_varios_swf(swfs, "piezas", piezas)

    def decoracion_de_swfs(self, swfs: list | None = None) -> dict:
        """Los objetos de la casa (muebles, decoración, y los dibujos de Flash, que llegan a la casa como un objeto)
        de varios SWF (None: todos los del juego), con la
        forma de las Piezas de `piezas_de_swfs` (`partes` vacías, `uso` "casa", `decoracion`): una acción
        los puede mostrar como a una Pieza (probado en el juego). `sin_accion`: por qué no lo mostraría."""
        def decoracion(swf, obtenido):
            return [{"ruta": f"{swf}.{clase}", "clase": clase, "swf": swf, "partes": [], "uso": CASA, "decoracion": True,
                     "pasaporte": item.get("pasaporte", False),
                     "sin_accion": motivo_pieza_sin_accion(f"{swf}.{clase}", obtenido["se_ve"].get(clase, {}))}
                    for clase, item in sorted(obtenido["items"].items(), key=lambda i: orden_natural(i[0]))
                    if es_decoracion(item) and item.get("destino") != DESCARTADO]

        return self._de_varios_swf(swfs, "decoracion", decoracion)

    def items_de_swfs(self, swfs: list | None = None) -> dict:
        """Los Items de varios SWF (None: todos los del juego) con su SWF, su tipo ("prenda", "mochila",
        "transporte", "casa", "mascota", "ropa_mascota", "comida_mascota", "juguete_mascota", "cuidado_mascota" u "otro"),
        las Partes del cuerpo que viste si es una Prenda, para qué mascota es (`mascota`, o None) y dónde
        llega al juego (`destino`, ver `destinos`; `motivo` si no llega bien, o None), si solo se la
        puede poner quien tiene pasaporte (`pasaporte`) y, si no sirve de Item base, por qué (`no_sirve_de_base`).

        Como `piezas_de_swfs`: del índice que trae el programa, o analizados acá si no están o cambiaron.
        """
        def items(swf, obtenido):
            return [{"ruta": f"{swf}.{clase}", "clase": clase, "swf": swf, "tipo": item["tipo"], "partes": item.get("partes", []),
                     "mascota": item.get("mascota"), "destino": item.get("destino"), "motivo": motivo_de(item),
                     "parecido": item.get("parecido", []), "pasaporte": item.get("pasaporte", False),
                     "dibujo": item.get("dibujo", False), "no_sirve_de_base": no_sirve_de_base(f"{swf}.{clase}", item["tipo"])}
                    for clase, item in sorted(obtenido["items"].items(), key=lambda i: orden_natural(i[0]))]

        return self._de_varios_swf(swfs, "items", items)

    def _de_varios_swf(self, swfs: list | None, clave: str, filas) -> dict:
        """`{"ok", clave: [...], "errores": {SWF: error}}` juntando `filas(swf, categorías del SWF)`."""
        if swfs is None:
            swfs = list(dict.fromkeys([*self._indice.swfs(), *(s["swf"] for s in self._catalogo)]))
        if not isinstance(swfs, list) or not all(isinstance(s, str) for s in swfs):
            return {"ok": False, "error": "Los SWF no tienen la forma esperada."}
        resultado, errores = [], {}
        for swf in dict.fromkeys(swfs):
            obtenido = self._categorias_de(swf)
            if not obtenido["ok"]:
                errores[swf] = obtenido["error"]
                continue
            resultado += filas(swf, obtenido)
        return {"ok": True, clave: resultado, "errores": errores}

    def _categorias_de(self, swf: str) -> dict:
        """`{"ok", "piezas": {Pieza: [Partes]}, "otros_usos": {Pieza: uso}, "items": {Item: {"tipo", "partes"}}}`
        de un SWF: del índice, o analizado acá si no está o cambió."""
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
            return {"ok": True, "piezas": del_indice["piezas"], "otros_usos": del_indice.get("otros_usos", {}),
                    "items": del_indice.get("items", {}), "se_ve": del_indice.get("se_ve", {})}
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
                return {"ok": True, **guardadas}
            clases = [clase for _, clase in leer_simbolos(data)]
            items = items_del_swf(clases)
            with self._candado_ffdec:
                fuentes = self._prendas_ffdec.fuentes(data, items + piezas_del_swf(clases))
            items_base = {i.clase: i for i in map(leer_item_base, fuentes.values()) if i and i.clase in items}
            piezas = categorias(piezas_del_swf(clases), usos_de_piezas(swf, items_base).get(swf, {}))
            otros = {p: uso for p, uso in otros_usos(swf, fuentes).get(swf, {}).items() if p in piezas and not piezas[p]}
            tipos = {clase: tipo for clase, tipo in tipos_de_items(swf, fuentes).items() if clase in items}
            limites = limites_de_simbolos(data)
            se_ve = donde_se_ven(swf, list(piezas), fuentes, limites) | decoracion_en_acciones(swf, tipos, limites)
            cache.guardar(swf, version, piezas, otros, tipos, se_ve)
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden clasificar los Items de {swf}."}
        except (OSError, SwfInvalido, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron clasificar los Items de {swf}: {e}"}
        return {"ok": True, "piezas": piezas, "otros_usos": otros, "items": tipos, "se_ve": se_ve}

    def _datos_de_otro_swf(self, swf: str) -> dict:
        """Un SWF del CDN que no es el abierto (se recuerda mientras dura el programa)."""
        if swf not in self._otros_swf:
            obtenido = self._obtener_del_cdn(swf)
            if not obtenido["ok"]:
                return obtenido
            self._otros_swf[swf] = obtenido["data"]
        return {"ok": True, "data": self._otros_swf[swf]}

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

    def _obtener_del_cdn(self, nombre: str, carpeta: str = "assets") -> dict:
        """`{"ok", "data", "extra"}` de un SWF del CDN (de su carpeta `carpeta`), usando la copia guardada si no
        cambió. No lo abre."""
        if not _NOMBRE_SWF.match(nombre):
            return {"ok": False, "error": f"Nombre de SWF inválido: {nombre}"}
        try:
            cache = CacheSwf(self._entorno.carpeta_cache() / ("swf" if carpeta == "assets" else carpeta))
        except OSError as e:
            return {"ok": False, "error": str(e)}
        guardado = cache.leer(nombre)

        try:
            version = self._fuente.version(nombre, carpeta)
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
            data = self._fuente.descargar(nombre, carpeta)
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

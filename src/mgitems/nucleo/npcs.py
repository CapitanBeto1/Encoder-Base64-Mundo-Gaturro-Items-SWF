"""Tiendas, Portales, Minijuegos y Fondos: cualquier Item como NPC de la casa (`mgitems.npcs`, `mgitems.fondos`)."""

import concurrent.futures
import re
import subprocess

from mgitems.destinos import DESCARTADO, motivo_de
from mgitems.ffdec import FFDecNoDisponible
from mgitems.fondos import SUFIJO_CUADRO, COMPORTAMIENTO as COMPORTAMIENTO_FONDO, CuadrosFFDec
from mgitems.fuente import SwfNoEncontrado
from mgitems.items import es_ruta_valida, orden_natural
from mgitems.npcs import (
    ComportamientosEncontrados, TIPOS as TIPOS_NPC, clasificar, comportamientos_en_cache, describir,
    es_comportamiento_valido, leer_npc,
)
from mgitems.nucleo._comun import _cantidad
from mgitems.prendas import no_sirve_de_base
from mgitems.script import codificar, generar_script_con_atributos


class Npcs:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def comportamientos(self, tipo: str) -> dict:
        """Los comportamientos de NPC conocidos de un tipo ("tienda", "portal", "minijuego"), por nombre: los que trae
        el programa y los encontrados en el caché del juego (`encontrado`)."""
        if tipo not in TIPOS_NPC:
            return {"ok": False, "error": f"Tipo de NPC desconocido: {tipo}"}
        conocidos = self._comportamientos.todos()
        filas = [self._fila_comportamiento(nombre, info) for nombre, info in conocidos.items() if info["tipo"] == tipo]
        filas += [self._fila_comportamiento(nombre, info) | {"encontrado": True} for nombre, info in self._encontrados().items()
                  if info["tipo"] == tipo and nombre not in conocidos]
        return {"ok": True, "comportamientos": sorted(filas, key=lambda f: orden_natural(f["comportamiento"]))}

    def buscar_comportamientos_en_el_juego(self) -> dict:
        """Busca en el caché del juego los comportamientos de los NPC de las salas por las que se pasó (y los anotados
        antes de una entrega), baja los que no se conocen y los guarda. `nuevos`: las tiendas, portales y minijuegos
        que no estaban."""
        try:
            almacen = self._almacen_encontrados()
            datos = almacen.leer()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        conocidos = set(self._comportamientos.todos()) | set(datos["comportamientos"])
        try:
            del_cache = self._comportamientos_del_cache()
        except OSError as e:
            return {"ok": False, "error": f"{e}: {e.__cause__ or 'está en uso'}."}
        por_bajar = sorted((del_cache | set(datos["pendientes"])) - conocidos, key=orden_natural)
        por_bajar = [n for n in por_bajar if es_comportamiento_valido(n)]

        def bajar(nombre):
            try:
                return nombre, clasificar(leer_npc(self._fuente.npc(nombre))) | {"objetos": []}
            except SwfNoEncontrado:
                return nombre, {"tipo": None, "catalogos": [], "salas": [], "juegos": [], "objetos": []}
            except OSError:
                return nombre, None  # sin conexión: queda pendiente

        with concurrent.futures.ThreadPoolExecutor(8) as hilos:
            bajados = dict(hilos.map(bajar, por_bajar))
        nuevos = {n: info for n, info in bajados.items() if info is not None}
        datos["comportamientos"] |= nuevos
        datos["pendientes"] = sorted(n for n, info in bajados.items() if info is None)
        try:
            almacen.guardar(datos)
        except OSError as e:
            return {"ok": False, "error": f"No se pudieron guardar los encontrados: {e}"}
        filas = [self._fila_comportamiento(n, info) | {"encontrado": True} for n, info in nuevos.items() if info["tipo"]]
        return {"ok": True, "nuevos": sorted(filas, key=lambda f: orden_natural(f["comportamiento"])),
                "sin_conexion": bool(datos["pendientes"])}

    def _comportamientos_del_cache(self) -> set[str]:
        perfil = self._entorno.ruta("perfil")
        return comportamientos_en_cache(perfil / "Cache") if perfil else set()

    def _anotar_comportamientos_del_cache(self) -> None:
        """Anota, sin bajarlos, los comportamientos del caché que no se conocen (se bajan al buscar)."""
        try:
            almacen = self._almacen_encontrados()
            datos = almacen.leer()
            conocidos = set(self._comportamientos.todos()) | set(datos["comportamientos"])
            nuevos = {n for n in self._comportamientos_del_cache() if es_comportamiento_valido(n)} - conocidos
            if nuevos - set(datos["pendientes"]):
                datos["pendientes"] = sorted(set(datos["pendientes"]) | nuevos, key=orden_natural)
                almacen.guardar(datos)
        except OSError:
            pass  # no impide entregar

    def _encontrados(self) -> dict[str, dict]:
        try:
            return self._almacen_encontrados().leer()["comportamientos"]
        except OSError:
            return {}

    def _almacen_encontrados(self) -> ComportamientosEncontrados:
        return ComportamientosEncontrados(self._entorno.carpeta_programa() / "comportamientos_encontrados.json")

    def comportamiento(self, nombre: str) -> dict:
        """Qué hace un comportamiento, también uno escrito a mano (se lee su guion del juego)."""
        if not es_comportamiento_valido(nombre):
            return {"ok": False, "error": f"«{nombre}» no es un nombre de comportamiento válido (letras, números, _ - y /)."}
        info = self._comportamientos.leer(nombre) or self._encontrados().get(nombre) or self._comportamientos_a_mano.get(nombre)
        if info is None:
            try:
                info = clasificar(leer_npc(self._fuente.npc(nombre))) | {"objetos": []}
            except SwfNoEncontrado:
                return {"ok": False, "error": f"El juego no tiene el comportamiento «{nombre}»."}
            except OSError:
                return {"ok": False, "error": "Para leer un comportamiento escrito a mano hace falta conexión a internet."}
            self._comportamientos_a_mano[nombre] = info
        return {"ok": True, "comportamiento": self._fila_comportamiento(nombre, info)}

    def _fila_comportamiento(self, nombre: str, info: dict) -> dict:
        return {"comportamiento": nombre, "tipo": info["tipo"], "descripcion": describir(info, self._comportamientos.salas),
                "objeto": info["objetos"][0] if info.get("objetos") else None}

    def convertir_en_npcs(self, pedidos: list) -> dict:
        """Varios Items convertidos en NPC en un solo Encode: cada uno (`{"base", "comportamiento", "cantidad"}`, y
        `cuadro` si es un fondo) es un Item ("swf.clase", de cualquier SWF) que llega a la casa y, al tocarlo, hace lo
        que su comportamiento. Un fondo es un NPC con `painting` que muestra su `cuadro` (atributo `frame`).

        No se truca ningún SWF: los atributos van en el Encode (`inventory.addOptions`, ADR 0007), así que el mismo
        Item puede ir varias veces, con otro comportamiento o con otro cuadro. Como el inventario junta los Items por
        nombre (`Inventory.itemsGrouped`), cada uno lleva lo suyo detrás de un segundo punto, que el juego ignora al
        cargarlo (`Libraries.getPackName`/`getItemName` toman `split(".")[0]` y `[1]`): un fondo, siempre su cuadro
        ("swf.clase.cuadro2"); un NPC, su comportamiento si el mismo Item va más de una vez ("swf.clase.brujaMesa")."""
        if not isinstance(pedidos, list) or not pedidos:
            return {"ok": False, "error": "Agregá al menos uno a la lista."}
        vistos, filas = set(), []
        for p in pedidos:
            if not (isinstance(p, dict) and isinstance(p.get("base"), str) and es_ruta_valida(p["base"])
                    and isinstance(p.get("comportamiento"), str)):
                return {"ok": False, "error": "La lista no tiene la forma esperada."}
            base, comportamiento, cuadro = p["base"], p["comportamiento"], p.get("cuadro")
            if cuadro is not None and (isinstance(cuadro, bool) or not isinstance(cuadro, int) or cuadro < 1):
                return {"ok": False, "error": f"El cuadro de {base} no es válido."}
            if (base, comportamiento, cuadro) in vistos:
                return {"ok": False, "error": f"{base} está dos veces igual: subí su cantidad."}
            vistos.add((base, comportamiento, cuadro))
            if (cantidad := _cantidad(p.get("cantidad", 1))) is None:
                return {"ok": False, "error": f"La cantidad de {base} tiene que ser un número entero mayor que 0."}
            descripto = self.comportamiento(comportamiento)
            if not descripto["ok"]:
                return descripto
            swf, _, clase = base.rpartition(".")
            obtenido = self._categorias_de(swf)
            if not obtenido["ok"]:
                return {"ok": False, "error": f"No se pudo usar {base}: {obtenido['error']}"}
            item = obtenido["items"].get(clase)
            if item is None:
                return {"ok": False, "error": f"{clase} no es un Item de {swf}."}
            if motivo := no_sirve_de_base(base, item["tipo"]):
                return {"ok": False, "error": f"{clase} no sirve de Item base: {motivo}."}
            if item.get("destino") == DESCARTADO:
                return {"ok": False, "error": f"{clase} no llega al juego: {motivo_de(item) or 'el juego lo descarta'}."}
            filas.append((base, comportamiento, cantidad, cuadro))

        repetidos = {b for b in (f[0] for f in filas) if sum(f[0] == b for f in filas) > 1}
        entregas = []
        for base, comportamiento, cantidad, cuadro in filas:
            atributos = {"behavior": comportamiento, "monitorAttributes": False} | ({"frame": cuadro} if cuadro else {})
            nombre = (f"{base}{SUFIJO_CUADRO}{cuadro}" if cuadro
                      else f"{base}.{_sufijo_de_nombre(comportamiento)}" if base in repetidos else base)
            entregas.append((nombre, cantidad, atributos))
        script = generar_script_con_atributos(entregas)
        return {"ok": True, "items": [{"ruta": nombre, "cantidad": cantidad} for nombre, cantidad, _ in entregas],
                "script": script, "encode": codificar(script)}

    def fondos(self) -> dict:
        """Los objetos que sirven de fondo (los que trae el programa), con cuántos cuadros tiene cada uno."""
        filas = [{"ruta": ruta, "clase": ruta.rpartition(".")[2], "swf": ruta.rpartition(".")[0], "cuadros": cuadros}
                 for ruta, cuadros in self._fondos.todos().items()]
        return {"ok": True, "fondos": sorted(filas, key=lambda f: orden_natural(f["clase"])), "comportamiento": COMPORTAMIENTO_FONDO}

    def cuadros_de_fondo(self, ruta: str) -> dict:
        """La vista previa de cada cuadro del dibujo de un Item ("swf.clase"), para elegir cuál se ve."""
        if not isinstance(ruta, str) or not es_ruta_valida(ruta):
            return {"ok": False, "error": "El Item no es válido."}
        swf, _, clase = ruta.rpartition(".")
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            return {"ok": False, "error": f"No se pudo leer {swf}: {obtenido['error']}"}
        cuadros = self._cuadros or CuadrosFFDec(self._entorno.carpeta_cache() / "cuadros")
        try:
            with self._candado_ffdec:
                imagenes = cuadros.cuadros(swf, clase, obtenido["data"])
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden mostrar los cuadros."}
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron mostrar los cuadros de {clase}: {e}"}
        return {"ok": True, "ruta": ruta, "cuadros": imagenes}


def _sufijo_de_nombre(texto: str) -> str:
    """Lo que va detrás del segundo punto del nombre de un Item para que el inventario no lo junte con otro: solo
    letras y números (el juego rechaza los nombres con «_so» u «_on», y los de «_catalog» van a otro lado)."""
    return re.sub(r"[^A-Za-z0-9]", "", texto) or "npc"

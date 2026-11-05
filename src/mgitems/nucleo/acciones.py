"""Acciones: un Item de mochila que hace una animación del juego mostrando una Pieza, y su vista previa."""

import subprocess
import tempfile
from pathlib import Path

from mgitems.acciones import (
    ANIMACIONES, NO_SE_DIBUJAN, animaciones, motivo_pieza_sin_accion, motivo_sin_accion, valor_de_accion,
)
from mgitems.animacion import CUADROS_POR_SEGUNDO, Linea, NoSeReproduce, alinear, espejar, simular_accion
from mgitems.categorias import CASA
from mgitems.ffdec import FFDecNoDisponible
from mgitems.gaturro import CLASE_CUERPO, OBJETOS, SWF_POSES, componer, preparar_cuerpo
from mgitems.iconos import version_de
from mgitems.items import es_ruta_valida, piezas_del_swf
from mgitems.mambo import atributo_en_codigo, clase_de_mochila
from mgitems.npcs import NoSePuedeConvertir
from mgitems.prendas import ACCION, EFECTO, MOCHILA, PREFIJO_EFECTO, TruqueoFallido, no_sirve_de_base
from mgitems.script import codificar, generar_script
from mgitems.swf import SwfInvalido, leer_simbolos


class Acciones:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def animaciones(self) -> dict:
        """Las animaciones que puede hacer un Item de mochila, en el orden en que se ofrecen (ver `acciones`):
        `id`, `nombre` en castellano, `grupo` ("accion", "no_se_dibuja" u "otras") y si la vista previa
        la puede dibujar (`se_dibuja`)."""
        return {"ok": True, "animaciones": animaciones()}

    def aplicar_accion(self, accion: dict) -> dict:
        """Truca el Item `accion["base"]` para que, al usarlo, el Gaturro haga la animación `accion["animacion"]`
        mostrando `accion["pieza"]` (opcional; cualquier Pieza, también un vehículo o un objeto de la casa) y, si se
        elige, ponga `accion["efecto"]` sobre la cabeza. Con usos ilimitados. Devuelve el Encode que lo agrega, y en
        `avisos` lo que el juego haría distinto de lo elegido.

        El Item puede ser cualquiera de cualquier SWF (menos las Prendas de `clothes1`): uno de mochila guarda la
        acción en `adds.action`; cualquier otro se convierte en uno de mochila (ADR 0007) y llega a la mochila."""
        if not isinstance(accion, dict):
            return {"ok": False, "error": "La acción no tiene la forma esperada."}
        animacion, base = accion.get("animacion"), accion.get("base")
        pieza, efecto = accion.get("pieza") or None, accion.get("efecto") or None
        if animacion not in ANIMACIONES:
            return {"ok": False, "error": "Elegí una animación."}
        if not isinstance(base, str) or not es_ruta_valida(base):
            return {"ok": False, "error": "Elegí el Item donde se guarda la acción."}
        if any(p is not None and not (isinstance(p, str) and es_ruta_valida(p)) for p in (pieza, efecto)):
            return {"ok": False, "error": "La Pieza no tiene la forma esperada."}

        swf, _, clase = base.rpartition(".")
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            return {"ok": False, "error": f"No se pudo usar el Item: {obtenido['error']}"}
        data = obtenido["data"]
        try:
            item = self._prendas_de(swf, data).get(clase)
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden leer los Items."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron leer los Items: {e}"}

        piezas_propias = set(piezas_del_swf([c for _, c in leer_simbolos(data)]))
        valores, avisos = {}, []
        objeto = None
        if pieza:
            objeto, error = (pieza, None) if self._es_decoracion(pieza) else self._valor_de_pieza(swf, piezas_propias, pieza, con_swf=True)
            if error:
                return {"ok": False, "error": error}
        valores[ACCION] = valor_de_accion(animacion, objeto)
        if motivo := motivo_sin_accion(valores[ACCION]):
            return {"ok": False, "error": f"El juego no haría esta acción: {motivo}."}
        if objeto and (motivo := self._motivo_pieza_sin_accion(objeto)):
            avisos.append({"ruta": objeto, "motivo": motivo})
        if efecto:
            valor, error = self._valor_de_pieza(swf, piezas_propias, efecto, con_swf=True)
            if error:
                return {"ok": False, "error": error}
            valores[EFECTO] = PREFIJO_EFECTO + valor
            if motivo := self._motivo_no_se_ve(valor, EFECTO):
                avisos.append({"ruta": valor, "motivo": motivo})

        if item is not None and item.tipo == MOCHILA:
            resultado = self._trucar_item(swf, data, item, valores)
        else:
            resultado = self._accion_en_cualquier_item(swf, data, clase, valores)
        if resultado["ok"]:
            resultado["avisos"] = avisos
        return resultado

    def _accion_en_cualquier_item(self, swf: str, data: bytes, clase: str, valores: dict[str, str]) -> dict:
        """Convierte `clase` (una Prenda, un objeto de la casa…) en un Item de mochila que hace la acción (ADR 0007)."""
        base = f"{swf}.{clase}"
        obtenido = self._categorias_de(swf)
        if not obtenido["ok"]:
            return {"ok": False, "error": f"No se pudo usar {base}: {obtenido['error']}"}
        item = obtenido["items"].get(clase)
        if item is None:
            return {"ok": False, "error": f"{clase} no es un Item de {swf}."}
        if motivo := no_sirve_de_base(base, item["tipo"]):
            return {"ok": False, "error": f"{clase} no sirve de Item base: {motivo}."}
        adds = {"action": valores[ACCION], **({"effect": valores[EFECTO]} if EFECTO in valores else {})}
        try:
            with self._candado_ffdec:
                fuente = self._prendas_ffdec.fuentes(data, [clase]).get(clase)
                if fuente is None:
                    raise NoSePuedeConvertir(f"no se encontró el código de {clase}")
                trucado = self._prendas_ffdec.reemplazar(data, {clase: clase_de_mochila(fuente, clase, adds)})
                verificado = self._prendas_ffdec.fuentes(trucado, [clase]).get(clase, "")
            if any(atributo_en_codigo(verificado, f"attr_{k}") != v for k, v in adds.items()):
                raise TruqueoFallido("el SWF trucado no quedó con la acción elegida")
        except (TruqueoFallido, NoSePuedeConvertir) as e:
            return {"ok": False, "error": f"No se pudo poner la acción en {clase}: {e}."}
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se puede trucar."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudo poner la acción en {clase}: {e}"}
        script = generar_script([(base, 1)])
        encode = codificar(script)
        self._trucos[encode] = {swf: trucado}
        return {"ok": True, "prenda": {"ruta": base, "tipo": MOCHILA, "partes": dict(valores)},
                "items": [{"ruta": base, "cantidad": 1}], "script": script, "encode": encode}

    def animacion_de_accion(self, accion: dict, colores: dict | None = None) -> dict:
        """La vista previa de la acción: el Gaturro haciendo la animación entera, cuadro por cuadro como en el
        juego (ver `animacion`), con la Pieza de la acción y la de la cabeza.

        `{"ok", "imagenes": [SVG], "secuencia": [índice de imagen por cuadro], "cuadros_por_segundo",
        "repite_desde": cuadro desde el que se repite sin fin (None: queda en el último), "avisos"}`; si no se
        puede mostrar igual que en el juego, sin imágenes y con `aviso`.
        """
        if not isinstance(accion, dict) or accion.get("animacion") not in ANIMACIONES:
            return {"ok": False, "error": "Elegí una animación."}
        animacion = accion["animacion"]
        if animacion in NO_SE_DIBUJAN:
            return {"ok": True, "imagenes": [], "secuencia": [], "avisos": [],
                    "aviso": "Esta animación no se puede mostrar: el Gaturro que se puede leer no la tiene."}
        avisos = []
        try:
            gaturro = self._linea(SWF_POSES, CLASE_CUERPO)
            objeto = efecto = None
            if pieza := accion.get("pieza"):
                if motivo := self._motivo_pieza_sin_accion(pieza):
                    avisos.append(f"{pieza.rpartition('.')[2]} no se ve: {motivo}.")
                else:
                    objeto = (self._linea(pieza.rpartition(".")[0], pieza.rpartition(".")[2]), pieza.rpartition(".")[2])
            if (cabeza := accion.get("efecto")) and es_ruta_valida(cabeza):
                if motivo := self._motivo_no_se_ve(cabeza, EFECTO):
                    avisos.append(f"{cabeza.rpartition('.')[2]} no se ve: {motivo}.")
                else:
                    efecto = (self._linea(cabeza.rpartition(".")[0], cabeza.rpartition(".")[2]), cabeza.rpartition(".")[2])
            reproducida = simular_accion(gaturro, CLASE_CUERPO, animacion, objeto, efecto)
            svgs = {}
            for linea, carpeta, claves in (
                (gaturro, SWF_POSES, {c.gaturro for c in reproducida.cuadros}),
                *([(objeto[0], accion["pieza"], {c.objeto for c in reproducida.cuadros if c.objeto})] if objeto else []),
                *([(efecto[0], accion["efecto"], {c.efecto for c in reproducida.cuadros if c.efecto})] if efecto else []),
            ):
                svgs.update(self._svgs_congelados(linea, carpeta, claves))
        except NoSeReproduce as e:
            return {"ok": True, "imagenes": [], "secuencia": [], "avisos": avisos,
                    "aviso": f"Esta animación no se puede mostrar igual que en el juego: {e}."}
        except FFDecNoDisponible as e:
            return {"ok": False, "sin_exportador": True, "error": f"{e}: no se puede mostrar la animación."}
        except (OSError, SwfInvalido, subprocess.SubprocessError, ValueError) as e:
            return {"ok": False, "error": f"No se pudo preparar la animación: {e}"}

        cuerpos = dict(zip(sorted({c.gaturro for c in reproducida.cuadros}),
                           alinear([svgs.get(k, "") for k in sorted({c.gaturro for c in reproducida.cuadros})])))
        imagenes, indices, secuencia = [], {}, []
        for cuadro in reproducida.cuadros:
            clave = (cuadro.gaturro, cuadro.efecto, cuadro.objeto)
            if clave not in indices:
                cuerpo = cuerpos.get(cuadro.gaturro)
                if not cuerpo:
                    return {"ok": True, "imagenes": [], "secuencia": [], "avisos": avisos,
                            "aviso": "Esta animación no se puede mostrar: FFDec no dibujó alguno de sus cuadros."}
                piezas = {}
                if cuadro.efecto and svgs.get(cuadro.efecto):
                    piezas[EFECTO] = (efecto[1], svgs[cuadro.efecto])
                if cuadro.objeto and svgs.get(cuadro.objeto):
                    piezas[OBJETOS] = (objeto[1], espejar(svgs[cuadro.objeto]) if reproducida.espejo else svgs[cuadro.objeto])
                cuerpo = preparar_cuerpo(cuerpo)
                indices[clave] = len(imagenes)
                imagenes.append(componer(cuerpo, piezas, colores))
            secuencia.append(indices[clave])
        return {"ok": True, "imagenes": imagenes, "secuencia": secuencia, "cuadros_por_segundo": CUADROS_POR_SEGUNDO,
                "repite_desde": reproducida.repite_desde, "avisos": avisos}

    def _linea(self, swf: str, clase: str) -> Linea:
        """Las líneas de tiempo de `swf`, con el código de los sprites que puede mostrar `clase`."""
        obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not obtenido["ok"]:
            raise NoSeReproduce(f"no se pudo descargar {swf}")
        data = obtenido["data"]
        clave = (swf, version_de(data))
        linea = self._lineas.get(clave)
        if linea is None:
            linea = self._lineas[clave] = Linea(data, {})
        faltan = linea.alcanzables(clase) - linea.con_codigo
        if faltan:
            with self._candado_ffdec:
                fuentes = self._prendas_ffdec.fuentes(data, sorted(faltan))
            linea.agregar_codigo(fuentes, faltan)
        return linea

    def _svgs_congelados(self, linea: Linea, swf: str, claves: set[str]) -> dict[str, str]:
        """Clave → SVG de los sprites congelados de `linea`, exportados con FFDec una vez y guardados."""
        carpeta = self._entorno.carpeta_cache() / "animaciones" / Path(*swf.replace(".", "/").split("/"))
        faltan = {linea.congelados[c][0]: c for c in claves if not (carpeta / f"{c}.svg").is_file()}
        if faltan:
            with tempfile.TemporaryDirectory(prefix="mgitems-", ignore_cleanup_errors=True) as temporal:
                archivo = Path(temporal) / "congelados.swf"
                archivo.write_bytes(linea.swf_con_congelados())
                with self._candado_ffdec:
                    self._exportador.exportar(archivo, faltan, carpeta, "svg")
        resultado = {}
        for c in claves:
            try:
                resultado[c] = (carpeta / f"{c}.svg").read_text(encoding="utf-8")
            except OSError:
                pass
        return resultado

    def _es_decoracion(self, ruta: str) -> bool:
        """Si `ruta` ("swf.clase") es un objeto de la casa, que una acción puede mostrar como una Pieza."""
        swf, _, clase = ruta.rpartition(".")
        obtenido = self._categorias_de(swf) if swf else {"ok": False}
        return obtenido["ok"] and obtenido["items"].get(clase, {}).get("tipo") == CASA

    def _motivo_pieza_sin_accion(self, ruta: str) -> str | None:
        swf, _, clase = ruta.rpartition(".")
        obtenido = self._categorias_de(swf)
        return motivo_pieza_sin_accion(ruta, obtenido.get("se_ve", {}).get(clase, {}) if obtenido["ok"] else {})

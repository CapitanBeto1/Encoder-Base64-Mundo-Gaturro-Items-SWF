"""Looks: aplicar un Look en su Item base, y los dibujos del juego para las ventanas que imitan las suyas."""

import subprocess
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDecNoDisponible
from mgitems.interfaz import BANNERS, CARPETA_BANNERS, DIBUJOS, recortar
from mgitems.items import orden_natural
from mgitems.looks import Look, LookInvalido
from mgitems.personalizar import (
    PersonalizacionInvalida, con_personalizacion, desde_valores, es_personalizable, es_valor_valido, normalizar, separar,
)
from mgitems.prendas import CAPAS, PARTES_CON_CAPAS, PARTES_DEL_CUERPO, PRENDA, capa, no_sirve_de_base, parte_de_la_capa


class Looks:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def dibujos_de_la_interfaz(self) -> dict:
        """Los dibujos del juego que usan las ventanas que imitan las suyas (ver `interfaz`): `{"ok", "dibujos":
        {nombre: SVG}}`. Falta el que no se pudo conseguir (sin conexión, sin FFDec, otra versión del banner)."""
        dibujos = {}
        for banner, tamano in BANNERS.items():
            obtenido = self._obtener_del_cdn(banner, CARPETA_BANNERS)
            if not obtenido["ok"] or len(obtenido["data"]) != tamano:
                continue
            carpeta = self._entorno.carpeta_cache() / "interfaz" / banner / str(tamano)
            # Cada forma se exporta una vez (de una misma salen varios recortes).
            formas = {forma: f"forma{forma}" for de, forma, _ in DIBUJOS.values() if de == banner}
            faltan = {forma: archivo for forma, archivo in formas.items() if not (carpeta / f"{archivo}.svg").is_file()}
            if faltan:
                try:
                    with tempfile.TemporaryDirectory(prefix="mgitems-", ignore_cleanup_errors=True) as temporal:
                        archivo = Path(temporal) / f"{banner}.swf"
                        archivo.write_bytes(obtenido["data"])
                        with self._candado_ffdec:
                            self._exportador.exportar_formas(archivo, faltan, carpeta)
                except (FFDecNoDisponible, OSError, subprocess.SubprocessError):
                    continue
            for nombre, (de, forma, recorte) in DIBUJOS.items():
                if de != banner:
                    continue
                try:
                    dibujos[nombre] = recortar((carpeta / f"{formas[forma]}.svg").read_text(encoding="utf-8"), recorte)
                except OSError:
                    pass
        return {"ok": True, "dibujos": dibujos}

    def para_el_editor(self, partes: dict, colores: dict | None = None, emote: str | None = None,
                       personalizacion: dict | None = None) -> dict:
        """Lo que necesita el editor de Piezas del juego (`ClothEditorModal`, en el Gaturro en vivo) para editar el
        Look: `piezas` (Parte → valor de su Pieza con la personalización, solo las que se pueden personalizar) y
        `atributos` (los del Gaturro, para su «Visualizar»)."""
        vivo = self.gaturro_en_vivo(partes, colores, emote, None, personalizacion)
        if not vivo["ok"]:
            return vivo
        atributos = vivo["atributos"]
        piezas = _personalizables(partes, atributos)
        if not piezas:
            return {"ok": False, "error": "El transporte y el efecto de cabeza no se personalizan: poné una Pieza en "
                                          "otra Parte."}
        return {"ok": True, "piezas": piezas, "atributos": atributos}

    def para_personalizar(self, partes: dict, colores: dict | None = None, emote: str | None = None,
                          personalizacion: dict | None = None, swfs: list | None = None) -> dict:
        """Lo que necesitan las ventanas del juego para personalizar el Look, que se eligen en su menú (ADR 0009):
        `atributos` (los del Gaturro), `piezas` (las que edita «Customiza tu ropa», como en `para_el_editor`; puede no
        haber ninguna) y `capas`: las Piezas de las fuentes `swfs` (None: todos los SWF) que «Configura tus accesorios»
        muestra en su grilla, cada una con la Parte de su pestaña (la primera de `PARTES_CON_CAPAS` donde el juego la
        usa, como `CustomLayerBanner.getItemCategory`)."""
        vivo = self.gaturro_en_vivo(partes, colores, emote, None, personalizacion)
        if not vivo["ok"]:
            return vivo
        disponibles = self.piezas_de_swfs(swfs)
        if not disponibles["ok"]:
            return disponibles
        capas = []
        for pieza in disponibles["piezas"]:
            usos = {parte_de_la_capa(p) for p in pieza["partes"]}
            if parte := next((p for p in PARTES_CON_CAPAS if p in usos), None):
                if "no_se_ve" not in pieza:
                    capas.append({"ruta": pieza["ruta"], "parte": parte})
        atributos = vivo["atributos"]
        return {"ok": True, "atributos": atributos, "piezas": _personalizables(partes, atributos), "capas": capas}

    def capas_configuradas(self, partes: dict, personalizacion: dict | None, valores: dict) -> dict:
        """El Look después de «Configura tus accesorios»: `valores` son las capas como las dejó la ventana del juego
        (Parte de cada capa → valor de su Pieza, o "" si quedó vacía). Devuelve las `partes` y la `personalizacion`
        nuevas: la personalización sigue a su Pieza aunque cambie de capa, porque la ventana mueve el valor entero."""
        if not isinstance(partes, dict) or not isinstance(valores, dict):
            return {"ok": False, "error": "Lo que devolvió «Configura tus accesorios» no tiene la forma esperada."}
        try:
            actual = normalizar(personalizacion, partes)
        except PersonalizacionInvalida as e:
            return {"ok": False, "error": str(e)}
        nuevas, nueva_personalizacion = dict(partes), dict(actual)
        for parte in (capa(p, n) for p in PARTES_CON_CAPAS for n in CAPAS):
            if parte not in valores:
                continue
            nuevas.pop(parte, None)
            nueva_personalizacion.pop(parte, None)
            valor = valores[parte]
            if not valor:
                continue
            if not isinstance(valor, str) or not es_valor_valido(valor):
                return {"ok": False, "error": f"«Configura tus accesorios» devolvió una Pieza que no tiene la forma esperada: {valor!r}"}
            ruta, colores, ajuste = separar(valor)
            nuevas[parte] = ruta
            nueva_personalizacion[parte] = {"colores": colores, "ajuste": ajuste}
        return {"ok": True, "partes": nuevas, "personalizacion": normalizar(nueva_personalizacion, nuevas)}

    def personalizacion_del_editor(self, partes: dict, valores: dict, editadas: list) -> dict:
        """La personalización del Look según lo que guardó el editor del juego: `valores` (Parte → valor de Pieza,
        las que quedaron) de las Partes `editadas` (las que el editor mostró). Las editadas que faltan en `valores`
        se cortaron con la tijera: van en `quitadas`, para sacarlas del Look, como hace el juego con la Prenda."""
        if not isinstance(partes, dict) or not isinstance(editadas, list):
            return {"ok": False, "error": "Lo que devolvió el editor no tiene la forma esperada."}
        try:
            personalizacion = normalizar(desde_valores(valores, partes), partes)
        except PersonalizacionInvalida as e:
            return {"ok": False, "error": str(e)}
        quitadas = [p for p in editadas if p in partes and p not in valores]
        return {"ok": True, "personalizacion": personalizacion, "quitadas": quitadas}

    def partes_del_cuerpo(self) -> dict:
        """Las Partes del cuerpo conocidas, con su nombre en español (no hace falta un SWF abierto) y, las capas de
        «Configura tus accesorios», la Parte de la que son capa (`capa_de`)."""
        return {"ok": True, "partes_del_cuerpo": [{"id": i, "nombre": n, **({"capa_de": b} if (b := parte_de_la_capa(i)) != i else {})}
                                                  for i, n in PARTES_DEL_CUERPO.items()]}

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
        # Cada Pieza va con sus colores por forma y su ajuste: el juego los lee del mismo texto (`personalizar`).
        partes = con_personalizacion(look.partes, look.personalizacion)
        resultado = self._trucar(swf, data, clase, partes, colores=look.colores or None, emote=look.emote or None)
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
        candidatas = [c for c, p in prendas.items() if p.tipo == PRENDA and not no_sirve_de_base(f"{swf}.{c}", p.tipo)]
        return f"{swf}.{min(candidatas, key=orden_natural)}" if candidatas else None


def _personalizables(partes: dict, atributos: dict) -> dict:
    """Las Piezas que edita «Customiza tu ropa»: Parte → valor de la Pieza con su personalización (de `atributos`)."""
    return {p: atributos[p] for p in partes if es_personalizable(p) and atributos.get(p)}

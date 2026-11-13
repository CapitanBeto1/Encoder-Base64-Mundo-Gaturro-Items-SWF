"""Looks: aplicar un Look en su Item base, y los dibujos del juego para las ventanas que imitan las suyas."""

import subprocess
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDecNoDisponible
from mgitems.interfaz import BANNERS, CARPETA_BANNERS, DIBUJOS, recortar
from mgitems.items import orden_natural
from mgitems.looks import Look, LookInvalido
from mgitems.personalizar import con_personalizacion, reglas
from mgitems.prendas import PARTES_DEL_CUERPO, PRENDA, no_sirve_de_base


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

    def reglas_de_personalizar(self) -> dict:
        """Qué Partes se pueden personalizar y ajustar, y los topes del ajuste (los del juego, ver `personalizar`)."""
        return {"ok": True, **reglas()}

    def partes_del_cuerpo(self) -> dict:
        """Las Partes del cuerpo conocidas, con su nombre en español (no hace falta un SWF abierto)."""
        return {"ok": True, "partes_del_cuerpo": [{"id": i, "nombre": n} for i, n in PARTES_DEL_CUERPO.items()]}

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

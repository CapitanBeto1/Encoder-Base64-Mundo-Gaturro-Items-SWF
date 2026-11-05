"""Agregar al juego con Fiddler: el entorno (juego, Fiddler), las reglas y los SWF trucados que necesita un Encode."""

from dataclasses import asdict
from pathlib import Path

from mgitems.entrega import (
    PUERTO_FIDDLER_POR_DEFECTO, QUE_HACER_EN_EL_JUEGO, URL_LOLA, Entrega, PasoFallido, SwfTrucado,
)
from mgitems.fuente import URL_ASSETS, SwfNoEncontrado
from mgitems.script import EncodeInvalido, decodificar


_LEEME_TRUCO = """Prenda trucada de MG Items, para usar con Fiddler a mano.

En Fiddler, pestaña AutoResponder: activá "Enable rules" y "Unmatched requests passthrough",
y agregá una regla por cada par: en el primer campo del "Rule Editor" va la línea EXACT:…
y en el segundo, la ruta completa del archivo de esta carpeta que se indica debajo.

{reglas}

Después cerrá el juego, borrá su caché (%APPDATA%\\MundoGaturro\\Cache), abrilo y tocá a Lola.
"""


class Entregar:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

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
        self._anotar_comportamientos_del_cache()  # la entrega borra el caché: que no se pierdan
        try:
            entrega.entregar(encode, trucados)
        except PasoFallido as e:
            return self._resultado_fallido(entrega, e)
        return {"ok": True, "pasos": [asdict(p) for p in entrega.pasos], "que_hacer": QUE_HACER_EN_EL_JUEGO}

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

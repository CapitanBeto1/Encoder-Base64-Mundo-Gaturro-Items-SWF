"""Buscar por imagen: qué Item es una captura del juego (`mgitems.busqueda`)."""

import base64

from mgitems.busqueda import FALTA_ONNXRUNTIME, QUE_ES, DatosBusqueda, abrir_encuadres, espejada, guiar, hay_onnxruntime
from mgitems.destinos import DESCARTADO, es_de_pasaporte, motivo_de
from mgitems.items import es_ruta_valida


class Busqueda:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    RESULTADOS_BUSQUEDA = 20

    def estado_busqueda(self) -> dict:
        """Si ya están los datos de la búsqueda (el modelo y las huellas) y cuánto pesa bajarlos (en bytes). Sin
        onnxruntime no se puede buscar: se avisa antes de bajar nada."""
        if not hay_onnxruntime():
            return {"ok": False, "sin_onnxruntime": True, "error": FALTA_ONNXRUNTIME}
        try:
            datos = self._datos()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "listos": datos.listos(), "tamano": DatosBusqueda.TAMANO}

    def preparar_busqueda(self) -> dict:
        """Baja los datos de la búsqueda la primera vez (unos 107 MB). `progreso_busqueda` dice cuánto va."""
        try:
            datos = self._datos()
            if datos.listos():
                return {"ok": True}
            self._progreso_busqueda = {"bajando": True, "hechos": 0, "total": DatosBusqueda.TAMANO}

            def progreso(hechos, total):
                self._progreso_busqueda = {"bajando": True, "hechos": hechos, "total": total}

            datos.bajar(progreso)
        except ValueError as e:
            return {"ok": False, "error": f"No se pudieron bajar los datos de la búsqueda: {e}. Probá de nuevo."}
        except OSError as e:
            return {"ok": False, "error": f"No se pudieron bajar los datos de la búsqueda (hace falta internet): {e}"}
        finally:
            self._progreso_busqueda = {**self._progreso_busqueda, "bajando": False}
        return {"ok": True}

    def progreso_busqueda(self) -> dict:
        return {"ok": True, **self._progreso_busqueda}

    def opciones_que_es(self) -> dict:
        """Las opciones de «¿Qué es?» de la búsqueda por imagen, en orden."""
        return {"ok": True, "opciones": [{"id": i, "nombre": nombre} for i, (nombre, _) in QUE_ES.items()]}

    def buscar_por_imagen(self, imagen: str, recorte: list | None = None, que: str | None = None,
                          se_parece: list | None = None, descartados: list | None = None) -> dict:
        """Los Items que más se parecen a una captura (`imagen`: data URL o base64 de un PNG/JPG; `recorte`:
        [x0, y0, x1, y1] del rectángulo marcado, o None). Cada uno con su ruta, SWF, tipo, adónde llega, el
        parecido (de -1 a 1) y la Pieza por la que se encontró si lo parecido era lo que se ve puesto (`por_pieza`).
        Si esa Pieza es solo una parte del Item (está «cortado»: el pantalón de un traje), `cortado` dice cuál.

        Para buscar de nuevo, mejor: `que` (una de `opciones_que_es`) limita a ese tipo de Item; `se_parece` (rutas
        de resultados) acerca la búsqueda a ellos y `descartados` (rutas) la aleja de ellos y los saca."""
        try:
            data = base64.b64decode(imagen.split(",", 1)[-1], validate=False)
            encuadres = abrir_encuadres(data, tuple(recorte) if recorte else None)
        except (ValueError, TypeError, AttributeError) as e:
            return {"ok": False, "error": f"No se pudo leer la imagen: {e}."}
        if que is not None and que not in QUE_ES:
            return {"ok": False, "error": f"No se puede buscar «{que}»."}
        se_parece, descartados = set(se_parece or []), set(descartados or [])
        if not all(isinstance(r, str) and es_ruta_valida(r) for r in se_parece | descartados):
            return {"ok": False, "error": "Los resultados marcados no tienen la forma esperada."}
        try:
            datos = self._datos()
            if not datos.listos():
                return {"ok": False, "faltan_datos": True, "error": "Primero hay que bajar los datos de la búsqueda."}
            modelo, huellas = datos.cargar()
            consultas = guiar(modelo.huellas(encuadres + [espejada(e) for e in encuadres]), huellas.de_items(se_parece),
                              huellas.de_items(descartados))
            parecidos = huellas.parecidos(consultas)
        except (OSError, ValueError, RuntimeError) as e:
            return {"ok": False, "error": f"No se pudo buscar: {e}"}

        limite = QUE_ES[que][1] if que else {}
        filas, vistos = [], set(descartados)
        for ruta, parecido in parecidos:
            por_pieza = ruta if ruta in huellas.prendas_de_pieza else None
            for item in huellas.prendas_de_pieza.get(ruta, [ruta]):
                if item in vistos:
                    continue
                fila = self._fila_de_busqueda(item, parecido, por_pieza)
                if fila is None or self._es_lo_que_busca(fila, limite):
                    vistos.add(item)
                    if fila:
                        filas.append(fila)
                # Si no es lo que se busca (el ícono de un traje, buscando un pantalón), puede serlo más abajo por
                # una de sus Piezas (su pantalón, cortado).
            if len(filas) >= self.RESULTADOS_BUSQUEDA:
                break
        return {"ok": True, "resultados": filas[: self.RESULTADOS_BUSQUEDA]}

    @staticmethod
    def _es_lo_que_busca(fila: dict, limite: dict) -> bool:
        partes = set(fila["partes"])
        if "partes" in limite:
            cortado = fila["cortado"]
            return (bool(partes) and partes <= limite["partes"]) or bool(cortado and set(cortado["partes"]) & limite["partes"])
        if limite.get("disfraz"):
            return len(partes) >= 3
        if "tipos" in limite:
            return fila["tipo"] in limite["tipos"]
        if "destinos" in limite:
            return fila["destino"] in limite["destinos"]
        return True

    def _fila_de_busqueda(self, ruta: str, parecido: float, por_pieza: str | None) -> dict | None:
        """Un resultado de la búsqueda, si `ruta` es un Item que llega al juego, o una Pieza que se viste pero que
        ningún Item trae (`suelta`: se ve puesta en otros Gaturros, armada con Trucar Prenda o con Looks)."""
        swf, _, clase = ruta.rpartition(".")
        obtenido = self._indice.leer(swf)
        item = (obtenido or {}).get("items", {}).get(clase)
        if item is None:
            partes = (obtenido or {}).get("piezas", {}).get(clase) or []
            if not partes:
                return None
            return {"ruta": ruta, "clase": clase, "swf": swf, "tipo": "pieza", "partes": partes, "mascota": None,
                    "destino": None, "motivo": None, "pasaporte": es_de_pasaporte(ruta), "parecido": round(parecido, 4),
                    "por_pieza": ruta, "cortado": {"pieza": ruta, "partes": partes}, "suelta": True}
        if item.get("destino") == DESCARTADO:
            return None
        return {"ruta": ruta, "clase": clase, "swf": swf, "tipo": item["tipo"], "partes": item.get("partes", []),
                "mascota": item.get("mascota"), "destino": item.get("destino"), "motivo": motivo_de(item),
                "pasaporte": es_de_pasaporte(ruta), "parecido": round(parecido, 4), "por_pieza": por_pieza,
                "cortado": self._cortado(item, por_pieza)}

    def _cortado(self, item: dict, por_pieza: str | None) -> dict | None:
        """Si lo que se parece es una sola Pieza de un Item que tiene más (el pantalón de un traje, las mangas de una
        remera): `{"pieza", "partes"}` de esa Pieza; si no, None."""
        if not por_pieza:
            return None
        swf, _, clase = por_pieza.rpartition(".")
        partes = (self._indice.leer(swf) or {}).get("piezas", {}).get(clase) or []
        return {"pieza": por_pieza, "partes": partes} if partes and set(item.get("partes", [])) - set(partes) else None

    def _datos(self) -> DatosBusqueda:
        if self._datos_busqueda is None:
            self._datos_busqueda = DatosBusqueda(self._entorno.carpeta_programa() / "busqueda")
        return self._datos_busqueda

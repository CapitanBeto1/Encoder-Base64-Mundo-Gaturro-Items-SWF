"""Trucar Prenda: un Item base que muestra otras Piezas, con su SWF trucado."""

import subprocess

from mgitems.ffdec import FFDecNoDisponible
from mgitems.items import es_ruta_valida, piezas_del_swf
from mgitems.prendas import (
    EFECTO, MOCHILA, PREFIJO_EFECTO, ItemBase, TruqueoFallido, no_sirve_de_base, reescribir_partes,
)
from mgitems.script import codificar, generar_script, generar_script_con_atributos
from mgitems.swf import leer_simbolos


class Trucar:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

    def trucar_varias(self, trucadas: list, colores: dict | None = None) -> dict:
        """Varias Prendas trucadas en un solo Encode: cada una (`{"base", "parte", "pieza"}`) es un Item base
        ("swf.clase", de cualquier SWF) que muestra solo `pieza` (de cualquier SWF) en `parte`. Cada Item base va
        una sola vez (si no, sería el mismo Item con dos cosas). Las de un mismo SWF van en el mismo SWF trucado.
        Si se pasan `colores` ({"color1": "#RRGGBB", …}), se incluyen en el Encode como `user.attr`."""
        if not isinstance(trucadas, list) or not trucadas:
            return {"ok": False, "error": "Agregá al menos una Prenda trucada a la lista."}
        vistas = set()
        for t in trucadas:
            if not isinstance(t, dict) or not all(isinstance(t.get(k), str) for k in ("base", "parte", "pieza")) \
                    or not es_ruta_valida(t["base"]) or not es_ruta_valida(t["pieza"]):
                return {"ok": False, "error": "Las Prendas trucadas no tienen la forma esperada."}
            if t["base"] in vistas:
                return {"ok": False, "error": f"{t['base']} está dos veces: cada Prenda trucada necesita otro Item base."}
            vistas.add(t["base"])

        trucados, resumen = {}, []
        for t in trucadas:
            swf, _, clase = t["base"].rpartition(".")
            obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
            if not obtenido["ok"]:
                return {"ok": False, "error": f"No se pudo usar {t['base']}: {obtenido['error']}"}
            data = obtenido["data"]
            try:
                item = self._prendas_de(swf, data).get(clase)
            except FFDecNoDisponible as e:
                return {"ok": False, "error": f"{e}: no se pueden leer las Prendas."}
            except (OSError, subprocess.SubprocessError) as e:
                return {"ok": False, "error": f"No se pudieron leer las Prendas: {e}"}
            if item is None:
                return {"ok": False, "error": f"{clase} no es una Prenda ni un Item de mochila de {swf}."}
            if motivo := no_sirve_de_base(t["base"], item.tipo):
                return {"ok": False, "error": f"{clase} no sirve de Item base: {motivo}."}
            valores, error = self._valores_de_piezas(swf, data, item, {t["parte"]: t["pieza"]})
            if error:
                return {"ok": False, "error": error}
            try:
                # Sobre lo ya trucado de ese SWF: así quedan todas las suyas.
                trucados[swf] = self._trucado(trucados.get(swf, data), item, valores, colores=colores or None)
            except TruqueoFallido as e:
                return {"ok": False, "error": f"No se pudo trucar {t['base']}: {e}."}
            except FFDecNoDisponible as e:
                return {"ok": False, "error": f"{e}: no se puede trucar."}
            except (OSError, subprocess.SubprocessError, ValueError) as e:
                return {"ok": False, "error": f"No se pudo trucar {t['base']}: {e}"}
            resumen.append({"ruta": t["base"], "tipo": item.tipo, "partes": dict(valores)})

        rutas = [t["base"] for t in trucadas]
        script = generar_script([(ruta, 1) for ruta in rutas])
        encode = codificar(script)
        self._trucos[encode] = trucados
        return {"ok": True, "trucadas": resumen, "items": [{"ruta": r, "cantidad": 1} for r in rutas],
                "script": script, "encode": encode}

    def trucar_varias_via_encode(self, trucadas: list, colores: dict | None = None) -> dict:
        """Como `trucar_varias` pero via `inventory.addOptions`: el Encode guarda los `wear_*` en el servidor,
        por lo que la Prenda persiste después del relog aunque Fiddler esté apagado. No truca el SWF.
        Si se pasan `colores`, se incluyen en el Encode como `user.attr`."""
        if not isinstance(trucadas, list) or not trucadas:
            return {"ok": False, "error": "Agregá al menos una Prenda trucada a la lista."}
        for t in trucadas:
            if not isinstance(t, dict) or not all(isinstance(t.get(k), str) for k in ("base", "parte", "pieza")) \
                    or not es_ruta_valida(t["base"]) or not es_ruta_valida(t["pieza"]):
                return {"ok": False, "error": "Las Prendas trucadas no tienen la forma esperada."}

        pedidos, resumen = [], []
        for t in trucadas:
            swf, _, clase = t["base"].rpartition(".")
            obtenido = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
            if not obtenido["ok"]:
                return {"ok": False, "error": f"No se pudo usar {t['base']}: {obtenido['error']}"}
            data = obtenido["data"]
            try:
                prendas = self._prendas_de(swf, data)
            except FFDecNoDisponible as e:
                return {"ok": False, "error": f"{e}: no se pueden leer las Prendas."}
            except (OSError, subprocess.SubprocessError) as e:
                return {"ok": False, "error": f"No se pudieron leer las Prendas: {e}"}
            item = prendas.get(clase)
            if item is None:
                return {"ok": False, "error": f"{clase} no es una Prenda ni un Item de mochila de {swf}."}
            if motivo := no_sirve_de_base(t["base"], item.tipo):
                return {"ok": False, "error": f"{clase} no sirve de Item base: {motivo}."}
            piezas_propias = set(piezas_del_swf([cls for _, cls in leer_simbolos(data)]))
            valor, error = self._valor_de_pieza(swf, piezas_propias, t["pieza"], con_swf=True)
            if error:
                return {"ok": False, "error": error}
            pedidos.append((t["base"], 1, {f"wear_{t['parte']}": valor}))
            resumen.append({"ruta": t["base"], "tipo": item.tipo, "partes": {t["parte"]: valor}})

        if colores:
            # Para via-encode, los colores van en los attrs de cada item (como en food.swf: adds.colorN = int).
            int_colores = {c: int(v.lstrip("#"), 16) for c, v in colores.items()}
            pedidos = [(ruta, qty, {**attrs, **int_colores}) for ruta, qty, attrs in pedidos]
        script = generar_script_con_atributos(pedidos)
        encode = codificar(script)
        return {"ok": True, "trucadas": resumen, "items": [{"ruta": t["base"], "cantidad": 1} for t in trucadas],
                "script": script, "encode": encode}

    def trucar_prenda(self, base: str, parte: str, pieza: str, colores: dict | None = None) -> dict:
        """Genera la Prenda trucada: `base` (un Item base del SWF abierto) mostrando solo `pieza` en `parte`.

        `pieza` es una Pieza del SWF abierto o de otro (`costumes.coronaRey_on`).
        Devuelve el Encode que la agrega; al entregarlo se entrega también el SWF trucado.
        Si se pasan `colores`, se incluyen en el Encode como `user.attr`.
        """
        resultado = self.prendas()
        if not resultado["ok"]:
            return resultado
        partes_validas = {p["id"] for p in resultado["partes_del_cuerpo"]}
        if parte not in partes_validas:
            return {"ok": False, "error": f"{parte} no es una Parte del cuerpo."}
        return self._trucar(self._swf_abierto, self._data_swf, base, {parte: pieza}, colores=colores)

    def _trucar(self, swf: str, data: bytes, base: str, partes: dict[str, str], colores: dict | None = None) -> dict:
        """Truca el Item base `base` del SWF `swf` para que muestre `partes` (Parte del cuerpo → Pieza de cualquier SWF)."""
        try:
            prendas = self._prendas_de(swf, data)
        except FFDecNoDisponible as e:
            return {"ok": False, "error": f"{e}: no se pueden leer las Prendas."}
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": f"No se pudieron leer las Prendas: {e}"}
        if base not in prendas:
            return {"ok": False, "error": f"{base} no es una Prenda ni un Item de mochila de {swf}."}
        if motivo := no_sirve_de_base(f"{swf}.{base}", prendas[base].tipo):
            return {"ok": False, "error": f"{base} no sirve de Item base: {motivo}."}
        if not partes:
            return {"ok": False, "error": "Elegí al menos una Pieza."}

        item = prendas[base]
        valores, error = self._valores_de_piezas(swf, data, item, partes)
        if error:
            return {"ok": False, "error": error}
        return self._trucar_item(swf, data, item, valores, colores=colores)

    def _valores_de_piezas(self, swf: str, data: bytes, item: ItemBase, partes: dict[str, str]) -> tuple[dict, str | None]:
        """(Parte → cómo se escribe su Pieza en `item` del SWF `swf`, error)."""
        piezas_propias = set(piezas_del_swf([clase for _, clase in leer_simbolos(data)]))
        valores = {}
        for parte, pieza in partes.items():
            # El efecto de cabeza lleva siempre el SWF de la Pieza: el juego la busca tal cual.
            valor, error = self._valor_de_pieza(swf, piezas_propias, pieza, con_swf=item.tipo == MOCHILA or parte == EFECTO)
            if error:
                return {}, error
            valores[parte] = PREFIJO_EFECTO + valor if parte == EFECTO else valor
        return valores, None

    def _trucado(self, data: bytes, item: ItemBase, valores: dict[str, str], colores: dict | None = None) -> bytes:
        """El SWF `data` con `item` mostrando `valores` (puede lanzar TruqueoFallido, FFDecNoDisponible, OSError…).
        Si se pasan `colores`, se inyectan como `adds.colorN = <int>` en el AS3 del item."""
        return self._prendas_ffdec.trucar(data, item.clase, reescribir_partes(item, valores, colores), dict(valores))

    def _trucar_item(self, swf: str, data: bytes, item: ItemBase, valores: dict[str, str],
                     colores: dict | None = None) -> dict:
        """Truca `item` del SWF `swf` con `valores` (Parte → cómo se escribe) y arma el Encode que lo agrega."""
        base = item.clase
        try:
            trucado = self._trucado(data, item, valores, colores=colores or None)
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

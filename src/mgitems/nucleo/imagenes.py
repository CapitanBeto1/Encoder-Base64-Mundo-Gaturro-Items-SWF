"""Las imágenes: los íconos de los Items y el Gaturro dibujado con Piezas, como en el juego."""

import subprocess

from mgitems.ffdec import FFDecNoDisponible
from mgitems.gaturro import (
    CLASE_CUERPO, CLASE_PLANTILLA, COLORES, CUADRO_QUIETO_DEL_VEHICULO, SWF_CUERPO,
    SWF_PLANTILLA, SWF_POSES, ImagenesPiezas, completar_con_plantilla, componer,
    pose_de_transporte, preparar_cuerpo, tiene_color_de_nariz, tiene_lugar,
)
from mgitems.iconos import IconosItems
from mgitems.items import es_ruta_valida, filtrar_por_prefijos, piezas_del_swf
from mgitems.nucleo._comun import _simbolos_con_imagen
from mgitems.prendas import EFECTO, PARTES_DEL_CUERPO
from mgitems.se_ve import TRANSPORTE, motivo_sin_efecto
from mgitems.swf import SwfInvalido, congelado_en, leer_simbolos, rotulos


class Imagenes:
    """Una parte de `Nucleo`: usa el estado que arma `Nucleo.__init__`."""

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
        `sin_imagen`, y las de Partes donde este Gaturro no tiene lugar, en `sin_lugar`. Las que el juego
        no dibujaría en esa Parte (ver `se_ve`) no se dibujan y van en `no_se_ven` ({ruta, parte, motivo}),
        igual que el transporte, que la vista previa todavía no dibuja (`transporte`). Si el Gaturro
        conseguido es una versión anterior a la del juego, `aviso` lo dice.
        """
        if not isinstance(partes, dict) or not isinstance(colores, (dict, type(None))):
            return {"ok": False, "error": "Las Partes del cuerpo no tienen la forma esperada."}
        no_se_ven = [{"ruta": r, "parte": p, "motivo": m} for p, r in partes.items()
                     if isinstance(r, str) and es_ruta_valida(r) and (m := self._motivo_no_se_ve(r, p))]
        transporte = partes.get(TRANSPORTE) if isinstance(partes.get(TRANSPORTE), str) and es_ruta_valida(partes[TRANSPORTE]) else None
        if any(n["parte"] == TRANSPORTE for n in no_se_ven):
            transporte = None
        try:
            vehiculo, cuerpo, sin_pose = None, None, None
            if transporte:
                vehiculo, cuerpo, sin_pose = self._gaturro_en_vehiculo(transporte)
            cuerpo = cuerpo or self._cuerpo_gaturro()
        except FFDecNoDisponible as e:
            return {"ok": False, "sin_exportador": True, "error": f"{e}: no se puede dibujar al Gaturro."}
        if cuerpo is None:
            return {"ok": False, "sin_gaturro": True,
                    "error": "No se encontró el Gaturro original del juego, así que no se muestra ninguno."}

        partes = {p: r for p, r in partes.items() if p != TRANSPORTE and r not in {n["ruta"] for n in no_se_ven if n["parte"] == p}}
        con_lugar = {p for p in partes if tiene_lugar(cuerpo, p) or (p == EFECTO and tiene_lugar(cuerpo, "hats"))}
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
        if vehiculo:
            piezas[TRANSPORTE] = vehiculo
        return {"ok": True, "svg": componer(cuerpo, piezas, colores), "sin_imagen": sin_imagen, "sin_lugar": sin_lugar,
                "no_se_ven": no_se_ven, "transporte": sin_pose,
                "colores_de_fabrica": COLORES, "color_de_nariz": tiene_color_de_nariz(cuerpo)}

    def _gaturro_en_vehiculo(self, ruta: str) -> tuple[tuple[str, str] | None, str | None, dict | None]:
        """(vehículo (clase, SVG), cuerpo en su pose, None) para dibujar el Gaturro subido al vehículo `ruta`,
        o (None, None, {"ruta", "motivo"}) si no se puede dibujar igual que en el juego.

        Como `Gaturro.state`/`transportActive`: el Gaturro va al cuadro `transportStand_<tipo>` y el vehículo
        a su cuadro «off». Los dos se congelan en ese cuadro (`swf.congelado_en`)."""
        swf, _, clase = ruta.rpartition(".")
        obtenido = self._categorias_de(swf)
        tipo = (obtenido.get("se_ve", {}).get(clase, {}) if obtenido["ok"] else {}).get("vehiculo")
        if tipo is None:
            return None, None, {"ruta": ruta, "motivo": "no se sabe qué vehículo es"}
        del_cuerpo = self._datos_de_otro_swf(SWF_POSES)
        del_vehiculo = {"ok": True, "data": self._data_swf} if swf == self._swf_abierto else self._datos_de_otro_swf(swf)
        if not del_cuerpo["ok"] or not del_vehiculo["ok"]:
            return None, None, {"ruta": ruta, "motivo": "no se pudo descargar el Gaturro o el vehículo"}
        pose = pose_de_transporte(tipo)
        try:
            if pose not in rotulos(del_cuerpo["data"], CLASE_CUERPO):
                return None, None, {"ruta": ruta, "motivo": f"la pose «{pose}» no está en el Gaturro que se puede leer"}
            cuerpo = self._svg_congelado("gaturro-poses", SWF_POSES, del_cuerpo["data"], CLASE_CUERPO, pose)
            quieto = CUADRO_QUIETO_DEL_VEHICULO if CUADRO_QUIETO_DEL_VEHICULO in rotulos(del_vehiculo["data"], clase) else None
            svg = self._svg_congelado("vehiculos", f"{swf}/{clase}", del_vehiculo["data"], clase, quieto)
        except (OSError, SwfInvalido, subprocess.SubprocessError):
            return None, None, {"ruta": ruta, "motivo": "no se pudo dibujar la pose"}
        if not cuerpo or not svg:
            return None, None, {"ruta": ruta, "motivo": "no se pudo dibujar la pose"}
        if 'id="foreground"' in svg:  # `transportForeground` la pondría delante del Gaturro: no se arma a ojo
            return None, None, {"ruta": ruta, "motivo": "este vehículo tiene una parte que va delante del Gaturro"}
        cuerpo = preparar_cuerpo(cuerpo)
        return (clase, svg), cuerpo, None

    def _svg_congelado(self, carpeta: str, clave: str, data: bytes, clase: str, rotulo: str | None) -> str | None:
        """El SVG de `clase` en el cuadro `rotulo` (None: el primero), exportado una vez por versión."""
        datos = congelado_en(data, clase, rotulo) if rotulo else data
        imagenes = ImagenesPiezas(self._entorno.carpeta_cache() / carpeta, self._exportador)
        ids = {i: c for i, c in leer_simbolos(datos) if c == clase}
        with self._candado_iconos:
            imagenes.preparar(f"{clave}/{rotulo or 'cuadro1'}", datos, ids)
        return imagenes.svg(f"{clave}/{rotulo or 'cuadro1'}", clase)

    def _motivo_no_se_ve(self, ruta: str, parte: str) -> str | None:
        """Por qué el juego no dibujaría esta Pieza en esta Parte del Gaturro, o None (ver `se_ve`)."""
        swf, _, clase = ruta.rpartition(".")
        obtenido = self._categorias_de(swf)
        donde = obtenido.get("se_ve", {}).get(clase, {}) if obtenido["ok"] else {}
        if parte == EFECTO:
            return motivo_sin_efecto(donde)
        if "no_se_ve" in donde:
            return donde["no_se_ve"]
        if "solo_en" in donde and donde["solo_en"] != parte:
            return f"solo se ve en {PARTES_DEL_CUERPO.get(donde['solo_en'], donde['solo_en'])}"
        if parte == TRANSPORTE and donde.get("solo_en") != TRANSPORTE:
            return "en Transporte solo se ven los vehículos"
        return None

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
        return preparar_cuerpo(cuerpo)

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

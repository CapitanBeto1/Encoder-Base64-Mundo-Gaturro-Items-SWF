"""La animación de una acción, cuadro por cuadro, como la reproduce el juego.

El Gaturro animado (`assets.GaturroMC` de `superHeroesTrajes`) es un MovieClip con su línea de tiempo,
clips adentro (cabeza, brazos, ojos, boca) con las suyas y código en sus cuadros (`addFrameScript`):
frenar, seguir, saltar a un cuadro, y `eyes`/`mouth`/`headAction`, que llevan los ojos, la boca o la
cabeza a un cuadro. Exportar cada cuadro con FFDec no alcanza: FFDec no corre ese código y adelanta
todos los clips. Acá se reproduce como lo hace Flash Player:

- En cada cuadro (24 por segundo, los del cliente), cada clip que está andando pasa al cuadro
  siguiente (después del último, vuelve al primero) y se arma lo que su línea de tiempo coloca o saca.
  Un clip nuevo empieza en su cuadro 1 y no avanza hasta el cuadro siguiente.
- Después corre el código de los cuadros a los que se llegó; si ese código salta a otro cuadro, el
  código de ese cuadro corre a continuación.
- Saltar para atrás vuelve a armar el cuadro: lo que sigue en la misma profundidad con el mismo símbolo
  es el mismo clip (conserva su cuadro); lo demás es nuevo.
- Un error de ActionScript (un clip que no está, un cuadro que no existe) corta el código de ese
  cuadro, como en el juego. El código que no se entiende no se adivina: la animación no se muestra
  (`NoSeReproduce`).

Para dibujar, cada cuadro queda «congelado»: un sprite de un solo cuadro con lo que se ve, cuyos clips de
adentro son, a su vez, sprites congelados en el cuadro en que están (como `swf.congelado_en`, pero en todos
los niveles). FFDec los exporta a SVG de una vez.
"""

import hashlib
import re
import struct
from dataclasses import dataclass, field

from mgitems.swf import (
    TAG_DEFINE_SPRITE, TAG_FIN, TAG_FRAME_LABEL, TAG_PLACE_OBJECT2, TAG_PLACE_OBJECT3, TAG_REMOVE_OBJECT2, TAG_SHOW_FRAME,
    SwfInvalido, _Bits, _descomprimir, _tag, _tags_crudos, leer_simbolos,
)

TAG_REMOVE_OBJECT = 5
# Tags que definen un símbolo nuevo con su id al principio (para no repetir ids al agregar sprites).
_TAGS_QUE_DEFINEN = {2, 6, 7, 10, 11, 14, 20, 21, 22, 32, 33, 34, 35, 36, 37, 39, 46, 48, 60, 75, 83, 84, 87, 90, 91}

CUADROS_POR_SEGUNDO = 24  # MMO.swf: frameRate="24"
MAXIMO_DE_CUADROS = 600
CUADROS_QUIETO = 50  # el Gaturro parado antes de la acción (los ojos y la boca terminan de acomodarse)
_MAXIMO_DE_CODIGO = 10000  # código que corre en un mismo cuadro: más que esto es un salto sin fin


class NoSeReproduce(Exception):
    """La animación tiene algo que no se sabe reproducir igual que el juego."""


class _ErrorDeCodigo(Exception):
    """Como un error de ActionScript: corta el código de ese cuadro."""


# --- Lectura del SWF ---

@dataclass
class _Colocacion:
    """Un PlaceObject: `simbolo` si pone un símbolo, y dónde está su id en `crudo` para cambiarlo."""
    mueve: bool
    profundidad: int
    simbolo: int | None
    nombre: str | None
    crudo: bytes
    pos_simbolo: int | None


def _fin_matriz(datos: bytes, inicio: int) -> int:
    bits = _Bits(datos, inicio)
    for _ in range(2):  # escala y rotación, si están
        if bits.sin_signo(1):
            bits.sin_signo(2 * bits.sin_signo(5))
    bits.sin_signo(2 * bits.sin_signo(5))
    return (bits._pos + 7) // 8


def _fin_color(datos: bytes, inicio: int) -> int:
    bits = _Bits(datos, inicio)
    suma, multiplica = bits.sin_signo(1), bits.sin_signo(1)
    bits.sin_signo(bits.sin_signo(4) * 4 * (suma + multiplica))
    return (bits._pos + 7) // 8


def _colocacion(codigo: int, cuerpo: bytes, crudo: bytes) -> _Colocacion:
    cabecera = len(crudo) - len(cuerpo)
    banderas, q = cuerpo[0], 1
    if codigo == TAG_PLACE_OBJECT3:
        banderas3, q = cuerpo[1], 2
        if banderas3 & 0x08 or (banderas3 & 0x10 and banderas & 0x02):  # nombre de clase
            q = cuerpo.index(b"\0", q) + 1
    profundidad = struct.unpack_from("<H", cuerpo, q)[0]
    q += 2
    simbolo = pos = None
    if banderas & 0x02:
        simbolo, pos = struct.unpack_from("<H", cuerpo, q)[0], cabecera + q
        q += 2
    if banderas & 0x04:
        q = _fin_matriz(cuerpo, q)
    if banderas & 0x08:
        q = _fin_color(cuerpo, q)
    if banderas & 0x10:
        q += 2
    nombre = None
    if banderas & 0x20:
        fin = cuerpo.index(b"\0", q)
        nombre = cuerpo[q:fin].decode("utf-8", "replace")
    return _Colocacion(bool(banderas & 0x01), profundidad, simbolo, nombre, crudo, pos)


@dataclass
class _Sprite:
    id: int
    cuadros: list[list[tuple]]  # por cuadro: ("pone", _Colocacion) o ("saca", profundidad)
    rotulos: dict[str, int]

    @property
    def total(self) -> int:
        return max(1, len(self.cuadros))


def _leer_sprite(id_sprite: int, cuerpo: bytes) -> _Sprite:
    cuadros, actual, rotulos = [], [], {}
    for codigo, interno, crudo in _tags_crudos(cuerpo, 4):
        if codigo == TAG_FRAME_LABEL:
            rotulos.setdefault(interno.split(b"\0")[0].decode("utf-8", "replace"), len(cuadros) + 1)
        elif codigo in (TAG_PLACE_OBJECT2, TAG_PLACE_OBJECT3):
            actual.append(("pone", _colocacion(codigo, interno, crudo)))
        elif codigo == TAG_REMOVE_OBJECT2:
            actual.append(("saca", struct.unpack_from("<H", interno)[0]))
        elif codigo == TAG_REMOVE_OBJECT:
            actual.append(("saca", struct.unpack_from("<H", interno, 2)[0]))
        elif codigo == TAG_SHOW_FRAME:
            cuadros.append(actual)
            actual = []
    return _Sprite(id_sprite, cuadros, rotulos)


# --- El código de los cuadros (lo que exporta FFDec) ---

_FUNCION = re.compile(r"(?:public|internal|private|protected)\s+function\s+(\w+)\(([^)]*)\)\s*:\s*[\w*]+\s*\{")
_LLAMADA = re.compile(
    r"(?:(?:MovieClip\((?P<base>[\w.]+)\.getChildAt\((?P<indice>\d+)\)\)|(?P<ruta>[\w.]+))\.)?(?P<metodo>\w+)\((?P<args>[^()]*)\);"
)
_ASIGNACION = re.compile(r"(?P<variable>\w+) = MovieClip\((?P<base>[\w.]+)\.getChildAt\((?P<indice>\d+)\)\);")
_SIN_EFECTO = re.compile(r"(?:trace|dispatchEvent|Security\.\w+)\(.*\);|super\(\);")


def _funciones(fuente: str):
    """(nombre, parámetros, cuerpo) de cada función de la clase."""
    for m in _FUNCION.finditer(fuente):
        nivel, pos = 1, m.end()
        while nivel and pos < len(fuente):
            nivel += {"{": 1, "}": -1}.get(fuente[pos], 0)
            pos += 1
        parametros = [p.split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]
        yield m.group(1), parametros, fuente[m.end():pos - 1]


def _sentencia(linea: str) -> tuple:
    if _SIN_EFECTO.fullmatch(linea):
        return ("nada",)
    if m := _ASIGNACION.fullmatch(linea):
        return ("asigna", m.group("variable"), ("hijo", m.group("base").split("."), int(m.group("indice"))))
    if m := _LLAMADA.fullmatch(linea):
        if m.group("base"):
            destino = ("hijo", m.group("base").split("."), int(m.group("indice")))
        else:
            destino = ("ruta", m.group("ruta").split(".")) if m.group("ruta") else None
        args = [a.strip() for a in m.group("args").split(",") if a.strip()]
        return ("llama", destino, m.group("metodo"), args)
    return ("desconocida", linea)


def _bloque(lineas: list[str], i: int) -> tuple[list, int]:
    sentencias = []
    while i < len(lineas):
        linea = lineas[i]
        if linea == "}":
            return sentencias, i + 1
        if m := re.fullmatch(r"if\((.*)\)", linea):
            if i + 1 < len(lineas) and lineas[i + 1] == "{":
                cuerpo, i = _bloque(lineas, i + 2)
            else:
                cuerpo, i = [_sentencia(lineas[i + 1])] if i + 1 < len(lineas) else [], i + 2
            sentencias.append(("si", m.group(1), cuerpo))
            continue
        sentencias.append(_sentencia(linea))
        i += 1
    return sentencias, i


def _sentencias(texto: str) -> list:
    return _bloque([linea.strip() for linea in texto.splitlines() if linea.strip()], 0)[0]


class _Codigo:
    """El código de una clase: el de cada cuadro (desde 1) y sus métodos."""

    def __init__(self, fuente: str):
        funciones = {nombre: (parametros, cuerpo) for nombre, parametros, cuerpo in _funciones(fuente)}
        self.cuadros: dict[int, list] = {}
        registro = re.search(r"addFrameScript\(([^)]*)\);", fuente)
        pares = [p.strip() for p in registro.group(1).split(",")] if registro else []
        for indice, nombre in zip(pares[::2], pares[1::2]):
            if nombre in funciones:
                self.cuadros[int(indice) + 1] = _sentencias(funciones[nombre][1])
        de_cuadro = set(pares[1::2])
        self.metodos = {n: (p, _sentencias(c)) for n, (p, c) in funciones.items() if n not in de_cuadro}


class Linea:
    """Las líneas de tiempo y el código de los cuadros de un SWF. `fuentes`: clase (sin paquete) → código AS3."""

    def __init__(self, data: bytes, fuentes: dict[str, str]):
        self.swf = _descomprimir(data)
        bits = self.swf[8] >> 3
        self._inicio = 8 + (5 + bits * 4 + 7) // 8 + 4
        self.clases = dict(leer_simbolos(data))  # id → clase
        self.ids = {c: i for i, c in self.clases.items()}
        self.sprites: dict[int, _Sprite] = {}
        mayor = 0
        try:
            for codigo, cuerpo, _ in _tags_crudos(self.swf, self._inicio):
                if codigo in _TAGS_QUE_DEFINEN and len(cuerpo) >= 2:
                    mayor = max(mayor, struct.unpack_from("<H", cuerpo)[0])
                if codigo == TAG_DEFINE_SPRITE:
                    id_sprite = struct.unpack_from("<H", cuerpo)[0]
                    self.sprites[id_sprite] = _leer_sprite(id_sprite, cuerpo)
        except (struct.error, IndexError, ValueError) as e:
            raise SwfInvalido("El SWF está dañado") from e
        self._siguiente_id = mayor + 1
        self.codigos: dict[int, _Codigo] = {}
        self.con_codigo: set[str] = set()  # las clases cuyo código ya se leyó
        self.agregar_codigo(fuentes, {c for c in self.ids if c.rpartition(".")[2] in fuentes})
        self.congelados: dict[str, tuple[int, bytes]] = {}  # clave → (id, DefineSprite)

    def agregar_codigo(self, fuentes: dict[str, str], clases: set[str]) -> None:
        """El código de `clases`, ya leídas (`fuentes`: clase sin paquete → código AS3; la que no está, no tiene)."""
        for clase in clases:
            id_sprite, corto = self.ids.get(clase), clase.rpartition(".")[2]
            if id_sprite in self.sprites and corto in fuentes:
                self.codigos[id_sprite] = _Codigo(fuentes[corto])
            self.con_codigo.add(clase)

    def alcanzables(self, clase: str) -> set[str]:
        """Las clases de los sprites que el de `clase` puede llegar a mostrar (para exportar solo su código)."""
        pendientes, vistos = [self.ids[clase]] if clase in self.ids else [], set()
        while pendientes:
            id_sprite = pendientes.pop()
            if id_sprite in vistos or id_sprite not in self.sprites:
                continue
            vistos.add(id_sprite)
            pendientes += [a[1].simbolo for cuadro in self.sprites[id_sprite].cuadros for a in cuadro
                           if a[0] == "pone" and a[1].simbolo is not None]
        return {self.clases[i] for i in vistos if i in self.clases}

    def congelar(self, clave: str, cuerpo_tags: bytes) -> int:
        if clave not in self.congelados:
            id_sprite, self._siguiente_id = self._siguiente_id, self._siguiente_id + 1
            self.congelados[clave] = (id_sprite, _tag(TAG_DEFINE_SPRITE, struct.pack("<HH", id_sprite, 1) + cuerpo_tags))
        return self.congelados[clave][0]

    def swf_con_congelados(self) -> bytes:
        """El SWF con los sprites congelados agregados (antes del fin)."""
        fin = len(self.swf) - 2 if self.swf.endswith(b"\0\0") else len(self.swf)
        nuevos = b"".join(tag for _, tag in self.congelados.values())
        resultado = bytearray(b"FWS" + self.swf[3:fin] + nuevos + self.swf[fin:])
        struct.pack_into("<I", resultado, 4, len(resultado))
        return bytes(resultado)


# --- La reproducción ---

@dataclass(eq=False)
class Clip:
    linea: Linea
    sprite: _Sprite
    nombre: str | None = None
    cuadro: int = 0
    anda: bool = True
    vivo: bool = True
    lista: dict = field(default_factory=dict)  # profundidad → [símbolo, [_Colocacion], Clip | None]
    de_codigo: list = field(default_factory=list)  # agregados con addChild, encima de la línea de tiempo
    variables: dict = field(default_factory=dict)

    def hijos(self) -> list["Clip"]:
        """Los clips de adentro en el orden de `getChildAt`: la línea de tiempo por profundidad y después los agregados."""
        return [self.lista[p][2] for p in sorted(self.lista) if self.lista[p][2]] + self.de_codigo

    def hijo(self, nombre: str) -> "Clip | None":
        return next((c for c in self.hijos() if c.nombre == nombre), None)


def _morir(clip: Clip) -> None:
    clip.vivo = False
    for hijo in clip.hijos():
        _morir(hijo)


class Simulador:
    def __init__(self):
        self._pendientes: list[tuple[Clip, int]] = []
        self.al_entrar_al_cuadro = []  # funciones que corren al empezar cada cuadro (ENTER_FRAME)

    def nuevo(self, linea: Linea, clase: str) -> Clip:
        """Un clip nuevo de `clase`, en su cuadro 1 (su código corre con `correr_codigo`)."""
        if linea.ids.get(clase) not in linea.sprites:
            raise NoSeReproduce(f"no se encontró {clase}")
        return self._crear(linea, linea.ids[clase], None)

    def _crear(self, linea: Linea, simbolo: int, nombre: str | None) -> Clip | None:
        if simbolo not in linea.sprites:
            return None  # una forma, un texto: no tiene línea de tiempo
        clip = Clip(linea, linea.sprites[simbolo], nombre)
        self._ir(clip, 1)
        return clip

    def _aplicar(self, clip: Clip, cuadro: int, lista: dict, crear: bool) -> None:
        for accion in clip.sprite.cuadros[cuadro - 1] if cuadro <= len(clip.sprite.cuadros) else []:
            if accion[0] == "saca":
                quitado = lista.pop(accion[1], None)
                if crear and quitado and quitado[2]:
                    _morir(quitado[2])
                continue
            colocacion = accion[1]
            actual = lista.get(colocacion.profundidad)
            if colocacion.simbolo is not None and (not colocacion.mueve or not actual or actual[0] != colocacion.simbolo):
                if crear and actual and actual[2]:
                    _morir(actual[2])
                hijo = self._crear(clip.linea, colocacion.simbolo, colocacion.nombre) if crear else None
                lista[colocacion.profundidad] = [colocacion.simbolo, [colocacion], hijo]
            elif actual:
                actual[1].append(colocacion)

    def _ir(self, clip: Clip, cuadro: int) -> None:
        if cuadro == clip.cuadro:
            return
        if cuadro > clip.cuadro:
            for c in range(clip.cuadro + 1, cuadro + 1):
                self._aplicar(clip, c, clip.lista, crear=True)
        else:
            # Para atrás: se arma el cuadro desde el principio y se conserva lo que sigue igual.
            nueva: dict = {}
            for c in range(1, cuadro + 1):
                self._aplicar(clip, c, nueva, crear=False)
            for profundidad, entrada in nueva.items():
                anterior = clip.lista.get(profundidad)
                if anterior and anterior[0] == entrada[0]:
                    entrada[2] = anterior[2]
                else:
                    if anterior and anterior[2]:
                        _morir(anterior[2])
                    entrada[2] = self._crear(clip.linea, entrada[0], entrada[1][0].nombre)
            for profundidad, anterior in clip.lista.items():
                if profundidad not in nueva and anterior[2]:
                    _morir(anterior[2])
            clip.lista = nueva
        clip.cuadro = cuadro
        self._pendientes.append((clip, cuadro))

    def todos(self, raiz: Clip) -> list[Clip]:
        resultado = [raiz]
        for hijo in raiz.hijos():
            resultado += self.todos(hijo)
        return resultado

    def avanzar(self, raiz: Clip) -> None:
        """Un cuadro del juego."""
        for funcion in self.al_entrar_al_cuadro:
            funcion()
        for clip in self.todos(raiz):
            if clip.vivo and clip.anda and clip.sprite.total > 1:
                self._ir(clip, clip.cuadro + 1 if clip.cuadro < clip.sprite.total else 1)
        self.correr_codigo()

    def correr_codigo(self) -> None:
        veces = 0
        while self._pendientes:
            clip, cuadro = self._pendientes.pop(0)
            veces += 1
            if veces > _MAXIMO_DE_CODIGO:
                raise NoSeReproduce("su código salta sin fin")
            codigo = clip.linea.codigos.get(clip.sprite.id)
            if not clip.vivo or clip.cuadro != cuadro or not codigo or cuadro not in codigo.cuadros:
                continue
            try:
                self._ejecutar(clip, codigo.cuadros[cuadro], {})
            except _ErrorDeCodigo:
                pass

    def llamar(self, clip: Clip, metodo: str, args: list) -> None:
        try:
            self._llamar(clip, metodo, args)
        except _ErrorDeCodigo as e:
            raise NoSeReproduce(str(e)) from e

    def _ejecutar(self, clip: Clip, sentencias: list, parametros: dict) -> None:
        for sentencia in sentencias:
            tipo = sentencia[0]
            if tipo == "nada":
                continue
            if tipo == "desconocida":
                raise NoSeReproduce(f"tiene código que no se sabe reproducir («{sentencia[1]}»)")
            if tipo == "si":
                if self._condicion(clip, sentencia[1]):
                    self._ejecutar(clip, sentencia[2], parametros)
            elif tipo == "asigna":
                clip.variables[sentencia[1]] = self._destino(clip, sentencia[2])
            else:
                destino = self._destino(clip, sentencia[1])
                self._llamar(destino, sentencia[2], [self._valor(a, parametros) for a in sentencia[3]])

    def _condicion(self, clip: Clip, texto: str) -> bool:
        resultado = True
        for termino in (t.strip() for t in texto.split("&&")):
            if m := re.fullmatch(r"Boolean\(([\w.]+)\)", termino):
                resultado = resultado and self._buscar(clip, m.group(1).split(".")) is not None
            elif m := re.fullmatch(r"([\w.]+)\.numChildren > 0", termino):
                encontrado = self._buscar(clip, m.group(1).split("."))
                if encontrado is None:
                    raise _ErrorDeCodigo(f"no está {m.group(1)}")
                resultado = resultado and bool(encontrado.hijos())
            else:
                raise NoSeReproduce(f"tiene una condición que no se sabe reproducir («{texto}»)")
        return resultado

    def _buscar(self, clip: Clip, ruta: list[str]) -> Clip | None:
        actual = clip.variables.get(ruta[0]) or clip.hijo(ruta[0])
        for nombre in ruta[1:]:
            actual = actual.hijo(nombre) if actual else None
        return actual

    def _destino(self, clip: Clip, descripcion) -> Clip:
        if descripcion is None:
            return clip
        encontrado = self._buscar(clip, descripcion[1])
        if descripcion[0] == "hijo":
            hijos = encontrado.hijos() if encontrado else []
            encontrado = hijos[descripcion[2]] if descripcion[2] < len(hijos) else None
        if encontrado is None:
            raise _ErrorDeCodigo(f"no está {'.'.join(descripcion[1])}")
        return encontrado

    @staticmethod
    def _valor(texto: str, parametros: dict):
        if texto.startswith('"') and texto.endswith('"'):
            return texto[1:-1]
        if re.fullmatch(r"-?\d+", texto):
            return int(texto)
        if texto in parametros:
            return parametros[texto]
        raise NoSeReproduce(f"usa un valor que no se sabe reproducir («{texto}»)")

    def _llamar(self, clip: Clip, metodo: str, args: list) -> None:
        if metodo == "stop":
            clip.anda = False
        elif metodo == "play":
            clip.anda = True
        elif metodo in ("gotoAndStop", "gotoAndPlay"):
            destino = args[0] if isinstance(args[0], int) else clip.sprite.rotulos.get(args[0])
            if destino is None or not 1 <= destino <= clip.sprite.total:
                raise _ErrorDeCodigo(f"no hay un cuadro «{args[0]}»")
            clip.anda = metodo == "gotoAndPlay"
            self._ir(clip, destino)
        elif metodo == "nextFrame" and clip.cuadro < clip.sprite.total:
            clip.anda = False
            self._ir(clip, clip.cuadro + 1)
        elif (codigo := clip.linea.codigos.get(clip.sprite.id)) and metodo in codigo.metodos:
            parametros, cuerpo = codigo.metodos[metodo]
            self._ejecutar(clip, cuerpo, dict(zip(parametros, args)))
        else:
            raise NoSeReproduce(f"llama a «{metodo}», que no se sabe reproducir")


def estado(raiz: Clip, simulador: Simulador) -> tuple:
    """Todo lo que decide los cuadros que siguen: si se repite, la animación vuelve a empezar desde ahí."""
    return tuple((id(c.linea), c.sprite.id, c.cuadro, c.anda, len(c.hijos())) for c in simulador.todos(raiz))


def congelar(clip: Clip) -> str:
    """La clave del sprite congelado de `clip` tal como se ve ahora (lo agrega a los congelados de su SWF)."""
    partes, claves = [], []
    for profundidad in sorted(clip.lista):
        simbolo, colocaciones, hijo = clip.lista[profundidad]
        clave_hijo = congelar(hijo) if hijo else None
        id_hijo = clip.linea.congelados[clave_hijo][0] if clave_hijo else None
        for colocacion in colocaciones:
            if id_hijo is not None and colocacion.pos_simbolo is not None:
                crudo = bytearray(colocacion.crudo)
                struct.pack_into("<H", crudo, colocacion.pos_simbolo, id_hijo)
                partes.append(bytes(crudo))
            else:
                partes.append(colocacion.crudo)
            claves.append(hashlib.sha1(colocacion.crudo).hexdigest() + (clave_hijo or ""))
    clave = hashlib.sha1("|".join(claves).encode()).hexdigest()[:20]
    clip.linea.congelar(clave, b"".join(partes) + _tag(TAG_SHOW_FRAME) + _tag(TAG_FIN))
    return clave


# --- Una acción del Gaturro ---

@dataclass
class CuadroDeAccion:
    gaturro: str  # clave del Gaturro congelado
    efecto: str | None  # clave de la Pieza de la cabeza, si está
    objeto: str | None  # clave de la Pieza de la acción, si está


@dataclass
class Accion:
    cuadros: list[CuadroDeAccion]
    repite_desde: int | None  # desde qué cuadro se repite sin fin (None: termina en el último)
    espejo: bool  # la Pieza de la acción va dada vuelta (rótulo `lookRight`)


def simular_accion(gaturro: Linea, clase_gaturro: str, animacion: str, objeto: tuple[Linea, str] | None = None,
                   efecto: tuple[Linea, str] | None = None) -> Accion:
    """El Gaturro parado (con la Pieza del efecto en la cabeza, `GaturroEffectsManager.applyHead`) y después
    `Gaturro.state(animacion)`: `gotoAndPlay` y la Pieza de la acción en `objects_ph`, que se frena en su
    último cuadro (`GaturroAnimationController`)."""
    simulador = Simulador()
    raiz = simulador.nuevo(gaturro, clase_gaturro)
    simulador.correr_codigo()
    clip_efecto = None
    if efecto and (cabeza := raiz.hijo("head")):
        clip_efecto = simulador.nuevo(*efecto)
        cabeza.de_codigo.append(clip_efecto)
        simulador.correr_codigo()
    for _ in range(CUADROS_QUIETO):
        simulador.avanzar(raiz)
    if animacion not in raiz.sprite.rotulos:
        raise NoSeReproduce(f"el Gaturro no tiene el cuadro «{animacion}»")
    simulador.llamar(raiz, "gotoAndPlay", [animacion])
    simulador.correr_codigo()

    clip_objeto, espejo = None, False
    if objeto and (lugar := raiz.hijo("objects_ph")):
        for viejo in lugar.de_codigo:
            _morir(viejo)
        clip_objeto = simulador.nuevo(*objeto)
        lugar.de_codigo = [clip_objeto]
        simulador.correr_codigo()
        espejo = "lookRight" in clip_objeto.sprite.rotulos

        def frenar_en_el_ultimo():  # stopObjectOnLastFrame
            if lugar.de_codigo and lugar.de_codigo[0].cuadro == lugar.de_codigo[0].sprite.total:
                lugar.de_codigo[0].anda = False
        simulador.al_entrar_al_cuadro.append(frenar_en_el_ultimo)

    cuadros, vistos, repite_desde = [], {}, None
    for indice in range(MAXIMO_DE_CUADROS):
        firma = estado(raiz, simulador)
        if firma in vistos:
            repite_desde = vistos[firma]
            break
        vistos[firma] = indice
        cuadros.append(CuadroDeAccion(
            congelar(raiz),
            congelar(clip_efecto) if clip_efecto and clip_efecto.vivo else None,
            congelar(clip_objeto) if clip_objeto and clip_objeto.vivo else None,
        ))
        simulador.avanzar(raiz)
    if repite_desde == len(cuadros) - 1:
        repite_desde = None  # quedó quieto: termina ahí
    return Accion(cuadros, repite_desde, espejo)


# --- Para mostrar los cuadros quietos en el mismo lugar ---

_TAMANO = re.compile(r'height="(?P<alto>-?[\d.]+)px" width="(?P<ancho>-?[\d.]+)px"')
_ANCLAJE = re.compile(r'<g transform="matrix\(1\.0, 0\.0, 0\.0, 1\.0, (?P<x>-?[\d.]+), (?P<y>-?[\d.]+)\)">')


def alinear(svgs: list[str]) -> list[str]:
    """Los SVG que exporta FFDec, todos con el mismo tamaño y el punto de registro en el mismo lugar (cada
    uno viene recortado a lo que dibuja ese cuadro)."""
    limites = []
    for svg in svgs:
        tamano, anclaje = _TAMANO.search(svg), _ANCLAJE.search(svg)
        if not tamano or not anclaje:
            limites.append(None)
            continue
        x, y = float(anclaje.group("x")), float(anclaje.group("y"))
        limites.append((-x, -y, float(tamano.group("ancho")) - x, float(tamano.group("alto")) - y))
    conocidos = [l for l in limites if l]
    if not conocidos:
        return svgs
    x0, y0 = min(l[0] for l in conocidos), min(l[1] for l in conocidos)
    x1, y1 = max(l[2] for l in conocidos), max(l[3] for l in conocidos)
    resultado = []
    for svg, limite in zip(svgs, limites):
        if limite:
            svg = _TAMANO.sub(f'height="{round(y1 - y0, 2)}px" width="{round(x1 - x0, 2)}px"', svg, count=1)
            svg = _ANCLAJE.sub(f'<g transform="matrix(1.0, 0.0, 0.0, 1.0, {round(-x0, 2)}, {round(-y0, 2)})">', svg, count=1)
        resultado.append(svg)
    return resultado


def espejar(svg: str) -> str:
    """La Pieza dada vuelta sobre su punto de registro (`scaleX = -1`)."""
    anclaje = _ANCLAJE.search(svg)
    if not anclaje:
        return svg
    fin = svg.rindex("</g>", 0, svg.index("<defs>")) if "<defs>" in svg else svg.rindex("</g>")
    return svg[:anclaje.end()] + '<g transform="scale(-1, 1)">' + svg[anclaje.end():fin] + "</g>" + svg[fin:]

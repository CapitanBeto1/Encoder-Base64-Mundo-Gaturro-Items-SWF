"""CDN simulado: sirve SWF desde un diccionario y cuenta las descargas, sin red."""

from mgitems.fuente import FuenteCDN, SinConexion, SwfNoEncontrado, Version


class FuenteFalsa(FuenteCDN):
    def __init__(self, swfs: dict[str, bytes] | None = None):
        super().__init__()
        self.swfs = dict(swfs or {})
        self.etags = {nombre: f'"v1-{nombre}"' for nombre in self.swfs}
        self.descargas: list[str] = []
        self.sin_conexion = False

    def publicar(self, nombre: str, data: bytes, etag: str) -> None:
        self.swfs[nombre] = data
        self.etags[nombre] = etag

    # Los de otra carpeta del juego (por ejemplo, los banners) se publican como "<carpeta>/<nombre>".
    def version(self, nombre, carpeta="assets"):
        nombre = nombre if carpeta == "assets" else f"{carpeta}/{nombre}"
        self._chequear(nombre)
        return Version(len(self.swfs[nombre]), self.etags[nombre])

    def descargar(self, nombre, carpeta="assets"):
        nombre = nombre if carpeta == "assets" else f"{carpeta}/{nombre}"
        self._chequear(nombre)
        self.descargas.append(nombre)
        return self.swfs[nombre]

    def _chequear(self, nombre):
        if self.sin_conexion:
            raise SinConexion("sin internet")
        if nombre not in self.swfs:
            raise SwfNoEncontrado(nombre)

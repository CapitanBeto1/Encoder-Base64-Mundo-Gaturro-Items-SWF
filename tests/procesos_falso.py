"""Controlador de procesos simulado: registra lo que se cerró y abrió, sin tocar procesos reales."""

from pathlib import Path

from mgitems.entrega import Procesos


class ProcesosFalso(Procesos):
    def __init__(self, abiertos: tuple[Path, ...] = ()):
        self.abiertos = {p.name for p in abiertos}
        self.historial: list[str] = []
        self.no_se_cierran: set[str] = set()
        self.fiddler_captura = True
        self.al_cerrar = {}  # nombre → función a ejecutar al cerrarlo (ej. Fiddler guardando sus reglas)

    def corriendo(self, ejecutable):
        return ejecutable.name in self.abiertos

    def cerrar(self, ejecutable, espera):
        self.historial.append(f"cerrar {ejecutable.name}")
        if ejecutable.name in self.no_se_cierran:
            return False
        if ejecutable.name in self.abiertos and ejecutable.name in self.al_cerrar:
            self.al_cerrar[ejecutable.name]()
        self.abiertos.discard(ejecutable.name)
        return True

    def abrir(self, ejecutable):
        self.historial.append(f"abrir {ejecutable.name}")
        self.abiertos.add(ejecutable.name)

    def esperar_puerto(self, puerto, espera):
        self.historial.append(f"esperar puerto {puerto}")
        return self.fiddler_captura

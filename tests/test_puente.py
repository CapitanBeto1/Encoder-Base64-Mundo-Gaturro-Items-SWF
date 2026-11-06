"""Lo que la ventana le expone a la interfaz: el núcleo, salvo lo que recibe una ruta (eso lo elige un diálogo)."""
import inspect
import re
from pathlib import Path

import pytest

from mgitems.app import Puente
from mgitems.nucleo import Nucleo
from sistema_falso import SistemaFalso


@pytest.fixture
def puente(tmp_path):
    return Puente(Nucleo(SistemaFalso(tmp_path), catalogo=[]))


def expuestos(objeto) -> dict[str, object]:
    """Los métodos que pywebview le da a la interfaz (`webview.util.get_functions`: los públicos, también los de
    los objetos de adentro)."""
    funciones = {}
    for nombre in dir(objeto):
        if nombre.startswith("_"):
            continue
        atributo = getattr(objeto, nombre)
        if inspect.ismethod(atributo) or inspect.isfunction(atributo):
            funciones[nombre] = atributo
        elif not callable(atributo) and hasattr(atributo, "__module__"):
            funciones |= {f"{nombre}.{n}": f for n, f in expuestos(atributo).items()}
    return funciones


def test_la_interfaz_no_puede_elegir_rutas(puente):
    for nombre, metodo in expuestos(puente).items():
        parametros = set(inspect.signature(metodo).parameters)
        assert not parametros & {"ruta", "carpeta"}, f"{nombre} recibe una ruta: tiene que elegirla un diálogo"


def test_expone_el_resto_del_nucleo(puente):
    nombres = expuestos(puente)
    assert {"generar_encode", "buscar_por_imagen", "convertir_en_npcs", "gaturro"} <= set(nombres)
    assert {"guardados.lista", "guardados.guardar", "guardados.exportar", "guardados.importar"} <= set(nombres)
    assert "guardados.importar_de_archivo" not in nombres  # la del núcleo, con ruta
    assert "corregir_ruta" not in nombres and "elegir_ruta" in nombres  # la ruta, con un diálogo


def test_todo_lo_que_llama_la_interfaz_esta_en_el_puente(puente):
    """Un método del núcleo con un parámetro que se llame como una ruta (`ruta`, `carpeta`) no llega a la interfaz: si
    la interfaz lo usa, falla recién al tocarlo. Acá, cada `api().…` de ui/js tiene que existir."""
    interfaz = Path(__file__).parents[1] / "src" / "mgitems" / "ui" / "js"
    llamados = {m for archivo in interfaz.glob("*.js")
                for m in re.findall(r"api\(\)\.(\w+(?:\.\w+)?)\(", archivo.read_text(encoding="utf-8"))}
    assert len(llamados) > 30, "no se encontraron los llamados de la interfaz"
    assert not llamados - set(expuestos(puente)), "la interfaz llama a algo que el Puente no expone"

"""La sintaxis extendida de una Pieza: colores por forma y ajuste (posición, rotación, escala)."""
from mgitems.personalizar import componer, es_parte_rotable, es_valor_valido, ruta_limpia, separar


def test_sin_colores_ni_ajuste_es_la_pieza_sola():
    assert componer("clothes1.remera5_on") == "clothes1.remera5_on"


def test_colores_por_forma_en_orden():
    valor = componer("clothes1.buzo1_on", colores=[{"color": 0xFF0000}, {"color": 0x00FF00}])
    assert valor == "clothes1.buzo1_on,16711680,65280"


def test_quitar_y_dejar_una_forma():
    valor = componer("clothes1.buzo1_on", colores=[{"quitar": True}, {"color": None}, {"color": 0x0000FF}])
    assert valor == "clothes1.buzo1_on,-3,-2,255"  # -3 quita, -2 deja igual


def test_las_formas_por_defecto_del_final_no_se_nombran():
    assert componer("a.b_on", colores=[{"color": 0xFF}, {"color": None}, {"color": None}]) == "a.b_on,255"


def test_opacidad():
    assert componer("a.b_on", colores=[{"color": 0xFF0000, "opacidad": 5}]) == "a.b_on,16711680;5"
    # 10 es opaco (por defecto): no se escribe.
    assert componer("a.b_on", colores=[{"color": 0xFF0000, "opacidad": 10}]) == "a.b_on,16711680"


def test_ajuste_con_topes():
    assert componer("a.b_on", ajuste={"x": 10, "y": -8, "rot": 25, "escala": 7}) == "a.b_on//10,-8,25,7"
    # Fuera de los topes: se recorta (x e y a ±15, escala 5..10).
    assert componer("a.b_on", ajuste={"x": 99, "escala": 99}) == "a.b_on//15,0,0,10"


def test_ajuste_por_defecto_no_se_escribe():
    assert componer("a.b_on", ajuste={"x": 0, "y": 0, "rot": 0, "escala": 10}) == "a.b_on"


def test_colores_y_ajuste_juntos():
    valor = componer("x.y_on", colores=[{"color": 0x112233}], ajuste={"rot": 90})
    assert valor == "x.y_on,1122867//0,0,90,10"


def test_separar_es_lo_inverso():
    ruta, colores, ajuste = separar("clothes1.buzo1_on,16711680,-3//10,-8,25,7")
    assert ruta == "clothes1.buzo1_on"
    assert colores == [{"color": 0xFF0000, "opacidad": None}, {"quitar": True}]
    assert ajuste == {"x": 10, "y": -8, "rot": 25, "escala": 7}


def test_ruta_limpia():
    assert ruta_limpia("clothes1.buzo1_on,255//10,0,0,10") == "clothes1.buzo1_on"
    assert ruta_limpia("clothes1.buzo1_on") == "clothes1.buzo1_on"


def test_es_valor_valido():
    assert es_valor_valido("clothes1.buzo1_on")
    assert es_valor_valido("clothes1.buzo1_on,16711680,-3,-2//10,-8,25,7")
    assert es_valor_valido("a/b/c.Clase_on,255;5")
    assert not es_valor_valido("clothes1.buzo1_on,rojo")   # color no numérico
    assert not es_valor_valido("clothes1.buzo1_on//x,y")   # ajuste no numérico
    assert not es_valor_valido("sin punto")
    assert not es_valor_valido("clothes1.buzo1_on//")       # ajuste vacío
    assert not es_valor_valido(123)


def test_partes_rotables():
    assert es_parte_rotable("cloth") and es_parte_rotable("hats2") and es_parte_rotable("gripFore")
    assert not es_parte_rotable("foot") and not es_parte_rotable("transport") and not es_parte_rotable("armFore")

// Acciones: un Item de mochila que hace una animación del juego, y su vista previa cuadro por cuadro.

// --- Acciones: un Item de mochila que, al usarlo, hace una animación del juego mostrando una Pieza ---

let animacionesDelJuego = []; // [{id, nombre, grupo, se_dibuja}], en el orden en que se ofrecen
const GRUPOS_ANIMACION = {
  accion: "Acciones",
  no_se_dibuja: "La vista previa no las puede mostrar",
  otras: "Otras (partes de animaciones)",
};

function nuevaAccion() {
  return { id: "", nombre: "", base: null, animacion: "showObject", partes: {}, colores: {} };
}

async function cargarAcciones() {
  if (!partesConocidas.length) partesConocidas = (await api().partes_del_cuerpo()).partes_del_cuerpo;
  if (!animacionesDelJuego.length) {
    animacionesDelJuego = (await api().animaciones()).animaciones;
    $("animacion-accion").replaceChildren(
      ...Object.entries(GRUPOS_ANIMACION).map(([grupo, nombre]) => {
        const g = Object.assign(document.createElement("optgroup"), { label: nombre });
        g.append(...animacionesDelJuego.filter((a) => a.grupo === grupo)
          .map((a) => Object.assign(document.createElement("option"), { value: a.id, textContent: `${a.nombre} (${a.id})` })));
        return g;
      })
    );
  }
  $("animacion-accion").value = lookActual.animacion ?? "";
  await cargarLooks(); // las acciones guardadas, el editor y el inventario
}

$("animacion-accion").addEventListener("change", () => {
  lookActual.animacion = $("animacion-accion").value;
  mostrarEncode(null);
  mostrarBarraLook();
  dibujarGaturro();
});

// --- La vista previa de la acción: la animación entera, cuadro por cuadro como en el juego ---

let animacion = null; // {imagenes: [SVG], secuencia, repite_desde, cuadros_por_segundo, urls, cuadro, reloj}

function detenerAnimacion() {
  if (animacion) clearInterval(animacion.reloj);
  animacion = null;
  $("repetir-accion").hidden = true;
}

// Todas las imágenes con el mismo encuadre (el que abarca todos los cuadros), para que el Gaturro no salte.
function encuadrarAnimacion() {
  const medidor = document.createElement("div");
  medidor.style.cssText = "position:absolute;left:-10000px;top:0;width:10px;height:10px;overflow:hidden;visibility:hidden";
  document.body.append(medidor);
  const documentos = animacion.imagenes.map((svg) => new DOMParser().parseFromString(svg, "image/svg+xml"));
  let caja = null;
  try {
    for (const documento of documentos) {
      const copia = document.importNode(documento.documentElement, true);
      medidor.replaceChildren(copia);
      const b = copia.getBBox();
      if (!b.width || !b.height) continue;
      caja = caja
        ? { x0: Math.min(caja.x0, b.x), y0: Math.min(caja.y0, b.y), x1: Math.max(caja.x1, b.x + b.width), y1: Math.max(caja.y1, b.y + b.height) }
        : { x0: b.x, y0: b.y, x1: b.x + b.width, y1: b.y + b.height };
    }
  } finally {
    medidor.remove();
  }
  const zoom = Number($("imagen-gaturro").dataset.zoom) || 1;
  animacion.urls = documentos.map((documento) => {
    const raiz = documento.documentElement;
    if (caja) {
      const lado = (Math.max(caja.x1 - caja.x0, caja.y1 - caja.y0) * 1.12) / zoom;
      raiz.setAttribute("viewBox", `${(caja.x0 + caja.x1) / 2 - lado / 2} ${(caja.y0 + caja.y1) / 2 - lado / 2} ${lado} ${lado}`);
      raiz.removeAttribute("width");
      raiz.removeAttribute("height");
    }
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(documento));
  });
  mostrarCuadro();
}

function mostrarCuadro() {
  $("imagen-gaturro").src = animacion.urls[animacion.secuencia[animacion.cuadro]];
}

function reproducirAnimacion() {
  clearInterval(animacion.reloj);
  animacion.cuadro = 0;
  mostrarCuadro();
  animacion.reloj = setInterval(() => {
    if (animacion.cuadro + 1 < animacion.secuencia.length) animacion.cuadro++;
    else if (animacion.repite_desde !== null) animacion.cuadro = animacion.repite_desde;
    else return clearInterval(animacion.reloj); // queda en el último, como en el juego
    mostrarCuadro();
  }, 1000 / animacion.cuadros_por_segundo);
}

async function dibujarAccion() {
  const img = $("imagen-gaturro");
  const pedido = (pedidosGaturro.get(img) ?? 0) + 1;
  pedidosGaturro.set(img, pedido);
  const { animacion: id, partes } = lookActual;
  const resultado = await conEsqueleto($("gaturro"), "gaturro",
    () => api().animacion_de_accion({ animacion: id, pieza: partes.action ?? null, efecto: partes.effect ?? null }, coloresDe(lookActual)));
  if (pedidosGaturro.get(img) !== pedido) return;
  if (!resultado.ok) return ($("estado-gaturro").textContent = resultado.error);
  const avisos = [...resultado.avisos, ...(resultado.aviso ? [resultado.aviso] : [])];
  $("estado-gaturro").replaceChildren(...avisos.map((a) => etiqueta(a, "aviso-gaturro")));
  if (!resultado.imagenes.length) {
    // Sin la animación, el Gaturro quieto con lo de la cabeza (lo que el juego muestra antes de usar el Item).
    await pedirGaturro(img, coloresDe(lookActual), partes.effect ? { effect: partes.effect } : {});
    return;
  }
  img.hidden = false;
  animacion = { ...resultado, cuadro: 0, reloj: null };
  encuadrarAnimacion();
  $("repetir-accion").hidden = false;
  reproducirAnimacion();
}

$("repetir-accion").addEventListener("click", () => animacion && reproducirAnimacion());

async function aplicarAccion() {
  const { nombre, animacion, base, partes } = lookActual;
  const pedido = { animacion, base, pieza: partes.action ?? null, efecto: partes.effect ?? null };
  const resultado = await mientras("Aplicando la acción… (tarda unos segundos)", () => api().aplicar_accion(pedido));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  const animacionElegida = animacionesDelJuego.find((a) => a.id === animacion);
  mostrarEncode({ ...resultado, accion: { nombre: nombre || animacionElegida?.nombre || animacion } });
  const avisos = resultado.avisos.map((a) => `${claseDeRuta(a.ruta)}: ${a.motivo}`);
  avisarLista(
    avisos.length
      ? `Acción aplicada, pero no se va a ver todo: ${avisos.join("; ")}. Tocá «Agregar al juego» para recibirla.`
      : "Acción aplicada: tocá «Agregar al juego» para recibirla. Usala desde la mochila, sin caminar.",
    avisos.length ? "advertencia" : "exito"
  );
  mostrarBarraLook();
}

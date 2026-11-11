// Acciones: un Item de mochila que hace una animación del juego (la vista previa la hace el Gaturro en vivo).

// --- Acciones: un Item de mochila que, al usarlo, hace una animación del juego mostrando una Pieza ---

let animacionesDelJuego = []; // [{id, nombre, grupo}], en el orden en que se ofrecen
const GRUPOS_ANIMACION = {
  accion: "Acciones",
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

$("repetir-accion").addEventListener("click", () => gaturroDelLook.repetir());

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

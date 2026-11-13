// Las cargas: mientras algo tarda, su lugar muestra un esqueleto con la forma de lo que viene, nunca un texto.
// Formas: «tarjetas» (una grilla de tarjetas vacías), «filas» (una lista), «gaturro» (su silueta), «foto» (la miniatura de
// un guardado) y «encode» (renglones).
// Lo que tarda menos de ESPERA_ESQUELETO no muestra nada, para que no parpadee.

const ESPERA_ESQUELETO = 120;
const ALTO_ESQUELETO = { tarjetas: 110, filas: 46 };

// Pone el esqueleto en `lugar` y devuelve con qué sacarlo. Las tarjetas y las filas reemplazan lo que había: cuando
// llega lo de verdad, lo pisa.
function esqueleto(lugar, forma) {
  if (!lugar) return () => {};
  const poner = setTimeout(() => {
    lugar.setAttribute("aria-busy", "true");
    if (!(forma in ALTO_ESQUELETO)) return lugar.classList.add("cargando");
    const estilo = getComputedStyle(lugar);
    const columnas = estilo.display.includes("grid") ? estilo.gridTemplateColumns.split(" ").length : 1;
    const filas = estilo.gridTemplateRows === "none"
      ? Math.max(2, Math.floor(lugar.clientHeight / ALTO_ESQUELETO[forma]))
      : estilo.gridTemplateRows.split(" ").length;
    lugar.replaceChildren(...Array.from({ length: Math.min(60, columnas * Math.min(filas, 10)) }, (_, i) => {
      const vacio = Object.assign(document.createElement("li"), { className: `esqueleto esqueleto-${forma}` });
      // La ola recorre la grilla en diagonal: arriba a la izquierda primero.
      vacio.style.setProperty("--i", (i % columnas) + Math.floor(i / columnas));
      vacio.innerHTML = forma === "tarjetas" ? '<span class="img"></span><span class="txt"></span><span class="txt corto"></span>'
        : '<span class="img"></span><span class="txt"></span>';
      return vacio;
    }));
  }, ESPERA_ESQUELETO);
  return () => {
    clearTimeout(poner);
    lugar.removeAttribute("aria-busy");
    lugar.classList.remove("cargando");
    lugar.querySelectorAll(":scope > .esqueleto").forEach((vacio) => vacio.remove());
  };
}

// Una tarea con el esqueleto puesto mientras dura.
async function conEsqueleto(lugar, forma, tarea) {
  const sacar = esqueleto(lugar, forma);
  try {
    return await tarea();
  } finally {
    sacar();
  }
}

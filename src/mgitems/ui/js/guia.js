// La guía de arriba: en qué paso de la pestaña estás. Los pasos de cada una están en PESTANA (`pasos`): lo hecho
// hasta el último paso hecho queda en verde y el que sigue, resaltado.

let pasoQueSigue = "";

function mostrarGuia() {
  const pasos = dePestana().pasos();
  const ultimoHecho = pasos.findLastIndex(([, hecho]) => hecho);
  pasoQueSigue = pasos[ultimoHecho + 1]?.[0] ?? "";
  explicarDeshabilitados();
  $("guia").replaceChildren(
    ...pasos.map(([texto], i) => {
      const estado = i <= ultimoHecho ? "hecho" : i === ultimoHecho + 1 ? "actual" : "falta";
      const paso = Object.assign(document.createElement("li"), { className: estado });
      if (estado === "actual") paso.setAttribute("aria-current", "step");
      paso.append(estado === "hecho" ? icono("check", "numero-paso") : etiqueta(String(i + 1), "numero-paso"), etiqueta(texto, "texto-paso"));
      return paso;
    })
  );
}

// Los botones principales, deshabilitados, dicen por qué al pasar el mouse: qué falta (el paso que sigue de la guía), o
// que el programa está trabajando. Cambian en varios lugares, así que se mira cuándo se habilitan o deshabilitan.
const CON_MOTIVO = ["generar", "entregar", "aplicar-look", "entregar-look", "agregar-trucada", "agregar-npc"];

function explicarDeshabilitados() {
  for (const id of CON_MOTIVO) {
    const boton = $(id);
    boton.dataset.titulo ??= boton.title;
    boton.title = !boton.disabled ? boton.dataset.titulo
      : !conectado ? "Esperá a que el programa termine de abrir."
      : ocupado ? "Esperá a que termine lo que está haciendo."
      : pasoQueSigue ? `Primero: ${pasoQueSigue.charAt(0).toLowerCase()}${pasoQueSigue.slice(1)}.`
      : boton.dataset.titulo;
  }
}

const habilitados = new MutationObserver(explicarDeshabilitados);
for (const id of CON_MOTIVO) habilitados.observe($(id), { attributes: true, attributeFilter: ["disabled"] });

// La guía de arriba: en qué paso de la pestaña estás. Los pasos de cada una están en PESTANA (`pasos`): lo hecho
// hasta el último paso hecho queda en verde y el que sigue, resaltado.

function mostrarGuia() {
  const pasos = dePestana().pasos();
  const ultimoHecho = pasos.findLastIndex(([, hecho]) => hecho);
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

// Detrás del Gaturro, uno de los fondos del perfil del juego (los saca scripts/sacar_arte.py a ui/arte/fondos/), con las
// flechas del juego para cambiarlo: en la tarjeta, en «Mis …» y en «Elige tus colores». Lo elegido queda para la
// próxima vez. Sin el arte, el escenario queda con su color.
const FONDO_DE_FABRICA = 29; // el de neón
let fondosDelPerfil = [];
let fondoElegido = (() => {
  try {
    const guardado = localStorage.getItem("fondo-del-perfil");
    return guardado === null ? FONDO_DE_FABRICA : Number(guardado);
  } catch {
    return FONDO_DE_FABRICA;
  }
})();

function flechaDelFondo(clase, titulo, paso) {
  const boton = Object.assign(document.createElement("button"), { type: "button", className: clase, title: titulo });
  boton.setAttribute("aria-label", titulo);
  boton.addEventListener("click", () => {
    fondoElegido = (fondoElegido + paso + fondosDelPerfil.length) % fondosDelPerfil.length;
    try {
      localStorage.setItem("fondo-del-perfil", String(fondoElegido));
    } catch {}
    pintarFondosDelPerfil();
  });
  return boton;
}

function pintarFondosDelPerfil() {
  const fondo = `url("${fondosDelPerfil[fondoElegido % fondosDelPerfil.length]}")`;
  for (const escenario of document.querySelectorAll(".escena .gaturro, .escenario-look, .escena-colores")) {
    escenario.classList.add("con-fondo-del-juego");
    escenario.style.setProperty("background-image", fondo, "important");
  }
  const tarjeta = document.querySelector(".escena .gaturro");
  if (!tarjeta.querySelector(".flechas-fondo")) {
    const flechas = Object.assign(document.createElement("div"), { className: "flechas-fondo" });
    flechas.append(flechaDelFondo("fondo-anterior", "Fondo anterior", -1), flechaDelFondo("fondo-siguiente", "Fondo siguiente", 1));
    tarjeta.append(flechas);
  }
}

// Cuántos fondos hay lo dice arte/fondos.js (si falta el arte, no hay fondos).
document.head.append(Object.assign(document.createElement("script"), {
  src: "arte/fondos.js",
  onload: () => {
    fondosDelPerfil = Array.from({ length: window.FONDOS_DEL_PERFIL || 0 }, (_, n) => `arte/fondos/${n + 1}.jpg`);
    if (fondosDelPerfil.length) pintarFondosDelPerfil();
  },
}));

// El modo claro u oscuro (css/celular.css, `<html data-modo>`). Lo elegido queda para la próxima vez; el <head> de
// index.html lo pone antes de dibujar nada, para que no se vea un momento el otro.
function ponerModo(modo) {
  document.documentElement.dataset.modo = modo;
  $("cambiar-modo").textContent = modo === "oscuro" ? "Modo claro" : "Modo oscuro";
  try {
    localStorage.setItem("modo", modo);
  } catch {}
}

ponerModo(document.documentElement.dataset.modo === "oscuro" ? "oscuro" : "claro");
$("cambiar-modo").addEventListener("click", () => ponerModo(document.documentElement.dataset.modo === "oscuro" ? "claro" : "oscuro"));

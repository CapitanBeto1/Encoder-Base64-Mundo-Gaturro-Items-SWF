// Monedas: generar un Encode que da monedas al jugador.

// --- Generar ---

async function generarMonedas(cantidad) {
  if (!cantidad || cantidad < 1) {
    return avisar($("mensaje-monedas"), "Escribí una cantidad mayor que 0.", "advertencia");
  }
  const resultado = await trabando(() => api().dar_monedas(cantidad));
  if (!resultado.ok) return avisar($("mensaje-monedas"), resultado.error, "error");
  mostrarEncode(resultado);
  avisar($("mensaje-monedas"), "");
}

// --- Chips ---

function actualizarPantalla(valor) {
  const num = parseInt(valor, 10);
  $("pantalla-numero").textContent = isNaN(num) || num < 1 ? "—" : num.toLocaleString("es");
}

for (const btn of document.querySelectorAll(".chip-moneda")) {
  btn.addEventListener("click", () => {
    $("cantidad-monedas").value = btn.dataset.cantidad;
    for (const c of document.querySelectorAll(".chip-moneda")) c.classList.toggle("activo", c === btn);
    actualizarPantalla(btn.dataset.cantidad);
  });
}

$("cantidad-monedas").addEventListener("input", () => {
  for (const c of document.querySelectorAll(".chip-moneda")) {
    c.classList.toggle("activo", c.dataset.cantidad === $("cantidad-monedas").value);
  }
  actualizarPantalla($("cantidad-monedas").value);
});

$("generar-monedas").addEventListener("click", () => {
  generarMonedas(parseInt($("cantidad-monedas").value, 10));
});

// Inicializar display y chip activo con el valor por defecto
actualizarPantalla($("cantidad-monedas").value);
const chipInicial = document.querySelector(`.chip-moneda[data-cantidad="${$("cantidad-monedas").value}"]`);
if (chipInicial) chipInicial.classList.add("activo");

// --- Barra de prototipo: 5 estilos de chips ---

function setChips(n) {
  $("vista-monedas").dataset.chips = n;
  for (const btn of document.querySelectorAll(".btn-estilo")) {
    btn.classList.toggle("activo", btn.dataset.chips === n);
  }
  try { localStorage.setItem("proto-monedas-chips", n); } catch {}
}

for (const btn of document.querySelectorAll(".btn-estilo")) {
  btn.addEventListener("click", () => setChips(btn.dataset.chips));
}

// Restaurar estilo guardado
try { setChips(localStorage.getItem("proto-monedas-chips") || "1"); } catch { setChips("1"); }

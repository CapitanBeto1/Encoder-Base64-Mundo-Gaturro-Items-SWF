// Monedas: generar un Encode que da monedas al jugador.

// --- Lógica compartida ---

async function generarMonedas(cantidad) {
  if (!cantidad || cantidad < 1) {
    return avisar($("mensaje-monedas"), "Escribí una cantidad mayor que 0.", "advertencia");
  }
  const resultado = await trabando(() => api().dar_monedas(cantidad));
  if (!resultado.ok) return avisar($("mensaje-monedas"), resultado.error, "error");
  mostrarEncode(resultado);
  avisar($("mensaje-monedas"), "");
}

// --- Variante A: chips rápidos ---

for (const btn of document.querySelectorAll(".chip-moneda")) {
  btn.addEventListener("click", () => {
    $("cantidad-monedas").value = btn.dataset.cantidad;
    for (const c of document.querySelectorAll(".chip-moneda")) c.classList.toggle("activo", c === btn);
  });
}

$("cantidad-monedas").addEventListener("input", () => {
  for (const c of document.querySelectorAll(".chip-moneda")) {
    c.classList.toggle("activo", c.dataset.cantidad === $("cantidad-monedas").value);
  }
});

$("generar-monedas").addEventListener("click", () => {
  generarMonedas(parseInt($("cantidad-monedas").value, 10));
});

// --- Variante B: cartas ---

for (const btn of document.querySelectorAll(".carta-moneda[data-cantidad]")) {
  btn.addEventListener("click", () => {
    $("cantidad-monedas").value = btn.dataset.cantidad;
    generarMonedas(parseInt(btn.dataset.cantidad, 10));
  });
}

const inputB = $("cantidad-b");
const btnB = document.querySelector(".btn-generar-b");

function syncBtnB() {
  btnB.disabled = $("generar-monedas").disabled || !inputB.value;
}

inputB.addEventListener("input", syncBtnB);

btnB.addEventListener("click", () => {
  const v = parseInt(inputB.value, 10);
  $("cantidad-monedas").value = v;
  generarMonedas(v);
});

// --- Variante C: número grande ---

const inputC = $("cantidad-c");
const btnGenC = document.querySelector(".btn-gen-c");

for (const btn of document.querySelectorAll(".preset-c")) {
  btn.addEventListener("click", () => {
    inputC.value = btn.dataset.cantidad;
    $("cantidad-monedas").value = btn.dataset.cantidad;
    for (const p of document.querySelectorAll(".preset-c")) p.classList.toggle("activo", p === btn);
  });
}

inputC.addEventListener("input", () => {
  $("cantidad-monedas").value = inputC.value;
  for (const p of document.querySelectorAll(".preset-c")) {
    p.classList.toggle("activo", p.dataset.cantidad === inputC.value);
  }
});

btnGenC.addEventListener("click", () => {
  generarMonedas(parseInt(inputC.value, 10));
});

// Sincroniza disabled de los botones de B y C con el botón principal (#generar-monedas,
// que es el que actualizarControles maneja).
function syncBotonesMonedas() {
  const dis = $("generar-monedas").disabled;
  syncBtnB();
  btnGenC.disabled = dis;
}

new MutationObserver(syncBotonesMonedas).observe($("generar-monedas"), {
  attributes: true,
  attributeFilter: ["disabled"],
});

// --- Barra de prototipo ---

function setVariante(v) {
  $("vista-monedas").dataset.variante = v;
  for (const btn of document.querySelectorAll(".btn-prototipo")) {
    btn.classList.toggle("activo", btn.dataset.variante === v);
  }
  try { localStorage.setItem("proto-monedas", v); } catch {}
}

for (const btn of document.querySelectorAll(".btn-prototipo")) {
  btn.addEventListener("click", () => setVariante(btn.dataset.variante));
}

// Restaurar variante guardada (con "a" como fallback).
try { setVariante(localStorage.getItem("proto-monedas") || "a"); } catch { setVariante("a"); }

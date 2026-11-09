// Monedas: generar un Encode que da monedas al jugador.

$("generar-monedas").addEventListener("click", async () => {
  const cantidad = parseInt($("cantidad-monedas").value, 10);
  if (!cantidad || cantidad < 1) {
    return avisar($("mensaje-monedas"), "Escribí una cantidad mayor que 0.", "advertencia");
  }
  const resultado = await trabando(() => api().dar_monedas(cantidad));
  if (!resultado.ok) return avisar($("mensaje-monedas"), resultado.error, "error");
  mostrarEncode(resultado);
  avisar($("mensaje-monedas"), "");
});

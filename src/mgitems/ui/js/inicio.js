// El arranque: cuando pywebview está listo, se carga lo de la primera pestaña.

window.addEventListener("pywebviewready", async () => {
  conectado = true;
  actualizarControles();
  mostrarEntorno(await api().estado_entorno());
  cargarParaLaVista();
  ponerDibujosDelJuego();
});
mostrarLista();

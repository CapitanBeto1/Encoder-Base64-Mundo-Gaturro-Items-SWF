import sys
import os
import shutil # Necesario para borrar directorios
import threading
import time

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.append(root_path)

import customtkinter as ctk
from tkinter import filedialog
from config import APP_TITLE, WINDOW_SIZE, DEFAULT_PREFIX_HINT
from swf_reader import leer_swf, extraer_imagenes_swf  
from item_finder import buscar_items
from script_generator import generar_script
from base64_encoder import convertir
from ui.components import crear_contenedor_items, crear_card_item, crear_textbox_base64

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        
        # Estado
        self.archivo = None
        self.items = []
        self.carpeta_temp_actual = None
        self.ultima_carpeta = r"C:\Users\Enzo\Desktop\swf 2024"
        self.cargando = False
        self.animacion_id = None
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # PROTOCOLO DE CIERRE: Ejecuta on_closing al tocar la X
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.crear_interfaz()

    def crear_interfaz(self):
        """Estructura de la UI."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40, pady=20)

        # Botón de selección grande y centrado sin recuadro
        self.btn_swf = ctk.CTkButton(container, text="Seleccionar SWF", width=200, height=50,
                                      font=("Segoe UI", 14), command=self.seleccionar_archivo)
        self.btn_swf.pack(pady=(0, 20))
        # etiqueta para mostrar el nombre del archivo elegido
        self.label_archivo = ctk.CTkLabel(container, text="", font=("Segoe UI", 11))
        self.label_archivo.pack()

        # Búsqueda
        pref_frame = ctk.CTkFrame(container)
        pref_frame.pack(fill="x", pady=5)
        self.pref_entry = ctk.CTkEntry(pref_frame, placeholder_text=DEFAULT_PREFIX_HINT, height=35)
        self.pref_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ctk.CTkButton(pref_frame, text="Buscar Items", width=140, command=self.buscar).pack(side="right", padx=10)

        # Área central
        main_boxes = ctk.CTkFrame(container, fg_color="transparent")
        main_boxes.pack(fill="both", expand=True, pady=10)

        # Frame izquierdo - Items + botones
        left_frame = ctk.CTkFrame(main_boxes, fg_color="transparent")
        left_frame.pack(side="left", expand=True, fill="both", padx=(0, 5))
        self.items_box = crear_contenedor_items(left_frame)
        self.items_box.pack(expand=True, fill="both")
        # Botones para items - centrados en la parte inferior
        left_buttons = ctk.CTkFrame(left_frame, fg_color="transparent")
        left_buttons.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(left_buttons, text="Copiar Nombres", fg_color="#3d3d3d", command=self.copiar_todos_los_nombres).pack(side="left", padx=3)
        ctk.CTkButton(left_buttons, text="Convertir a Base64", command=self.convertir).pack(side="left", padx=3)

        # Frame derecho - Base64 + botones
        right_frame = ctk.CTkFrame(main_boxes, fg_color="transparent")
        right_frame.pack(side="right", expand=True, fill="both", padx=(5, 0))
        right_box_frame, self.base64_box = crear_textbox_base64(right_frame)
        right_box_frame.pack(expand=True, fill="both")
        # Botones para base64 - centrados en la parte inferior
        right_buttons = ctk.CTkFrame(right_frame, fg_color="transparent")
        right_buttons.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(right_buttons, text="Copiar Base64", width=100, command=self.copiar_base64).pack(side="left", padx=3)
        ctk.CTkButton(right_buttons, text="Descargar .txt", fg_color="#2c6e49", command=self.guardar_archivo).pack(side="left", padx=3)

    def on_closing(self):
        """Limpia archivos temporales antes de cerrar la app."""
        temp_path = os.path.join(root_path, "temp_assets")
        if os.path.exists(temp_path):
            try:
                shutil.rmtree(temp_path)
                print("Carpeta temp_assets eliminada correctamente.")
            except Exception as e:
                print(f"No se pudo eliminar la carpeta temporal: {e}")
        
        self.destroy() # Cierra la ventana definitivamente

    def seleccionar_archivo(self):
        """Selecciona el SWF desde la carpeta de Laboulaye."""
        path = filedialog.askopenfilename(initialdir=self.ultima_carpeta, filetypes=[("SWF", "*.swf")])
        if path:
            self.archivo = path
            # actualizar etiqueta con nombre de archivo
            self.label_archivo.configure(text=os.path.basename(path))

    def buscar(self):
        """Inicia la búsqueda en un hilo separado para no congelar la UI."""
        if not self.archivo or self.cargando:
            return
        
        self.cargando = True
        self._mostrar_loader()
        thread = threading.Thread(target=self._buscar_thread, daemon=True)
        thread.start()

    def renderizar_lista(self):
        """Dibuja las cards con el botón de borrar."""
        for widget in self.items_box.winfo_children():
            widget.destroy()
        for i in self.items:
            crear_card_item(self.items_box, i, self.carpeta_temp_actual, self.eliminar_item)

    def eliminar_item(self, item_a_borrar):
        """Filtra la lista y refresca la UI."""
        self.items = [i for i in self.items if i != item_a_borrar]
        self.renderizar_lista()

    # --- Métodos de carga y threading ---
    def _mostrar_loader(self):
        """Muestra un spinner mientras se procesa la búsqueda."""
        for widget in self.items_box.winfo_children():
            widget.destroy()
        loader_frame = ctk.CTkFrame(self.items_box, fg_color="transparent")
        loader_frame.pack(expand=True, fill="both")
        self.loader_label = ctk.CTkLabel(loader_frame, text="⠋", font=("Segoe UI", 48), text_color="#0080FF")
        self.loader_label.pack(expand=True)
        self.loader_texto = ctk.CTkLabel(loader_frame, text="Cargando items...", font=("Segoe UI", 14), text_color="#888888")
        self.loader_texto.pack(pady=(10, 0))
        self._animar_loader(0)

    def _animar_loader(self, frame):
        if not self.cargando:
            return
        spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.loader_label.configure(text=spinner[frame % len(spinner)])
        self.animacion_id = self.after(80, self._animar_loader, frame + 1)

    def _buscar_thread(self):
        try:
            # El usuario escribe solo los términos a buscar (ej: "autoRiver,zapa,bufanda")
            search_terms = [t.strip() for t in self.pref_entry.get().split(",") if t.strip()]
            data = leer_swf(self.archivo)
            # Pasar el archivo SWF para que buscar_items construya rutas automáticas
            self.items = buscar_items(data, search_terms, swf_path=self.archivo)
            nombres_para_ffdec = [i['original'] for i in self.items]
            self.carpeta_temp_actual = extraer_imagenes_swf(self.archivo, nombres_para_ffdec)
            self.after(0, self._finalizar_busqueda)
        except Exception as e:
            print(f"Error en la búsqueda: {e}")
            self.after(0, self._finalizar_busqueda)

    def _finalizar_busqueda(self):
        self.cargando = False
        if self.animacion_id:
            self.after_cancel(self.animacion_id)
        self.renderizar_lista()

    def copiar_todos_los_nombres(self):
        """Copia nombres separados por espacio.

        Para mantener la ruta completa que aparece en el SWF usamos
        el valor original que encontró el escáner. El campo "limpio"
        sólo sirve para eliminar sufijos como _on/_off, pero la ruta
        puede ser importante para la generación del script.
        """
        if not self.items: return
        self.clipboard_clear()
        self.clipboard_append(" ".join([i['original'] for i in self.items]))

    def convertir(self):
        """Genera el Base64 sin padding.

        Para evitar que las rutas terminen en sufijos _on/_off, usamos el
        campo "limpio", que ya elimina esos finales. El nombre limpio
        conserva la ruta completa, por lo que seguimos codificando la
        ruta completa pero sin esos adornos.
        """
        if not self.items: return
        script = generar_script([i['limpio'] for i in self.items], self.archivo)
        self.base64_box.delete("0.0", "end")
        self.base64_box.insert("end", convertir(script))

    def copiar_base64(self):
        """Copia el resultado final."""
        text = self.base64_box.get("0.0", "end-1c")
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)

    def guardar_archivo(self):
        """Guarda el .txt con nombre automático basado en prefijos y SWF."""
        contenido = self.base64_box.get("0.0", "end-1c")
        if not contenido: return
        
        # Obtener prefijos y nombre del SWF
        prefijos = [p.strip() for p in self.pref_entry.get().split(",") if p.strip()]
        swf_name = os.path.splitext(os.path.basename(self.archivo))[0] if self.archivo else "salida"
        
        # Construir nombre automático
        prefijos_str = "_".join(prefijos) if prefijos else "items"
        nombre_automatico = f"{prefijos_str}_{swf_name}.txt"
        
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=nombre_automatico,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, "w") as f: f.write(contenido)
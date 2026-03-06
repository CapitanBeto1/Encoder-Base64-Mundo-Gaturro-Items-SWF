import customtkinter as ctk
from PIL import Image
import os

def crear_contenedor_items(parent):
    """Crea el contenedor con scroll."""
    return ctk.CTkScrollableFrame(parent, label_text="Vista Previa de Items", fg_color="#1a1a1a", corner_radius=15)

def crear_textbox_base64(parent):
    """Crea el cuadro de texto para el código."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    textbox = ctk.CTkTextbox(frame, width=350, height=380, font=("Consolas", 11))
    textbox.pack(side="left", fill="both", expand=True)
    return frame, textbox

def crear_card_item(parent, item_dict, carpeta_assets, al_eliminar):
    """Crea una tarjeta con botón de eliminación."""
    nombre_limpio = item_dict.get("limpio", "Desconocido")
    nombre_original = item_dict.get("original", "").lower()
    
    card = ctk.CTkFrame(parent, corner_radius=12, fg_color="#2b2b2b")
    card.pack(fill="x", padx=5, pady=2)

    # Búsqueda de imagen
    img_path = None
    if os.path.exists(carpeta_assets):
        for raiz, _, archivos in os.walk(carpeta_assets):
            if nombre_original in raiz.lower():
                for arc in archivos:
                    if arc.lower().endswith('.png'):
                        img_path = os.path.join(raiz, arc)
                        break
            if img_path: break

    # Vista previa
    img_label = ctk.CTkLabel(card, text="🚫", width=30, height=30, fg_color="#3d3d3d", corner_radius=8)
    img_label.pack(side="left", padx=5, pady=5)

    if img_path:
        try:
            img_data = Image.open(img_path)
            ctk_img = ctk.CTkImage(light_image=img_data, size=(30, 30))
            img_label.configure(image=ctk_img, text="")
        except: pass

    # Texto del ítem
    info = ctk.CTkFrame(card, fg_color="transparent")
    info.pack(side="left", fill="both", expand=True, padx=5)
    # Mostrar la ruta completa en lugar de recortarla, y desactivar el
    # ajuste de línea para que no se parta en varios renglones.
    # Suponemos que el contenedor tiene suficiente ancho para alojar la
    # cadena entera; el scroll horizontal no es necesario porque el frame
    # se estira con la ventana.
    ctk.CTkLabel(
        info,
        text=nombre_limpio,
        font=("Segoe UI", 10, "bold"),
        anchor="w",
        wraplength=0
    ).pack(fill="x", pady=(5, 0))
    ctk.CTkLabel(info, text="Asset del SWF", font=("Segoe UI", 8), text_color="#888888", anchor="w").pack(fill="x")

    # BOTÓN ELIMINAR (Cruz Roja)
    btn_delete = ctk.CTkButton(
        card, 
        text="✕", 
        width=20, 
        height=20, 
        fg_color="#a12525", 
        hover_color="#7a1a1a",
        command=lambda: al_eliminar(item_dict) # Ejecuta el callback pasando el item
    )
    btn_delete.pack(side="right", padx=5, pady=5)

    return card
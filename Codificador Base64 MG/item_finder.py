import re
import os
import subprocess
import tempfile
import csv

def buscar_items(data, search_terms, swf_path=None):
    """Busca items dentro del SWF seleccionado buscando en el binario descomprimido.
    
    Args:
        data: contenido binario descomprimido del SWF seleccionado
        search_terms: lista de términos simples a buscar (ej: ["zapa", "bufanda"])
        swf_path: ruta del archivo SWF (no usado ahora)
    
    """
    texto = data.decode("utf-8", errors="ignore")
    items = []
    vistos = set()

    print(f"[DEBUG] Búsqueda de términos: {search_terms}")

    for termino in search_terms:
        termino = termino.strip()
        if not termino:
            continue

        # Buscar el término seguido de caracteres permitidos (case-insensitive)
        patron = rf"(?i){re.escape(termino)}[A-Za-z0-9_.-]*"
        coincidencias = re.findall(patron, texto)
        print(f"[DEBUG] Término '{termino}': {len(coincidencias)} encontradas")
        
        if coincidencias:
            for c in coincidencias[:5]:
                print(f"  - {c}")

        for nombre in coincidencias:
            # Filtrar items inválidos
            if nombre.endswith('.as'):
                continue  # Ignorar archivos .as
            
            # Filtrar duplicados malformados como 'zapaBarbie2/zapaBarbie2'
            if '/' in nombre:
                partes = nombre.split('/')
                if len(partes) >= 2 and partes[-1] == partes[-2]:
                    continue  # Ignorar duplicados
            
            # No filtrar por prefijo, buscar todos
            
            # Solo limpiar sufijos _on, _off
            limpio = nombre.replace("_on", "").replace("_off", "")
            
            if limpio not in vistos:
                vistos.add(limpio)
                items.append({"limpio": limpio, "original": nombre})
    
    print(f"[DEBUG] Total items para codificar: {len(items)}")
    return items

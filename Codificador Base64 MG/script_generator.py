import os

def generar_script(items, swf_path):
    # Calcular el prefijo basado en la ruta del SWF
    swf_name = os.path.splitext(os.path.basename(swf_path))[0]
    parent_dir = os.path.dirname(swf_path)
    parent_name = os.path.basename(parent_dir)
    
    if parent_name.lower() != "swf 2024":
        prefix = f"{parent_name}/{swf_name}"
    else:
        prefix = swf_name
    
    lineas = []
    lineas.append("INICIO: DO")
    lineas.append("    on activate A1") # 4 espacios de indentación
    # la línea en blanco debe mantener los 4 espacios para coincidir con ejemplos
    lineas.append("    ")

    for i, item in enumerate(items, start=1):
        lineas.append(f"A{i}: DO")
        lineas.append("    user.state get")
        # Usar el prefijo completo
        lineas.append(f"    inventory.add 1 {prefix}.{item}")

        if i < len(items):
            lineas.append(f"    after 1 A{i+1}")
        else:
            lineas.append("    after 1 INICIO")
        
        if i < len(items):
            lineas.append("")

    # Unimos con \n y agregamos los dos saltos finales para evitar el padding '=='
    return "\n".join(lineas) + "\n\n"
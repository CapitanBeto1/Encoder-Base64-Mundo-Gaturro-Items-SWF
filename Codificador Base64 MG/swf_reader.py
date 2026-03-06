import zlib
import subprocess
import os
import shutil

def leer_swf(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:3] == b"CWS":
        header = data[:8]
        cuerpo = zlib.decompress(data[8:])
        data = b"FWS" + header[3:8] + cuerpo
    return data

def extraer_imagenes_swf(swf_path, nombres_items):
    base_path = os.path.dirname(os.path.abspath(__file__))
    bin_dir = os.path.join(base_path, "bin")
    # Definimos la ruta completa al JAR
    ffdec_path = os.path.join(bin_dir, "ffdec.jar")
    output_dir = os.path.join(base_path, "temp_assets")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    swf_path_norm = os.path.normpath(swf_path)

    try:
        # COMANDO 1: Exportar Sprites (Usamos ffdec_path)
        subprocess.run([
            "java", "-jar", ffdec_path,
            "-export", "sprite", output_dir, swf_path_norm
        ], check=True, capture_output=True, cwd=bin_dir)

        # COMANDO 2: Intentar generar el mapping
        try:
            list_file = os.path.join(output_dir, "mapping.txt")
            resultado = subprocess.run([
                "java", "-jar", ffdec_path,
                "-list", "sprite", swf_path_norm
            ], capture_output=True, text=True, cwd=bin_dir)
            
            if resultado.returncode == 0:
                with open(list_file, "w", encoding="utf-8") as f:
                    f.write(resultado.stdout)
        except Exception:
            print("Aviso: El comando -list falló, se usará búsqueda por nombre.")

    except Exception as e:
        print(f"Error crítico en la extracción: {e}")

    return output_dir
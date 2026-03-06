import base64

def convertir(script):
    # IMPORTANTE: No usamos .strip() para preservar los \n\n del final
    return base64.b64encode(script.encode("latin-1")).decode()
import json, os

with open("mundial/data/selecciones.json", encoding="utf-8") as f:
    db = json.load(f)

arg = db.get("argentina", {})
jor = db.get("jordan", {})

print(f"Argentina win_rate_neutro: {arg.get('win_rate_neutro')}")
print(f"Jordan    win_rate_neutro: {jor.get('win_rate_neutro')}")

for nombre in ["proyeccion_selecciones.py", "modelo.py", "prediccion.py"]:
    if os.path.exists(nombre):
        with open(nombre, encoding="utf-8") as f:  # <-- utf-8 aquí
            contenido = f.read()
        print(f"\nArchivo: {nombre}")
        print(f"¿Tiene _wr_con_fallback?: {'_wr_con_fallback' in contenido}")
        print(f"¿calcular_fuerza_base usa el helper?: {'_wr_con_fallback' in contenido[contenido.find('def calcular_fuerza_base'):]}")
        print(f"¿calcular_ipo_seleccion usa el helper?: {'_wr_con_fallback' in contenido[contenido.find('def calcular_ipo_seleccion'):]}")
        break
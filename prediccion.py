import json


# =============================
# CARGAR BASE DE DATOS
# =============================
def cargar_equipos():
    with open("equipos.json", "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_equipo(nombre, db):
    key = nombre.lower().replace(" ", "")
    return db.get(key)


# =============================
# MODELO (NO MODIFICADO)
# =============================
def calcular_fuerza(forma, win_rate, posicion, goles_diff, partidos, es_local):
    pos_score = 1 / posicion
    goles_norm = max(-1, min(1, goles_diff / partidos))
    localia = 0.03 if es_local else 0

    return (
        (forma * 0.28) +
        (win_rate * 0.27) +
        (pos_score * 0.10) +     
        (goles_norm * 0.30) +    
        localia                  
    )


def predecir_probabilidades(equipo_local, equipo_visitante):
    def filtrar_equipo(equipo):
        return {
            "forma": equipo["forma"],
            "win_rate": equipo["win_rate"],
            "posicion": equipo["posicion"],
            "goles_diff": equipo["goles_diff"],
            "partidos": equipo["partidos"],
            "es_local": equipo["es_local"]
        }

    f_local = calcular_fuerza(**filtrar_equipo(equipo_local))
    f_visitante = calcular_fuerza(**filtrar_equipo(equipo_visitante))

    total = f_local + f_visitante

    # evitar división por 0
    if total == 0:
        return {
            "local": 0.33,
            "empate": 0.34,
            "visitante": 0.33,
            "fuerza_local": 0,
            "fuerza_visitante": 0,
            "diferencia": 0
        }

    prob_local = f_local / total
    prob_visitante = f_visitante / total

    diferencia = abs(f_local - f_visitante) / (f_local + f_visitante + 1e-6)

    prob_empate = 0.22 * (1 / (1 + (diferencia * 4)))
    prob_empate = max(0.12, min(0.30, prob_empate))

    promedio_goles = (
        (equipo_local["goles_diff"] + equipo_visitante["goles_diff"]) /
        (equipo_local["partidos"] + equipo_visitante["partidos"])
    )

    factor_bajo_gol = max(0, 0.1 - promedio_goles)

    prob_empate += factor_bajo_gol

    prob_empate = min(prob_empate, 0.35)

    ajuste = 1 - prob_empate
    prob_local *= ajuste
    prob_visitante *= ajuste

    # =============================
    # 🔥 FIX CLAVE (sin cambiar lógica)
    # =============================
    EPSILON = 0.01  # 1% mínimo

    prob_local = max(EPSILON, prob_local)
    prob_visitante = max(EPSILON, prob_visitante)
    prob_empate = max(EPSILON, prob_empate)

    # normalizar para que sumen 1
    suma = prob_local + prob_visitante + prob_empate

    prob_local /= suma
    prob_visitante /= suma
    prob_empate /= suma

    return {
        "local": prob_local,
        "empate": prob_empate,
        "visitante": prob_visitante,
        "fuerza_local": f_local,
        "fuerza_visitante": f_visitante,
        "diferencia": diferencia
    }

# =============================
# GUARDAR RESULTADOS
# =============================
def guardar_resultado(partido, archivo="partidos.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = []

    data.append(partido)

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================
# GENERAR PARTIDO (CORE)
# =============================
def generar_partido(id, local_nombre, visitante_nombre, db):

    local = obtener_equipo(local_nombre, db)
    visitante = obtener_equipo(visitante_nombre, db)

    if not local or not visitante:
        raise ValueError("❌ Equipo no encontrado en equipos.json")

    # asignar localía
    local["es_local"] = True
    visitante["es_local"] = False

    resultado = predecir_probabilidades(local, visitante)

    # predicción final
    if resultado["local"] > resultado["visitante"] and resultado["local"] > resultado["empate"]:
        pred = local_nombre
    elif resultado["visitante"] > resultado["local"] and resultado["visitante"] > resultado["empate"]:
        pred = visitante_nombre
    else:
        pred = "Empate"

    output = {
        "id": id,
        "local": local_nombre,
        "visitante": visitante_nombre,
        "logo_local": local.get("escudo"),
        "logo_visitante": visitante.get("escudo"),
        "prob_local": resultado["local"],
        "prob_empate": resultado["empate"],
        "prob_visitante": resultado["visitante"],
        "fuerza_local": resultado["fuerza_local"],
        "fuerza_visitante": resultado["fuerza_visitante"],
        "diferencia": resultado["diferencia"],
        "prediccion": pred
    }

    guardar_resultado(output)

    return output


# =============================
# EJECUCIÓN MANUAL
# =============================
if __name__ == "__main__":

    db = cargar_equipos()

    # 👉 aquí solo cambias nombres
    generar_partido(
        1,
        "Monterrey",
        "Puebla",
        db
    )

    print("✅ Partido generado y guardado en partidos.json")
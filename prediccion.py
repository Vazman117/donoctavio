import json
import math
import os


# =============================
# CARGAR BASE
# =============================

def cargar_equipos():
    ruta = os.path.join("scrapper", "equipos.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_equipo(nombre, db):
    key = nombre.lower().replace(" ", "")
    return db.get(key)


# =============================
# CONFIG
# =============================

TOTAL_EQUIPOS = 18

# Menos agresivo que 5.8 → evita exceso de certeza
K_LOGISTICO = 4.2
MAX_FAVORITO = 0.68

# Pesos del modelo (suman 1.0)
PESO_FORMA          = 0.30   # momentum reciente (últimos 5 con pesos exponenciales)
PESO_WINRATE        = 0.22   # win_rate situacional (local o visita según rol)
PESO_GOLES_FAVOR    = 0.12   # capacidad ofensiva
PESO_GOLES_CONTRA   = 0.12   # solidez defensiva
PESO_POSICION       = 0.08   # posición en tabla
PESO_TENDENCIA      = 0.06   # ¿está subiendo o bajando?
PESO_STREAK         = 0.10   # partidos sin perder consecutivos


# =============================
# HELPERS
# =============================

def limitar(v, a, b):
    return max(a, min(v, b))


def normalizar_posicion(posicion):
    """Posición 1 → 1.0, posición 18 → 0.0"""
    return (TOTAL_EQUIPOS - posicion) / (TOTAL_EQUIPOS - 1)


def normalizar_tendencia(tendencia):
    """
    tendencia_posicion: positivo = subió, negativo = bajó.
    Normalizamos a [-1, 1] asumiendo máximo cambio razonable de ±6 lugares.
    """
    return limitar(tendencia / 6.0, -1.0, 1.0)


def normalizar_streak(streak):
    """
    imbatido_streak: partidos sin perder consecutivos.
    Cap en 10 para no sobreponderar rachas muy largas.
    """
    return limitar(streak / 10.0, 0.0, 1.0)


def normalizar_goles_favor(promedio):
    """
    goles_favor_promedio: típicamente entre 0.5 y 3.0 en Liga MX.
    Normalizamos con cap en 3.0.
    """
    return limitar(promedio / 3.0, 0.0, 1.0)


def normalizar_goles_contra(promedio):
    """
    goles_contra_promedio: menos goles recibidos = mejor.
    Invertimos: 0 goles recibidos → 1.0, 3+ → 0.0
    """
    return limitar(1.0 - (promedio / 3.0), 0.0, 1.0)


# =============================
# FUERZA
# =============================

def calcular_fuerza(equipo, es_local):
    """
    Calcula la fuerza de un equipo según su rol (local o visitante).
    Devuelve un score entre 0.0 y 1.0 aproximadamente.
    """

    # 1. Forma ponderada (ya viene calculada con pesos exponenciales del scrapper)
    forma = equipo["forma_ponderada"]  # ya está en [0, 1]

    # 2. Win rate situacional: local usa win_rate_local, visita usa win_rate_visita
    win_rate = equipo["win_rate_local"] if es_local else equipo["win_rate_visita"]

    # 3. Ofensiva y defensiva
    goles_favor = normalizar_goles_favor(equipo["goles_favor_promedio"])
    goles_contra = normalizar_goles_contra(equipo["goles_contra_promedio"])

    # 4. Posición en tabla
    posicion = normalizar_posicion(equipo["posicion"])

    # 5. Tendencia (¿sube o baja en la tabla?)
    tendencia = normalizar_tendencia(equipo["tendencia_posicion"])
    # Convertir de [-1,1] a [0,1] para que sea aditivo sin sesgo negativo
    tendencia_norm = (tendencia + 1.0) / 2.0

    # 6. Racha sin perder
    streak = normalizar_streak(equipo["imbatido_streak"])

    fuerza = (
        forma        * PESO_FORMA       +
        win_rate     * PESO_WINRATE     +
        goles_favor  * PESO_GOLES_FAVOR +
        goles_contra * PESO_GOLES_CONTRA +
        posicion     * PESO_POSICION    +
        tendencia_norm * PESO_TENDENCIA +
        streak       * PESO_STREAK
    )

    return fuerza


# =============================
# EMPATE DINÁMICO
# =============================

def calcular_prob_empate(f_local, f_visitante):
    """
    El empate es más probable cuando los equipos están parejos.
    Usamos la diferencia de fuerzas para modular la prob de empate
    en un rango [0.10, 0.28].
    """
    diferencia = abs(f_local - f_visitante)
    # A diferencia 0 → empate alto (0.28), a diferencia grande → empate bajo (0.10)
    # Mapeamos diferencia [0, 0.4+] a empate [0.28, 0.10]
    prob_empate = 0.28 - (diferencia / 0.40) * 0.18
    return limitar(prob_empate, 0.10, 0.28)


# =============================
# PROBABILIDADES
# =============================

def predecir_probabilidades(equipo_local, equipo_visitante):

    f_local     = calcular_fuerza(equipo_local, es_local=True)
    f_visitante = calcular_fuerza(equipo_visitante, es_local=False)

    # ---- Logística sobre la diferencia de fuerzas ----
    score = f_local - f_visitante
    prob_local     = 1 / (1 + math.exp(-K_LOGISTICO * score))
    prob_visitante = 1 - prob_local

    # ---- Cap de favorito ----
    if prob_local > MAX_FAVORITO:
        prob_local     = MAX_FAVORITO
        prob_visitante = 1 - prob_local

    if prob_visitante > MAX_FAVORITO:
        prob_visitante = MAX_FAVORITO
        prob_local     = 1 - prob_visitante

    # ---- Empate dinámico ----
    prob_empate = calcular_prob_empate(f_local, f_visitante)

    # Ajustar local y visitante para hacer espacio al empate
    ajuste = 1 - (prob_empate * 0.30)
    prob_local     *= ajuste
    prob_visitante *= ajuste

    # ---- Normalizar para que sumen 1.0 ----
    suma = prob_local + prob_visitante + prob_empate
    prob_local     /= suma
    prob_visitante /= suma
    prob_empate    /= suma

    # ---- Confianza ----
    gap = abs(prob_local - prob_visitante)
    if gap < 0.08:
        confianza = "ajustado"
    elif gap < 0.18:
        confianza = "moderado"
    else:
        confianza = "favorable"

    diferencia = abs(score)

    return {
        "local":             prob_local,
        "empate":            prob_empate,
        "visitante":         prob_visitante,
        "fuerza_local":      f_local,
        "fuerza_visitante":  f_visitante,
        "diferencia":        diferencia,
        "confianza":         confianza,
    }


# =============================
# RAZONES EXPLICABLES
# =============================

def generar_razones(local, visitante, resultado):
    """
    Genera bullet points explicando por qué el modelo favoreció a un equipo.
    """
    razones = []

    # Forma reciente
    if local["forma_ponderada"] > visitante["forma_ponderada"] + 0.10:
        razones.append(
            f"✅ {local['nombre']} llega con mejor forma reciente "
            f"({local['forma_ponderada']:.2f} vs {visitante['forma_ponderada']:.2f})"
        )
    elif visitante["forma_ponderada"] > local["forma_ponderada"] + 0.10:
        razones.append(
            f"⚠️ {visitante['nombre']} llega con mejor forma reciente "
            f"({visitante['forma_ponderada']:.2f} vs {local['forma_ponderada']:.2f})"
        )

    # Win rate situacional
    if local["win_rate_local"] >= 0.55:
        razones.append(
            f"✅ {local['nombre']} es sólido en casa "
            f"(gana el {local['win_rate_local']*100:.0f}% de sus partidos como local)"
        )
    elif local["win_rate_local"] <= 0.25:
        razones.append(
            f"⚠️ {local['nombre']} es débil como local "
            f"(solo {local['win_rate_local']*100:.0f}% de victorias en casa)"
        )

    if visitante["win_rate_visita"] <= 0.25:
        razones.append(
            f"⚠️ {visitante['nombre']} no rinde bien de visita "
            f"({visitante['win_rate_visita']*100:.0f}% de victorias fuera)"
        )
    elif visitante["win_rate_visita"] >= 0.50:
        razones.append(
            f"✅ {visitante['nombre']} es peligroso de visita "
            f"({visitante['win_rate_visita']*100:.0f}% de victorias fuera)"
        )

    # Racha sin perder
    if local["imbatido_streak"] >= 4:
        razones.append(
            f"✅ {local['nombre']} lleva {local['imbatido_streak']} partidos sin perder"
        )
    if visitante["imbatido_streak"] >= 4:
        razones.append(
            f"✅ {visitante['nombre']} lleva {visitante['imbatido_streak']} partidos sin perder"
        )

    # Goles a favor/contra
    if local["goles_favor_promedio"] > visitante["goles_favor_promedio"] + 0.5:
        razones.append(
            f"✅ {local['nombre']} anota más por partido "
            f"({local['goles_favor_promedio']:.2f} vs {visitante['goles_favor_promedio']:.2f})"
        )
    elif visitante["goles_favor_promedio"] > local["goles_favor_promedio"] + 0.5:
        razones.append(
            f"⚠️ {visitante['nombre']} anota más por partido "
            f"({visitante['goles_favor_promedio']:.2f} vs {local['goles_favor_promedio']:.2f})"
        )

    # Tendencia en tabla
    if local["tendencia_posicion"] > 2:
        razones.append(f"✅ {local['nombre']} está subiendo en la tabla")
    elif local["tendencia_posicion"] < -2:
        razones.append(f"⚠️ {local['nombre']} está bajando en la tabla")

    if visitante["tendencia_posicion"] > 2:
        razones.append(f"✅ {visitante['nombre']} está subiendo en la tabla")
    elif visitante["tendencia_posicion"] < -2:
        razones.append(f"⚠️ {visitante['nombre']} está bajando en la tabla")

    # Posición en tabla
    diff_pos = visitante["posicion"] - local["posicion"]
    if diff_pos >= 5:
        razones.append(
            f"✅ {local['nombre']} está {diff_pos} lugares arriba en la tabla"
        )
    elif diff_pos <= -5:
        razones.append(
            f"⚠️ {visitante['nombre']} está {abs(diff_pos)} lugares arriba en la tabla"
        )

    # Si no hay razones claras → partido parejo
    if not razones:
        razones.append("⚖️ Partido muy parejo, no hay ventaja clara para ningún equipo")

    return razones


# =============================
# GUARDAR
# =============================

def guardar_resultado(partido, archivo="partidos.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    data.append(partido)

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================
# GENERAR PARTIDO
# =============================

def generar_partido(id, local_nombre, visitante_nombre, db):

    local     = obtener_equipo(local_nombre, db)
    visitante = obtener_equipo(visitante_nombre, db)

    if not local or not visitante:
        raise ValueError(
            f"❌ Equipo no encontrado: "
            f"{'local' if not local else 'visitante'}"
        )

    resultado = predecir_probabilidades(local, visitante)

    # Predicción ganadora
    if (resultado["local"] > resultado["visitante"]
            and resultado["local"] > resultado["empate"]):
        pred = local["nombre"]
    elif (resultado["visitante"] > resultado["local"]
            and resultado["visitante"] > resultado["empate"]):
        pred = visitante["nombre"]
    else:
        pred = "Empate"

    razones = generar_razones(local, visitante, resultado)

    output = {
        "id":               id,
        "local":            local["nombre"],
        "visitante":        visitante["nombre"],
        "logo_local":       local.get("escudo"),
        "logo_visitante":   visitante.get("escudo"),
        "prob_local":       resultado["local"],
        "prob_empate":      resultado["empate"],
        "prob_visitante":   resultado["visitante"],
        "fuerza_local":     resultado["fuerza_local"],
        "fuerza_visitante": resultado["fuerza_visitante"],
        "diferencia":       resultado["diferencia"],
        "confianza":        resultado["confianza"],
        "prediccion":       pred,
        "razones":          razones,
    }

    guardar_resultado(output)
    return output


# =============================
# TEST
# =============================

if __name__ == "__main__":

    db = cargar_equipos()

    partido = generar_partido(
        9,
        "Cruz Azul",
        "Necaxa",
        db
    )

    print(json.dumps(partido, indent=2, ensure_ascii=False))
    print("\n✅ Partido generado y guardado en partidos.json")
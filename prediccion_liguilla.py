import json
import math
import os


# =============================
# CARGAR DATOS
# =============================

def cargar_equipos():
    ruta = os.path.join("scrapper", "equipos.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_h2h():
    ruta = os.path.join("scrapper", "h2h_liguilla.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_equipo(nombre, db):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    key = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        key = key.replace(a, b)
    return db.get(key)


# =============================
# CONFIG BASE
# =============================

TOTAL_EQUIPOS     = 18
K_LOGISTICO       = 4.2
MAX_FAVORITO      = 0.68

PESO_FORMA        = 0.30
PESO_WINRATE      = 0.22
PESO_GOLES_FAVOR  = 0.12
PESO_GOLES_CONTRA = 0.12
PESO_POSICION     = 0.08
PESO_TENDENCIA    = 0.06
PESO_STREAK       = 0.10

PESO_BASE         = 0.65
PESO_H2H          = 0.20
PESO_EXPERIENCIA  = 0.10
PESO_VUELTA_CASA  = 0.05


# =============================
# EXPERIENCIA EN LIGUILLA
# Actualizar cada torneo
# =============================

EXPERIENCIA_LIGUILLA = {
    "america":     0.94,
    "toluca":      0.81,
    "cruzazul":    0.75,
    "tigres":      0.69,
    "tigresuanl":  0.69,
    "guadalajara": 0.44,
    "pumasunam":   0.31,
    "pachuca":     0.28,
    "atlas":       0.13,
}


# =============================
# HELPERS
# =============================

def limitar(v, a, b):
    return max(a, min(v, b))

def normalizar_nombre(nombre):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n

def normalizar_posicion(posicion):
    return (TOTAL_EQUIPOS - posicion) / (TOTAL_EQUIPOS - 1)

def normalizar_tendencia(tendencia):
    return limitar(tendencia / 6.0, -1.0, 1.0)

def normalizar_streak(streak):
    return limitar(streak / 10.0, 0.0, 1.0)

def normalizar_goles_favor(promedio):
    return limitar(promedio / 3.0, 0.0, 1.0)

def normalizar_goles_contra(promedio):
    return limitar(1.0 - (promedio / 3.0), 0.0, 1.0)


# =============================
# FUERZA BASE
# =============================

def calcular_fuerza_base(equipo, es_local):
    forma          = equipo["forma_ponderada"]
    win_rate       = equipo["win_rate_local"] if es_local else equipo["win_rate_visita"]
    goles_favor    = normalizar_goles_favor(equipo["goles_favor_promedio"])
    goles_contra   = normalizar_goles_contra(equipo["goles_contra_promedio"])
    posicion       = normalizar_posicion(equipo["posicion"])
    tendencia      = normalizar_tendencia(equipo["tendencia_posicion"])
    tendencia_norm = (tendencia + 1.0) / 2.0
    streak         = normalizar_streak(equipo["imbatido_streak"])

    return (
        forma          * PESO_FORMA        +
        win_rate       * PESO_WINRATE      +
        goles_favor    * PESO_GOLES_FAVOR  +
        goles_contra   * PESO_GOLES_CONTRA +
        posicion       * PESO_POSICION     +
        tendencia_norm * PESO_TENDENCIA    +
        streak         * PESO_STREAK
    )


# =============================
# H2H SCORE
# =============================

def calcular_h2h_score(nombre_local, nombre_visitante, h2h_data):
    nl = normalizar_nombre(nombre_local)
    nv = normalizar_nombre(nombre_visitante)

    cruce = None
    for key, val in h2h_data.items():
        ea = normalizar_nombre(val["equipo_a"])
        eb = normalizar_nombre(val["equipo_b"])
        if (ea == nl and eb == nv) or (ea == nv and eb == nl):
            cruce = val
            break

    if not cruce:
        return 0.5, 0, 0

    def win_rate_para(partidos, ref):
        if not partidos:
            return None, 0
        victorias = 0
        for p in partidos:
            gl = p["goles_local"]
            gv = p["goles_visitante"]
            es_local_ref = normalizar_nombre(p["local"]) == normalizar_nombre(ref)
            if gl == gv:
                continue
            gano_local = gl > gv
            if (es_local_ref and gano_local) or (not es_local_ref and not gano_local):
                victorias += 1
        return victorias / len(partidos), len(partidos)

    wr_c, n_c = win_rate_para(cruce["clausura_2026"], nombre_local)
    wr_a, n_a = win_rate_para(cruce["apertura_2025"], nombre_local)
    total      = n_c + n_a

    if total == 0:
        return 0.5, 0, 0

    if wr_c is None:
        score = wr_a
    elif wr_a is None:
        score = wr_c
    else:
        score = (wr_c * 0.60) + (wr_a * 0.40)

    return limitar(score, 0.0, 1.0), n_c, n_a


# =============================
# EXPERIENCIA
# =============================

def get_experiencia(nombre):
    key = normalizar_nombre(nombre)
    if key in EXPERIENCIA_LIGUILLA:
        return EXPERIENCIA_LIGUILLA[key]
    for k, v in EXPERIENCIA_LIGUILLA.items():
        if k in key or key in k:
            return v
    return 0.50


# =============================
# VUELTA EN CASA
# =============================

def quien_juega_vuelta_en_casa(local, visitante):
    if local["posicion"] <= visitante["posicion"]:
        return "local"
    return "visitante"


# =============================
# EMPATE DINAMICO
# =============================

def calcular_prob_empate(f_local, f_visitante):
    diferencia  = abs(f_local - f_visitante)
    prob_empate = 0.28 - (diferencia / 0.40) * 0.18
    return limitar(prob_empate, 0.10, 0.28)


# =============================
# PROBABILIDADES LIGUILLA
# =============================

def predecir_probabilidades_liguilla(equipo_local, equipo_visitante, h2h_data, nombre_local, nombre_visitante):

    fb_local     = calcular_fuerza_base(equipo_local,     es_local=True)
    fb_visitante = calcular_fuerza_base(equipo_visitante, es_local=False)

    h2h_local, n_c, n_a = calcular_h2h_score(nombre_local, nombre_visitante, h2h_data)
    h2h_visitante        = 1.0 - h2h_local

    exp_local     = get_experiencia(nombre_local)
    exp_visitante = get_experiencia(nombre_visitante)

    vuelta       = quien_juega_vuelta_en_casa(equipo_local, equipo_visitante)
    vuelta_local = 1.0 if vuelta == "local" else 0.0
    vuelta_visit = 1.0 - vuelta_local

    f_local = (
        fb_local     * PESO_BASE        +
        h2h_local    * PESO_H2H         +
        exp_local    * PESO_EXPERIENCIA +
        vuelta_local * PESO_VUELTA_CASA
    )
    f_visitante = (
        fb_visitante  * PESO_BASE        +
        h2h_visitante * PESO_H2H         +
        exp_visitante * PESO_EXPERIENCIA +
        vuelta_visit  * PESO_VUELTA_CASA
    )

    score          = f_local - f_visitante
    prob_local     = 1 / (1 + math.exp(-K_LOGISTICO * score))
    prob_visitante = 1 - prob_local

    if prob_local > MAX_FAVORITO:
        prob_local     = MAX_FAVORITO
        prob_visitante = 1 - prob_local
    if prob_visitante > MAX_FAVORITO:
        prob_visitante = MAX_FAVORITO
        prob_local     = 1 - prob_visitante

    prob_empate    = calcular_prob_empate(f_local, f_visitante)
    ajuste         = 1 - (prob_empate * 0.30)
    prob_local    *= ajuste
    prob_visitante *= ajuste

    suma           = prob_local + prob_visitante + prob_empate
    prob_local    /= suma
    prob_visitante /= suma
    prob_empate   /= suma

    gap = abs(prob_local - prob_visitante)
    if gap < 0.08:
        confianza = "ajustado"
    elif gap < 0.18:
        confianza = "moderado"
    else:
        confianza = "favorable"

    return {
        "local":            prob_local,
        "empate":           prob_empate,
        "visitante":        prob_visitante,
        "fuerza_local":     f_local,
        "fuerza_visitante": f_visitante,
        "diferencia":       abs(score),
        "confianza":        confianza,
        "h2h_local":        h2h_local,
        "n_h2h_clausura":   n_c,
        "n_h2h_apertura":   n_a,
        "vuelta_en_casa":   vuelta,
        "exp_local":        exp_local,
        "exp_visitante":    exp_visitante,
    }


# =============================
# RAZONES POR EQUIPO
# Siempre al menos 1 pro y 1 contra por equipo
# =============================

def generar_razones(local, visitante, resultado, nombre_local, nombre_visitante):
    """
    Devuelve un dict con pros y contras separados por equipo.
    Garantiza al menos 1 pro y 1 contra para cada uno.
    Tono analítico y periodístico, sin emojis ni lenguaje de apuestas.
    """

    pros_local    = []
    contras_local = []
    pros_visit    = []
    contras_visit = []

    # ── FORMA RECIENTE ──────────────────────────────
    fl = local["forma_ponderada"]
    fv = visitante["forma_ponderada"]

    if fl >= 0.60:
        pros_local.append(f"Momentum positivo: {round(fl * 5, 1)} de 5 puntos posibles en los últimos 5 partidos")
    elif fl <= 0.35:
        contras_local.append(f"Racha irregular: solo {round(fl * 5, 1)} de 5 puntos posibles en los últimos 5 partidos")

    if fv >= 0.60:
        pros_visit.append(f"Momentum positivo: {round(fv * 5, 1)} de 5 puntos posibles en los últimos 5 partidos")
    elif fv <= 0.35:
        contras_visit.append(f"Racha irregular: solo {round(fv * 5, 1)} de 5 puntos posibles en los últimos 5 partidos")

    # ── WIN RATE SITUACIONAL ─────────────────────────
    wrl = local["win_rate_local"]
    wrv = visitante["win_rate_visita"]

    if wrl >= 0.55:
        pros_local.append(f"Dominio en casa: {wrl*100:.0f}% de victorias como local en el torneo")
    elif wrl <= 0.30:
        contras_local.append(f"Bajo rendimiento en casa: {wrl*100:.0f}% de victorias como local")

    if wrv >= 0.50:
        pros_visit.append(f"Efectivo de visita: {wrv*100:.0f}% de victorias fuera de casa en el torneo")
    elif wrv <= 0.25:
        contras_visit.append(f"Rendimiento exterior limitado: {wrv*100:.0f}% de victorias como visitante")

    # ── CAPACIDAD GOLEADORA ──────────────────────────
    gfl = local["goles_favor_promedio"]
    gfv = visitante["goles_favor_promedio"]
    gcl = local["goles_contra_promedio"]
    gcv = visitante["goles_contra_promedio"]

    if gfl >= 1.8:
        pros_local.append(f"Potencia ofensiva: {gfl:.2f} goles por partido a favor")
    elif gfl <= 1.1:
        contras_local.append(f"Producción ofensiva limitada: {gfl:.2f} goles por partido")

    if gfv >= 1.8:
        pros_visit.append(f"Potencia ofensiva: {gfv:.2f} goles por partido a favor")
    elif gfv <= 1.1:
        contras_visit.append(f"Producción ofensiva limitada: {gfv:.2f} goles por partido")

    # ── SOLIDEZ DEFENSIVA ────────────────────────────
    if gcl <= 1.0:
        pros_local.append(f"Solidez defensiva: {gcl:.2f} goles recibidos por partido")
    elif gcl >= 1.8:
        contras_local.append(f"Vulnerabilidad defensiva: {gcl:.2f} goles recibidos por partido")

    if gcv <= 1.0:
        pros_visit.append(f"Solidez defensiva: {gcv:.2f} goles recibidos por partido")
    elif gcv >= 1.8:
        contras_visit.append(f"Vulnerabilidad defensiva: {gcv:.2f} goles recibidos por partido")

    # ── RACHA SIN PERDER ────────────────────────────
    sl = local["imbatido_streak"]
    sv = visitante["imbatido_streak"]

    if sl >= 4:
        pros_local.append(f"Racha de invicto: {sl} partidos consecutivos sin perder")
    elif sl == 0:
        contras_local.append("Sin racha de invicto activa al inicio de la serie")

    if sv >= 4:
        pros_visit.append(f"Racha de invicto: {sv} partidos consecutivos sin perder")
    elif sv == 0:
        contras_visit.append("Sin racha de invicto activa al inicio de la serie")

    # ── H2H ─────────────────────────────────────────
    n_total = resultado["n_h2h_clausura"] + resultado["n_h2h_apertura"]
    if n_total > 0:
        h2h = resultado["h2h_local"]
        if h2h >= 0.60:
            pros_local.append(f"Ventaja histórica en este cruce: {h2h*100:.0f}% de victorias en {n_total} enfrentamientos recientes")
            contras_visit.append(f"Historial desfavorable en este cruce: {(1-h2h)*100:.0f}% de victorias en {n_total} enfrentamientos recientes")
        elif h2h <= 0.40:
            pros_visit.append(f"Ventaja histórica en este cruce: {(1-h2h)*100:.0f}% de victorias en {n_total} enfrentamientos recientes")
            contras_local.append(f"Historial desfavorable en este cruce: {h2h*100:.0f}% de victorias en {n_total} enfrentamientos recientes")
        else:
            pros_local.append(f"Historial equilibrado: {n_total} enfrentamientos recientes sin dominancia clara")
            pros_visit.append(f"Historial equilibrado: {n_total} enfrentamientos recientes sin dominancia clara")

    # ── EXPERIENCIA EN LIGUILLA ──────────────────────
    exp_l = resultado["exp_local"]
    exp_v = resultado["exp_visitante"]
    diff_exp = exp_l - exp_v

    if diff_exp >= 0.25:
        pros_local.append(f"Mayor experiencia en instancias eliminatorias (índice {exp_l:.2f} vs {exp_v:.2f})")
        contras_visit.append(f"Menor historial en rondas eliminatorias (índice {exp_v:.2f} vs {exp_l:.2f})")
    elif diff_exp <= -0.25:
        pros_visit.append(f"Mayor experiencia en instancias eliminatorias (índice {exp_v:.2f} vs {exp_l:.2f})")
        contras_local.append(f"Menor historial en rondas eliminatorias (índice {exp_l:.2f} vs {exp_v:.2f})")

    # ── VUELTA EN CASA ───────────────────────────────
    vuelta = resultado["vuelta_en_casa"]
    if vuelta == "local":
        pros_local.append("Ventaja táctica: disputa el partido de vuelta en condición de local")
        contras_visit.append("Deberá resolver la serie jugando la vuelta como visitante")
    else:
        pros_visit.append("Ventaja táctica: disputa el partido de vuelta en condición de local")
        contras_local.append("Deberá resolver la serie jugando la vuelta como visitante")

    # ── POSICIÓN EN TABLA ────────────────────────────
    diff_pos = visitante["posicion"] - local["posicion"]
    if diff_pos >= 3:
        pros_local.append(f"Mejor posición en tabla: {diff_pos} lugares por encima del rival al cierre del torneo")
    elif diff_pos <= -3:
        pros_visit.append(f"Mejor posición en tabla: {abs(diff_pos)} lugares por encima del rival al cierre del torneo")
    elif diff_pos > 0:
        contras_visit.append(f"Cierra el torneo {diff_pos} posiciones por debajo del rival en la tabla")
    elif diff_pos < 0:
        contras_local.append(f"Cierra el torneo {abs(diff_pos)} posiciones por debajo del rival en la tabla")

    # ── GARANTÍA: mínimo 1 pro y 1 contra por equipo ─

    # Si no hay pros para local → tomar el mejor dato disponible
    if not pros_local:
        pros_local.append(f"Clasificó entre los mejores ocho equipos del torneo con {local.get('puntos', 'N/A')} puntos")

    # Si no hay contras para local → señalar la presión eliminatoria
    if not contras_local:
        contras_local.append("La condición eliminatoria exige un nivel de consistencia superior al de la fase regular")

    # Si no hay pros para visitante
    if not pros_visit:
        pros_visit.append(f"Clasificó entre los mejores ocho equipos del torneo con {visitante.get('puntos', 'N/A')} puntos")

    # Si no hay contras para visitante
    if not contras_visit:
        contras_visit.append("La condición eliminatoria exige un nivel de consistencia superior al de la fase regular")

    return {
        "local": {
            "pros":    pros_local,
            "contras": contras_local,
        },
        "visitante": {
            "pros":    pros_visit,
            "contras": contras_visit,
        }
    }


# =============================
# GUARDAR
# =============================

def guardar_resultado(partido, archivo="partidos_liguilla.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append(partido)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================
# GENERAR PARTIDO IDA
# =============================

def generar_partido_ida(id, local_nombre, visitante_nombre, db, h2h):

    local     = obtener_equipo(local_nombre, db)
    visitante = obtener_equipo(visitante_nombre, db)

    if not local or not visitante:
        raise ValueError(f"Equipo no encontrado: {'local' if not local else 'visitante'}")

    resultado = predecir_probabilidades_liguilla(
        local, visitante, h2h, local_nombre, visitante_nombre
    )

    if resultado["local"] > resultado["visitante"] and resultado["local"] > resultado["empate"]:
        pred = local["nombre"]
    elif resultado["visitante"] > resultado["local"] and resultado["visitante"] > resultado["empate"]:
        pred = visitante["nombre"]
    else:
        pred = "Empate"

    razones = generar_razones(local, visitante, resultado, local_nombre, visitante_nombre)

    output = {
        "id":               id,
        "fase":             "liguilla_ida",
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
        "vuelta_en_casa":   resultado["vuelta_en_casa"],
        "razones":          razones,
    }

    guardar_resultado(output)
    return output


# =============================
# TEST
# =============================

if __name__ == "__main__":
    db  = cargar_equipos()
    h2h = cargar_h2h()

    partido = generar_partido_ida(1, "Atlas", "Cruz Azul", db, h2h)
    print(json.dumps(partido, indent=2, ensure_ascii=False))
    print("\nPartido de ida generado y guardado en partidos_liguilla.json")

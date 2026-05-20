import json
import math
import os


# =============================
# CARGAR DATOS
# =============================

def cargar_equipos():
    ruta = os.path.join("scrapper", "LIGA-MX", "equipos.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_h2h():
    ruta = os.path.join("scrapper", "LIGA-MX", "h2h_liguilla.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_equipo(nombre, db):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    key = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        key = key.replace(a, b)
    return db.get(key)


# =============================
# ADAPTADOR DE FORMATO
# =============================

LIGA_KEY = "mex.1"

def adaptar_equipo(equipo_raw):
    """
    Convierte el nuevo formato de equipos.json (con sub-objeto `competencias`)
    al formato plano que usa internamente el modelo.
    Usa los datos de la liga principal (mex.1) para todos los cálculos
    situacionales y de rendimiento; los campos de raíz para posición y metadata.
    """
    liga = equipo_raw.get("competencias", {}).get(LIGA_KEY, {})

    return {
        # — Metadata —
        "nombre":  equipo_raw.get("nombre", ""),
        "escudo":  equipo_raw.get("escudo", ""),

        # — Posición en tabla (raíz, refleja el torneo actual) —
        "posicion":           equipo_raw.get("posicion", 9),
        "tendencia_posicion": equipo_raw.get("tendencia_posicion", 0),

        # — Forma y racha (raíz, ya calculada por el scraper) —
        "forma_ponderada": equipo_raw.get("forma_liga", equipo_raw.get("forma_combinada", 0.5)),
        "imbatido_streak": equipo_raw.get("imbatido_streak", 0),
        "ultimos_5":       equipo_raw.get("ultimos_5_liga", []),

        # — Rendimiento situacional (liga) —
        "win_rate_local":  liga.get("win_rate_local",  0.0),
        "win_rate_visita": liga.get("win_rate_visita", 0.0),

        # — Goles (liga) —
        "goles_favor_promedio":  liga.get("goles_favor_promedio",  0.0),
        "goles_contra_promedio": liga.get("goles_contra_promedio", 0.0),

        # — Totales de partido (liga) —
        "partidos":  liga.get("partidos",  0),
        "ganados":   liga.get("ganados",   0),
        "empatados": liga.get("empatados", 0),
        "perdidos":  liga.get("perdidos",  0),

        # — Desglose local (liga) —
        "partidos_local":  liga.get("partidos_local",  0),
        "ganados_local":   liga.get("ganados_local",   0),
        "empatados_local": liga.get("empatados_local", 0),
        "perdidos_local":  liga.get("perdidos_local",  0),

        # — Desglose visita (liga) —
        "partidos_visita":  liga.get("partidos_visita",  0),
        "ganados_visita":   liga.get("ganados_visita",   0),
        "empatados_visita": liga.get("empatados_visita", 0),
        "perdidos_visita":  liga.get("perdidos_visita",  0),
    }


# =============================
# CONFIG
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

PESO_EMPATE_BASE      = 0.20
PESO_EMPATE_HISTORICO = 0.65
PESO_EMPATE_MOMENTUM  = 0.15

URGENCIA_ALTA     = 0.18
URGENCIA_MEDIA    = 0.10
URGENCIA_NULA     = 0.00

EMPATE_BOOST_URGENCIA_ALTA  = 0.05
EMPATE_BOOST_URGENCIA_MEDIA = 0.02

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

def contar_empates_recientes(ultimos_5):
    return ultimos_5.count("D")

def calcular_tasa_empate(equipo, es_local):
    if es_local:
        partidos  = equipo.get("partidos_local", 0)
        empatados = equipo.get("empatados_local", 0)
    else:
        partidos  = equipo.get("partidos_visita", 0)
        empatados = equipo.get("empatados_visita", 0)

    if partidos == 0:
        return 0.25

    return limitar(empatados / partidos, 0.0, 1.0)


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
# H2H
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
        return 0.5, 0, 0, []

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
        return 0.5, 0, 0, []

    if wr_c is None:
        score = wr_a
    elif wr_a is None:
        score = wr_c
    else:
        score = (wr_c * 0.60) + (wr_a * 0.40)

    partidos_recientes = (cruce["clausura_2026"] + cruce["apertura_2025"])[:5]

    return limitar(score, 0.0, 1.0), n_c, n_a, partidos_recientes


def contar_resultados_h2h(partidos_h2h, nombre_local, nombre_visitante):
    wins_local   = 0
    wins_visita  = 0
    empates      = 0

    for p in partidos_h2h:
        gl = p["goles_local"]
        gv = p["goles_visitante"]
        local_en_partido = normalizar_nombre(p["local"]) == normalizar_nombre(nombre_local)

        if gl == gv:
            empates += 1
        elif gl > gv:
            if local_en_partido:
                wins_local += 1
            else:
                wins_visita += 1
        else:
            if local_en_partido:
                wins_visita += 1
            else:
                wins_local += 1

    return wins_local, empates, wins_visita


def get_experiencia(nombre):
    key = normalizar_nombre(nombre)
    if key in EXPERIENCIA_LIGUILLA:
        return EXPERIENCIA_LIGUILLA[key]
    for k, v in EXPERIENCIA_LIGUILLA.items():
        if k in key or key in k:
            return v
    return 0.50


def calcular_prob_empate(f_local, f_visitante, equipo_local, equipo_visitante, urgencia_local="nula", urgencia_visitante="nula"):
    diferencia = abs(f_local - f_visitante)
    base = limitar(0.28 - (diferencia / 0.40) * 0.18, 0.10, 0.28)

    tasa_local     = calcular_tasa_empate(equipo_local,     es_local=True)
    tasa_visitante = calcular_tasa_empate(equipo_visitante, es_local=False)
    historico = max(tasa_local, tasa_visitante)

    d_local     = contar_empates_recientes(equipo_local.get("ultimos_5", []))
    d_visitante = contar_empates_recientes(equipo_visitante.get("ultimos_5", []))
    momentum    = limitar((d_local + d_visitante) * 0.07, 0.0, 0.35)

    prob_empate = (
        base      * PESO_EMPATE_BASE      +
        historico * PESO_EMPATE_HISTORICO +
        momentum  * PESO_EMPATE_MOMENTUM
    )

    if urgencia_local == "alta" or urgencia_visitante == "alta":
        prob_empate += EMPATE_BOOST_URGENCIA_ALTA
    elif urgencia_local == "media" or urgencia_visitante == "media":
        prob_empate += EMPATE_BOOST_URGENCIA_MEDIA

    return limitar(prob_empate, 0.08, 0.46)


# =============================
# CONTEXTO DE VUELTA
# =============================

def calcular_contexto_vuelta(
    goles_ida_local,
    goles_ida_visitante,
    tabla_local,
    tabla_visitante,
):
    goles_vuelta_local_en_ida     = goles_ida_visitante
    goles_vuelta_visitante_en_ida = goles_ida_local

    diferencia_global = goles_vuelta_local_en_ida - goles_vuelta_visitante_en_ida

    ventaja_tabla = "local"

    if diferencia_global > 0:
        estado_local             = "ganando_global"
        estado_visitante         = "perdiendo_global"
        goles_necesita_visitante = diferencia_global + 1
        goles_necesita_local     = 0
        clasifica_empate_local   = True
        clasifica_empate_visitante = False

    elif diferencia_global == 0:
        estado_local             = "global_empatado"
        estado_visitante         = "global_empatado"
        goles_necesita_visitante = 1
        goles_necesita_local     = 0
        clasifica_empate_local   = True
        clasifica_empate_visitante = False

    else:
        estado_local             = "perdiendo_global"
        estado_visitante         = "ganando_global"
        goles_necesita_local     = abs(diferencia_global) + 1
        goles_necesita_visitante = 0
        clasifica_empate_local   = False
        clasifica_empate_visitante = False

    def nivel_urgencia(goles_necesarios, clasifica_con_empate):
        if clasifica_con_empate:
            return "nula"
        elif goles_necesarios == 1:
            return "media"
        else:
            return "alta"

    urgencia_local     = nivel_urgencia(goles_necesita_local,    clasifica_empate_local)
    urgencia_visitante = nivel_urgencia(goles_necesita_visitante, clasifica_empate_visitante)

    return {
        "diferencia_global":              diferencia_global,
        "goles_vuelta_local_en_ida":      goles_vuelta_local_en_ida,
        "goles_vuelta_visitante_en_ida":  goles_vuelta_visitante_en_ida,
        "estado_local":                   estado_local,
        "estado_visitante":               estado_visitante,
        "goles_necesita_local":           goles_necesita_local,
        "goles_necesita_visitante":       goles_necesita_visitante,
        "clasifica_empate_local":         clasifica_empate_local,
        "clasifica_empate_visitante":     clasifica_empate_visitante,
        "urgencia_local":                 urgencia_local,
        "urgencia_visitante":             urgencia_visitante,
        "ventaja_tabla":                  ventaja_tabla,
    }


def ajuste_por_urgencia(urgencia):
    if urgencia == "alta":
        return URGENCIA_ALTA
    elif urgencia == "media":
        return URGENCIA_MEDIA
    else:
        return URGENCIA_NULA


# =============================
# PROBABILIDADES VUELTA
# =============================

def predecir_probabilidades_vuelta(
    equipo_local, equipo_visitante, h2h_data,
    nombre_local, nombre_visitante,
    contexto,
):
    fb_local     = calcular_fuerza_base(equipo_local,     es_local=True)
    fb_visitante = calcular_fuerza_base(equipo_visitante, es_local=False)

    h2h_local, n_c, n_a, partidos_h2h = calcular_h2h_score(
        nombre_local, nombre_visitante, h2h_data
    )
    h2h_visitante = 1.0 - h2h_local

    exp_local     = get_experiencia(nombre_local)
    exp_visitante = get_experiencia(nombre_visitante)

    vuelta_local = 1.0
    vuelta_visit = 0.0

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

    bonus_local     = ajuste_por_urgencia(contexto["urgencia_local"])
    bonus_visitante = ajuste_por_urgencia(contexto["urgencia_visitante"])

    f_local     = limitar(f_local     + bonus_local,     0.0, 1.0)
    f_visitante = limitar(f_visitante + bonus_visitante, 0.0, 1.0)

    score          = f_local - f_visitante
    prob_empate = calcular_prob_empate(
        f_local, f_visitante,
        equipo_local, equipo_visitante,
        urgencia_local=contexto["urgencia_local"],
        urgencia_visitante=contexto["urgencia_visitante"],
    )

    score_ratio_l  = 1 / (1 + math.exp(-K_LOGISTICO * score))
    score_ratio_v  = 1 - score_ratio_l
    restante       = 1.0 - prob_empate
    prob_local     = restante * score_ratio_l
    prob_visitante = restante * score_ratio_v

    if prob_local > MAX_FAVORITO:
        exceso         = prob_local - MAX_FAVORITO
        prob_local     = MAX_FAVORITO
        prob_visitante += exceso
    if prob_visitante > MAX_FAVORITO:
        exceso         = prob_visitante - MAX_FAVORITO
        prob_visitante = MAX_FAVORITO
        prob_local    += exceso

    suma           = prob_local + prob_visitante + prob_empate
    prob_local    /= suma
    prob_visitante /= suma
    prob_empate   /= suma

    gap = abs(prob_local - prob_visitante)
    confianza = "ajustado" if gap < 0.08 else "moderado" if gap < 0.18 else "favorable"

    return {
        "local":                    prob_local,
        "empate":                   prob_empate,
        "visitante":                prob_visitante,
        "fuerza_local":             f_local,
        "fuerza_visitante":         f_visitante,
        "diferencia":               abs(score),
        "confianza":                confianza,
        "h2h_local":                h2h_local,
        "n_h2h_clausura":           n_c,
        "n_h2h_apertura":           n_a,
        "partidos_h2h":             partidos_h2h,
        "exp_local":                exp_local,
        "exp_visitante":            exp_visitante,
        "fb_local":                 fb_local,
        "fb_visitante":             fb_visitante,
        "bonus_urgencia_local":     bonus_local,
        "bonus_urgencia_visitante": bonus_visitante,
    }


# =============================
# IMPACTO DE FACTOR
# =============================

def nivel_impacto(diferencia_normalizada):
    if diferencia_normalizada >= 0.25:
        return "alto"
    elif diferencia_normalizada >= 0.12:
        return "medio"
    else:
        return "bajo"


# =============================
# ANÁLISIS ESTRUCTURADO VUELTA
# =============================

def generar_analisis_vuelta(local, visitante, resultado, nombre_local, nombre_visitante, contexto):
    factores = []

    # ── 1. FORMA RECIENTE ───────────────────────────────────────────────────
    fl = local["forma_ponderada"]
    fv = visitante["forma_ponderada"]
    ul5_l  = local.get("ultimos_5", [])
    ul5_v  = visitante.get("ultimos_5", [])
    wins_l  = ul5_l.count("W")
    wins_v  = ul5_v.count("W")
    losses_l = ul5_l.count("L")
    losses_v = ul5_v.count("L")

    if fl > fv:
        if wins_l >= 4:
            interp = (f"{nombre_local} atraviesa su mejor racha del torneo: {wins_l} victorias "
                      f"en los últimos 5 partidos (índice {fl:.2f}/1.0). "
                      f"{nombre_visitante} muestra mayor irregularidad con {wins_v} victorias "
                      f"y {losses_v} derrotas en ese mismo período (índice {fv:.2f}/1.0).")
        else:
            interp = (f"{nombre_local} llega con mejor momentum reciente: índice de forma {fl:.2f}/1.0 "
                      f"frente a {fv:.2f}/1.0 de {nombre_visitante}. "
                      f"En los últimos 5 partidos, {nombre_local} acumula {wins_l} victorias "
                      f"contra {wins_v} del rival.")
    elif fv > fl:
        if wins_v >= 4:
            interp = (f"{nombre_visitante} llega en su mejor momento: {wins_v} victorias "
                      f"en los últimos 5 partidos (índice {fv:.2f}/1.0). "
                      f"{nombre_local} muestra irregularidad con {wins_l} victorias "
                      f"y {losses_l} derrotas recientes (índice {fl:.2f}/1.0).")
        else:
            interp = (f"{nombre_visitante} llega con mejor momentum: índice {fv:.2f}/1.0 "
                      f"frente a {fl:.2f}/1.0 de {nombre_local}. "
                      f"En los últimos 5 partidos, {nombre_visitante} acumula {wins_v} victorias "
                      f"contra {wins_l} del rival.")
    else:
        interp = (f"Ambos equipos llegan en condiciones similares: "
                  f"{nombre_local} con índice {fl:.2f}/1.0 y {nombre_visitante} con {fv:.2f}/1.0. "
                  f"Ninguno tiene ventaja clara en momentum reciente.")

    factores.append({
        "factor":         "Forma reciente",
        "impacto":        nivel_impacto(abs(fl - fv)),
        "tipo":           "forma",
        "local":          {"valor": round(fl, 2), "ultimos_5": ul5_l, "nombre": nombre_local},
        "visitante":      {"valor": round(fv, 2), "ultimos_5": ul5_v, "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 2. RENDIMIENTO SITUACIONAL ──────────────────────────────────────────
    wrl  = local["win_rate_local"]
    wrv  = visitante["win_rate_visita"]
    gl_l = local.get("ganados_local", 0)
    el_l = local.get("empatados_local", 0)
    pl_l = local.get("perdidos_local", 0)
    gv_v = visitante.get("ganados_visita", 0)
    ev_v = visitante.get("empatados_visita", 0)
    pv_v = visitante.get("perdidos_visita", 0)

    if wrl >= 0.55 and wrv <= 0.30:
        interp = (f"Contraste situacional marcado: {nombre_local} gana el {wrl*100:.0f}% "
                  f"de sus partidos en casa ({gl_l}G/{el_l}E/{pl_l}P como local), "
                  f"mientras {nombre_visitante} apenas convierte el {wrv*100:.0f}% de visita "
                  f"({gv_v}G/{ev_v}E/{pv_v}P como visitante). "
                  f"La localía es un factor determinante en este cruce.")
    elif wrl >= 0.55:
        interp = (f"{nombre_local} es dominante en casa: {wrl*100:.0f}% de victorias "
                  f"({gl_l}G/{el_l}E/{pl_l}P). {nombre_visitante} ha respondido con "
                  f"{wrv*100:.0f}% de efectividad como visitante ({gv_v}G/{ev_v}E/{pv_v}P).")
    elif wrv <= 0.30:
        interp = (f"{nombre_visitante} tiene dificultades fuera de casa: solo {wrv*100:.0f}% "
                  f"de victorias como visitante ({gv_v}G/{ev_v}E/{pv_v}P). "
                  f"{nombre_local} ha aprovechado su condición local ganando el {wrl*100:.0f}% "
                  f"de sus partidos en casa ({gl_l}G/{el_l}E/{pl_l}P).")
    else:
        interp = (f"Rendimiento situacional equilibrado: {nombre_local} gana el {wrl*100:.0f}% "
                  f"en casa ({gl_l}G/{el_l}E/{pl_l}P) y {nombre_visitante} el {wrv*100:.0f}% "
                  f"de visita ({gv_v}G/{ev_v}E/{pv_v}P). "
                  f"Ninguno tiene ventaja situacional clara.")

    factores.append({
        "factor":    "Rendimiento situacional",
        "impacto":   nivel_impacto(abs(wrl - wrv)),
        "tipo":      "barras",
        "local":     {"etiqueta": "Win rate local",  "valor": round(wrl, 2),
                      "detalle": f"{gl_l}G / {el_l}E / {pl_l}P", "nombre": nombre_local},
        "visitante": {"etiqueta": "Win rate visita", "valor": round(wrv, 2),
                      "detalle": f"{gv_v}G / {ev_v}E / {pv_v}P", "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 3. POTENCIAL OFENSIVO Y DEFENSIVO ───────────────────────────────────
    gf_l = local["goles_favor_promedio"]
    gc_l = local["goles_contra_promedio"]
    gf_v = visitante["goles_favor_promedio"]
    gc_v = visitante["goles_contra_promedio"]

    ventaja_of  = gf_l - gf_v
    ventaja_def = gc_v - gc_l

    if ventaja_of >= 0.4 and ventaja_def >= 0.3:
        interp = (f"Superioridad ofensiva y defensiva de {nombre_local}: anota {gf_l:.2f} goles "
                  f"por partido frente a {gf_v:.2f} del rival, y recibe {gc_l:.2f} frente "
                  f"a {gc_v:.2f} de {nombre_visitante}. Dominio integral en ambas fases.")
    elif ventaja_of >= 0.4:
        interp = (f"{nombre_local} tiene mayor potencia ofensiva: {gf_l:.2f} goles por partido "
                  f"contra {gf_v:.2f} de {nombre_visitante}. En defensa la diferencia es menor: "
                  f"{gc_l:.2f} recibidos por partido frente a {gc_v:.2f}.")
    elif ventaja_of <= -0.4:
        interp = (f"{nombre_visitante} genera más peligro ofensivo: {gf_v:.2f} goles por partido "
                  f"frente a {gf_l:.2f} de {nombre_local}. "
                  f"En defensa, {nombre_local} recibe {gc_l:.2f} goles por partido "
                  f"y {nombre_visitante} {gc_v:.2f}.")
    else:
        interp = (f"Producción ofensiva similar: {nombre_local} promedia {gf_l:.2f} goles "
                  f"por partido y {nombre_visitante} {gf_v:.2f}. En defensa, "
                  f"{nombre_local} recibe {gc_l:.2f} por partido frente a {gc_v:.2f} del rival.")

    factores.append({
        "factor":    "Potencial ofensivo y defensivo",
        "impacto":   nivel_impacto(abs(ventaja_of) * 0.5 + abs(ventaja_def) * 0.5),
        "tipo":      "doble_barra",
        "local":     {"nombre": nombre_local,     "goles_favor": round(gf_l, 2), "goles_contra": round(gc_l, 2)},
        "visitante": {"nombre": nombre_visitante, "goles_favor": round(gf_v, 2), "goles_contra": round(gc_v, 2)},
        "interpretacion": interp,
    })

    # ── 4. PERFIL EMPATADOR ─────────────────────────────────────────────────
    tasa_emp_l  = calcular_tasa_empate(local,     es_local=True)
    tasa_emp_v  = calcular_tasa_empate(visitante, es_local=False)
    emp_total_l = local.get("empatados", 0)
    emp_total_v = visitante.get("empatados", 0)
    partidos_l  = local.get("partidos", 1)
    partidos_v  = visitante.get("partidos", 1)
    d_l         = contar_empates_recientes(local.get("ultimos_5", []))
    d_v         = contar_empates_recientes(visitante.get("ultimos_5", []))
    tasa_max    = max(tasa_emp_l, tasa_emp_v)

    nota_vuelta = ""
    if tasa_max >= 0.25:
        if contexto["clasifica_empate_local"] and not contexto["clasifica_empate_visitante"]:
            nota_vuelta = (f" En el contexto de esta serie, un empate en el partido "
                           f"beneficia a {nombre_local}, que clasifica por tabla.")
        elif not contexto["clasifica_empate_local"] and contexto["clasifica_empate_visitante"]:
            nota_vuelta = (f" En el contexto de esta serie, un empate en el partido "
                           f"beneficia a {nombre_visitante}, que clasifica por tabla.")

    if tasa_max >= 0.40:
        equipo_emp = nombre_local if tasa_emp_l >= tasa_emp_v else nombre_visitante
        tasa_alta  = max(tasa_emp_l, tasa_emp_v)
        interp = (f"{equipo_emp} es un equipo marcadamente empatador: empata el "
                  f"{tasa_alta*100:.0f}% de sus partidos en su rol situacional. "
                  f"En los últimos 5, ambos suman {d_l + d_v} empate(s), lo que eleva "
                  f"la probabilidad de un resultado igualado en el marcador." + nota_vuelta)
    elif tasa_max >= 0.25:
        interp = (f"Perfil empatador moderado: {nombre_local} empata el {tasa_emp_l*100:.0f}% "
                  f"en casa ({emp_total_l} empates en {partidos_l} partidos) y "
                  f"{nombre_visitante} el {tasa_emp_v*100:.0f}% de visita "
                  f"({emp_total_v} empates en {partidos_v} partidos). "
                  f"El empate es una opción real." + nota_vuelta)
    else:
        interp = (f"Ambos equipos tienden a resolver sin empate: {nombre_local} empata el "
                  f"{tasa_emp_l*100:.0f}% en casa y {nombre_visitante} el "
                  f"{tasa_emp_v*100:.0f}% de visita. El partido debería tener un ganador.")

    factores.append({
        "factor":    "Perfil empatador",
        "impacto":   nivel_impacto(tasa_max),
        "tipo":      "barras",
        "local":     {"etiqueta": "Tasa empate local",  "valor": round(tasa_emp_l, 2),
                      "detalle": f"{emp_total_l} empates en {partidos_l} partidos | {d_l}D últimos 5",
                      "nombre": nombre_local},
        "visitante": {"etiqueta": "Tasa empate visita", "valor": round(tasa_emp_v, 2),
                      "detalle": f"{emp_total_v} empates en {partidos_v} partidos | {d_v}D últimos 5",
                      "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 5. H2H ──────────────────────────────────────────────────────────────
    n_total = resultado["n_h2h_clausura"] + resultado["n_h2h_apertura"]
    if n_total > 0:
        h2h_score = resultado["h2h_local"]
        n_c       = resultado["n_h2h_clausura"]
        n_a       = resultado["n_h2h_apertura"]

        wins_h2h_local, empates_h2h, wins_h2h_visit = contar_resultados_h2h(
            resultado["partidos_h2h"], nombre_local, nombre_visitante
        )

        if h2h_score >= 0.60:
            interp = (f"{nombre_local} domina el historial reciente con {wins_h2h_local} victorias "
                      f"en {n_total} enfrentamientos ({n_c} del Clausura 2026, {n_a} del Apertura 2025). "
                      f"{nombre_visitante} ha ganado {wins_h2h_visit} y hubo {empates_h2h} empate(s).")
        elif h2h_score <= 0.40:
            interp = (f"{nombre_visitante} lleva ventaja histórica: {wins_h2h_visit} victorias "
                      f"en {n_total} enfrentamientos recientes ({n_c} del Clausura 2026, {n_a} del Apertura 2025). "
                      f"{nombre_local} ha ganado {wins_h2h_local} y hubo {empates_h2h} empate(s).")
        else:
            interp = (f"Historial equilibrado: {wins_h2h_local} victorias para {nombre_local}, "
                      f"{wins_h2h_visit} para {nombre_visitante} y {empates_h2h} empate(s) "
                      f"en {n_total} enfrentamientos recientes. No hay dominancia clara.")

        factores.append({
            "factor":         "Historial directo",
            "impacto":        nivel_impacto(abs(h2h_score - 0.5) * 2),
            "tipo":           "h2h",
            "local":          {"nombre": nombre_local,     "victorias": wins_h2h_local},
            "visitante":      {"nombre": nombre_visitante, "victorias": wins_h2h_visit},
            "empates":        empates_h2h,
            "partidos":       resultado["partidos_h2h"],
            "total":          n_total,
            "interpretacion": interp,
        })

    # ── 6. EXPERIENCIA ELIMINATORIA ─────────────────────────────────────────
    exp_l    = resultado["exp_local"]
    exp_v    = resultado["exp_visitante"]
    diff_exp = exp_l - exp_v

    if abs(diff_exp) >= 0.15:
        equipo_exp   = nombre_local    if diff_exp > 0 else nombre_visitante
        equipo_inexp = nombre_visitante if diff_exp > 0 else nombre_local
        exp_mayor    = max(exp_l, exp_v)
        exp_menor    = min(exp_l, exp_v)
        interp = (f"{equipo_exp} acumula mayor experiencia en instancias eliminatorias "
                  f"(índice {exp_mayor:.2f}/1.0 vs {exp_menor:.2f}/1.0 de {equipo_inexp}), "
                  f"basado en resultados de las últimas 4 liguillas. "
                  f"La presión de los partidos de eliminación suele favorecer "
                  f"a los equipos con mayor rodaje en estas instancias.")
    else:
        interp = (f"Experiencia eliminatoria similar entre ambos equipos: "
                  f"{nombre_local} con índice {exp_l:.2f}/1.0 y {nombre_visitante} con {exp_v:.2f}/1.0. "
                  f"Este factor no genera ventaja significativa para ninguno.")

    factores.append({
        "factor":    "Experiencia eliminatoria",
        "impacto":   nivel_impacto(abs(diff_exp)),
        "tipo":      "barras",
        "local":     {"etiqueta": "Índice liguilla", "valor": round(exp_l, 2), "nombre": nombre_local},
        "visitante": {"etiqueta": "Índice liguilla", "valor": round(exp_v, 2), "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 7. CONTEXTO DE SERIE ────────────────────────────────────────────────
    dif       = contexto["diferencia_global"]
    gol_l_ida = contexto["goles_vuelta_local_en_ida"]
    gol_v_ida = contexto["goles_vuelta_visitante_en_ida"]

    if dif > 0:
        interp = (f"{nombre_local} llega con ventaja en el marcador global: "
                  f"ganó la ida {gol_l_ida}-{gol_v_ida} y además tiene mejor posición en tabla. "
                  f"Le basta con no perder por {dif + 1} o más goles para clasificar. "
                  f"Puede especular tácticamente desde el inicio.")
    elif dif == 0:
        interp = (f"Serie completamente abierta: empate global {gol_l_ida}-{gol_v_ida}. "
                  f"Si la vuelta termina empatada, clasifica {nombre_local} por mejor posición en tabla. "
                  f"{nombre_visitante} está obligado a ganar para avanzar.")
    else:
        interp = (f"{nombre_visitante} llega con ventaja en el marcador global: "
                  f"ganó la ida {gol_v_ida}-{gol_l_ida}. "
                  f"{nombre_local} necesita ganar por {abs(dif) + 1} o más goles para clasificar directamente, "
                  f"o por {abs(dif)} para igualar el global — pero en ese caso perdería por tabla. "
                  f"Obligado a atacar desde el primer minuto.")

    factores.append({
        "factor":                     "Contexto de serie",
        "impacto":                    "alto",
        "tipo":                       "serie",
        "diferencia_global":          dif,
        "goles_local_en_ida":         gol_l_ida,
        "goles_visitante_en_ida":     gol_v_ida,
        "clasifica_empate_local":     contexto["clasifica_empate_local"],
        "clasifica_empate_visitante": contexto["clasifica_empate_visitante"],
        "local":     {"nombre": nombre_local,     "estado": contexto["estado_local"]},
        "visitante": {"nombre": nombre_visitante, "estado": contexto["estado_visitante"]},
        "interpretacion": interp,
    })

    # ── 8. URGENCIA TÁCTICA ─────────────────────────────────────────────────
    urg_l = contexto["urgencia_local"]
    urg_v = contexto["urgencia_visitante"]

    def descripcion_urgencia(urgencia, goles_necesarios, nombre, clasifica_empate):
        if urgencia == "nula":
            return (f"{nombre} puede gestionar el partido sin arriesgar: "
                    f"clasifica incluso si la vuelta termina en empate. "
                    f"Probablemente opte por un bloque defensivo y contraataques.")
        elif urgencia == "media":
            return (f"{nombre} necesita {goles_necesarios} gol para avanzar. "
                    f"Atacará con orden, sin sacrificar la estructura defensiva.")
        else:
            return (f"{nombre} necesita {goles_necesarios} goles para clasificar. "
                    f"Deberá abrir el partido desde el inicio, lo que generará "
                    f"espacios para el rival y aumenta la probabilidad de un partido con más goles.")

    interp_l = descripcion_urgencia(urg_l, contexto["goles_necesita_local"],     nombre_local,     contexto["clasifica_empate_local"])
    interp_v = descripcion_urgencia(urg_v, contexto["goles_necesita_visitante"], nombre_visitante, contexto["clasifica_empate_visitante"])

    if urg_l == "nula" and urg_v in ("media", "alta"):
        interp = interp_v + " " + interp_l
    elif urg_v == "nula" and urg_l in ("media", "alta"):
        interp = interp_l + " " + interp_v
    else:
        interp = interp_l + " " + interp_v

    factores.append({
        "factor":  "Urgencia táctica",
        "impacto": "alto" if (urg_l == "alta" or urg_v == "alta") else "medio",
        "tipo":    "urgencia",
        "local": {
            "nombre":         nombre_local,
            "urgencia":       urg_l,
            "goles_necesita": contexto["goles_necesita_local"],
            "bonus_aplicado": round(resultado["bonus_urgencia_local"], 3),
        },
        "visitante": {
            "nombre":         nombre_visitante,
            "urgencia":       urg_v,
            "goles_necesita": contexto["goles_necesita_visitante"],
            "bonus_aplicado": round(resultado["bonus_urgencia_visitante"], 3),
        },
        "interpretacion": interp,
    })

    return factores


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
# GENERAR PARTIDO VUELTA
# =============================

def generar_partido_vuelta(
    id,
    local_nombre,
    visitante_nombre,
    goles_ida_local,
    goles_ida_visitante,
    db,
    h2h,
):
    local_raw     = obtener_equipo(local_nombre,     db)
    visitante_raw = obtener_equipo(visitante_nombre, db)

    if not local_raw:
        raise ValueError(f"Equipo local no encontrado: '{local_nombre}'")
    if not visitante_raw:
        raise ValueError(f"Equipo visitante no encontrado: '{visitante_nombre}'")

    # ── Adaptar al formato plano que usa el modelo internamente ─────────────
    local     = adaptar_equipo(local_raw)
    visitante = adaptar_equipo(visitante_raw)

    contexto = calcular_contexto_vuelta(
        goles_ida_local=goles_ida_local,
        goles_ida_visitante=goles_ida_visitante,
        tabla_local=local["posicion"],
        tabla_visitante=visitante["posicion"],
    )

    resultado = predecir_probabilidades_vuelta(
        local, visitante, h2h,
        local_nombre, visitante_nombre,
        contexto,
    )

    gap = abs(resultado["local"] - resultado["visitante"])
    if resultado["empate"] > 0.30 and gap < 0.08:
        pred_partido = "Empate"
    elif resultado["local"] > resultado["visitante"]:
        pred_partido = local["nombre"]
    else:
        pred_partido = visitante["nombre"]

    if resultado["local"] >= resultado["visitante"]:
        pred_clasifica = local_nombre
    else:
        pred_clasifica = visitante_nombre if not contexto["clasifica_empate_local"] else local_nombre

    analisis = generar_analisis_vuelta(
        local, visitante, resultado,
        local_nombre, visitante_nombre,
        contexto,
    )

    output = {
        "id":               id,
        "fase":             "liguilla_vuelta",
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
        "prediccion":       pred_partido,
        "clasifica":        pred_clasifica,
        "contexto_serie":   contexto,
        "analisis":         analisis,
    }

    guardar_resultado(output)
    return output


# =============================
# MAIN
# =============================

if __name__ == "__main__":
    db  = cargar_equipos()
    h2h = cargar_h2h()

    PARTIDOS_VUELTA = [
        {
            "id": 1,
            "local_nombre":        "Guadalajara",
            "visitante_nombre":    "Cruz Azul",
            "goles_ida_local":     2,
            "goles_ida_visitante": 2,
        },
        {
            "id": 2,
            "local_nombre":        "Pumas UNAM",
            "visitante_nombre":    "Pachuca",
            "goles_ida_local":     1,
            "goles_ida_visitante": 0,
        }
    ]

    todos_los_partidos = []

    for p in PARTIDOS_VUELTA:
        print(f"\n⚽ Generando: {p['local_nombre']} vs {p['visitante_nombre']}...")
        partido = generar_partido_vuelta(
            id=p["id"],
            local_nombre=p["local_nombre"],
            visitante_nombre=p["visitante_nombre"],
            goles_ida_local=p["goles_ida_local"],
            goles_ida_visitante=p["goles_ida_visitante"],
            db=db,
            h2h=h2h,
        )
        todos_los_partidos.append(partido)
        print(json.dumps(partido, indent=2, ensure_ascii=False))

    print(f"\n✅ {len(todos_los_partidos)} partidos generados y guardados en partidos_liguilla.json")
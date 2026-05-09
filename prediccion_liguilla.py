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

    # Juntar partidos para mostrar en análisis
    partidos_recientes = (cruce["clausura_2026"] + cruce["apertura_2025"])[:5]

    return limitar(score, 0.0, 1.0), n_c, n_a, partidos_recientes


def get_experiencia(nombre):
    key = normalizar_nombre(nombre)
    if key in EXPERIENCIA_LIGUILLA:
        return EXPERIENCIA_LIGUILLA[key]
    for k, v in EXPERIENCIA_LIGUILLA.items():
        if k in key or key in k:
            return v
    return 0.50


def quien_juega_vuelta_en_casa(local, visitante):
    return "local" if local["posicion"] <= visitante["posicion"] else "visitante"


def calcular_prob_empate(f_local, f_visitante):
    diferencia  = abs(f_local - f_visitante)
    prob_empate = 0.28 - (diferencia / 0.40) * 0.18
    return limitar(prob_empate, 0.10, 0.28)


# =============================
# PROBABILIDADES
# =============================

def predecir_probabilidades_liguilla(equipo_local, equipo_visitante, h2h_data, nombre_local, nombre_visitante):

    fb_local     = calcular_fuerza_base(equipo_local,     es_local=True)
    fb_visitante = calcular_fuerza_base(equipo_visitante, es_local=False)

    h2h_local, n_c, n_a, partidos_h2h = calcular_h2h_score(nombre_local, nombre_visitante, h2h_data)
    h2h_visitante = 1.0 - h2h_local

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
    confianza = "ajustado" if gap < 0.08 else "moderado" if gap < 0.18 else "favorable"

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
        "partidos_h2h":     partidos_h2h,
        "vuelta_en_casa":   vuelta,
        "exp_local":        exp_local,
        "exp_visitante":    exp_visitante,
        "fb_local":         fb_local,
        "fb_visitante":     fb_visitante,
    }


# =============================
# IMPACTO DE FACTOR
# =============================

def nivel_impacto(diferencia_normalizada):
    """
    Dado que tan diferentes son dos equipos en un factor,
    devuelve el nivel de impacto en la predicción.
    """
    if diferencia_normalizada >= 0.25:
        return "alto"
    elif diferencia_normalizada >= 0.12:
        return "medio"
    else:
        return "bajo"


# =============================
# ANÁLISIS ESTRUCTURADO
# =============================

def generar_analisis(local, visitante, resultado, nombre_local, nombre_visitante):
    """
    Devuelve una lista de factores estructurados, cada uno con:
    - factor: nombre del factor
    - impacto: alto / medio / bajo
    - tipo: forma | barras | h2h | experiencia | vuelta
    - local: datos del equipo local para ese factor
    - visitante: datos del equipo visitante para ese factor
    - interpretacion: conclusión analítica con datos concretos
    """
    factores = []

    # ── 1. FORMA RECIENTE ────────────────────────────
    fl = local["forma_ponderada"]
    fv = visitante["forma_ponderada"]
    ul5_l = local.get("ultimos_5", [])
    ul5_v = visitante.get("ultimos_5", [])

    wins_l = ul5_l.count("W")
    wins_v = ul5_v.count("W")
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
        "factor":        "Forma reciente",
        "impacto":       nivel_impacto(abs(fl - fv)),
        "tipo":          "forma",
        "local":         { "valor": round(fl, 2), "ultimos_5": ul5_l, "nombre": nombre_local },
        "visitante":     { "valor": round(fv, 2), "ultimos_5": ul5_v, "nombre": nombre_visitante },
        "interpretacion": interp,
    })

    # ── 2. RENDIMIENTO SITUACIONAL ───────────────────
    wrl = local["win_rate_local"]
    wrv = visitante["win_rate_visita"]
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
        "local":     {
            "etiqueta": "Win rate local",
            "valor":    round(wrl, 2),
            "detalle":  f"{gl_l}G / {el_l}E / {pl_l}P",
            "nombre":   nombre_local,
        },
        "visitante": {
            "etiqueta": "Win rate visita",
            "valor":    round(wrv, 2),
            "detalle":  f"{gv_v}G / {ev_v}E / {pv_v}P",
            "nombre":   nombre_visitante,
        },
        "interpretacion": interp,
    })

    # ── 3. CAPACIDAD OFENSIVA Y DEFENSIVA ────────────
    gf_l = local["goles_favor_promedio"]
    gc_l = local["goles_contra_promedio"]
    gf_v = visitante["goles_favor_promedio"]
    gc_v = visitante["goles_contra_promedio"]

    ventaja_of = gf_l - gf_v
    ventaja_def = gc_v - gc_l   # positivo = local más sólido

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
        "local":     {
            "nombre":        nombre_local,
            "goles_favor":   round(gf_l, 2),
            "goles_contra":  round(gc_l, 2),
        },
        "visitante": {
            "nombre":        nombre_visitante,
            "goles_favor":   round(gf_v, 2),
            "goles_contra":  round(gc_v, 2),
        },
        "interpretacion": interp,
    })

    # ── 4. H2H ───────────────────────────────────────
    n_total = resultado["n_h2h_clausura"] + resultado["n_h2h_apertura"]
    if n_total > 0:
        h2h    = resultado["h2h_local"]
        n_c    = resultado["n_h2h_clausura"]
        n_a    = resultado["n_h2h_apertura"]
        # Por esto:
        wins_h2h_local  = 0
        wins_h2h_visit  = 0
        empates_h2h     = 0
        for p in resultado["partidos_h2h"]:
            gl = p["goles_local"]
            gv = p["goles_visitante"]
            if gl == gv:
                empates_h2h += 1
            elif normalizar_nombre(p["local"]) == normalizar_nombre(nombre_local):
                if gl > gv:
                    wins_h2h_local += 1
                else:
                    wins_h2h_visit += 1
            else:
                if gv > gl:
                    wins_h2h_local += 1
                else:
                    wins_h2h_visit += 1

        if h2h >= 0.60:
            interp = (f"{nombre_local} domina el historial reciente con {wins_h2h_local} victorias "
                     f"en {n_total} enfrentamientos ({n_c} del Clausura 2026, {n_a} del Apertura 2025). "
                     f"{nombre_visitante} solo ha ganado {wins_h2h_visit} de esos cruces.")
        elif h2h <= 0.40:
            interp = (f"{nombre_visitante} lleva ventaja histórica: {wins_h2h_visit} victorias "
                     f"en {n_total} enfrentamientos recientes ({n_c} del Clausura 2026, {n_a} del Apertura 2025). "
                     f"{nombre_local} solo ha ganado {wins_h2h_local} de esos cruces.")
        else:
            interp = (f"Historial equilibrado entre ambos equipos: {wins_h2h_local} victorias "
                     f"para {nombre_local} y {wins_h2h_visit} para {nombre_visitante} "
                     f"en {n_total} enfrentamientos recientes. No hay dominancia clara.")

        factores.append({
            "factor":          "Historial directo",
            "impacto":         nivel_impacto(abs(h2h - 0.5) * 2),
            "tipo":            "h2h",
            "local":           { "nombre": nombre_local,    "victorias": wins_h2h_local },
            "visitante":       { "nombre": nombre_visitante, "victorias": wins_h2h_visit },
            "partidos":        resultado["partidos_h2h"],
            "total":           n_total,
            "interpretacion":  interp,
        })

    # ── 5. EXPERIENCIA ELIMINATORIA ──────────────────
    exp_l  = resultado["exp_local"]
    exp_v  = resultado["exp_visitante"]
    diff_exp = exp_l - exp_v

    if abs(diff_exp) >= 0.15:
        equipo_exp = nombre_local if diff_exp > 0 else nombre_visitante
        equipo_inexp = nombre_visitante if diff_exp > 0 else nombre_local
        exp_mayor = max(exp_l, exp_v)
        exp_menor = min(exp_l, exp_v)

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
        "local":     { "etiqueta": "Índice liguilla", "valor": round(exp_l, 2), "nombre": nombre_local },
        "visitante": { "etiqueta": "Índice liguilla", "valor": round(exp_v, 2), "nombre": nombre_visitante },
        "interpretacion": interp,
    })

    # ── 6. VENTAJA DE VUELTA EN CASA ─────────────────
    vuelta = resultado["vuelta_en_casa"]
    equipo_vuelta   = nombre_local   if vuelta == "local"     else nombre_visitante
    equipo_sin_vuelta = nombre_visitante if vuelta == "local" else nombre_local
    pos_l = local["posicion"]
    pos_v = visitante["posicion"]

    interp = (f"{equipo_vuelta} terminó mejor posicionado en la tabla "
             f"(posición {pos_l if vuelta == 'local' else pos_v} vs "
             f"{pos_v if vuelta == 'local' else pos_l}), "
             f"lo que le otorga el derecho de disputar la vuelta en casa. "
             f"Esta ventaja táctica le permite a {equipo_vuelta} especular en la ida "
             f"y definir la serie ante su afición, mientras {equipo_sin_vuelta} "
             f"deberá resolver la eliminatoria jugando el partido decisivo de visitante.")

    factores.append({
        "factor":         "Ventaja de vuelta en casa",
        "impacto":        "medio",
        "tipo":           "vuelta",
        "equipo_vuelta":  equipo_vuelta,
        "local":          { "nombre": nombre_local,    "posicion": pos_l },
        "visitante":      { "nombre": nombre_visitante, "posicion": pos_v },
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

    analisis = generar_analisis(local, visitante, resultado, local_nombre, visitante_nombre)

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
        "analisis":         analisis,
    }

    guardar_resultado(output)
    return output


# =============================
# TEST
# =============================

if __name__ == "__main__":
    db  = cargar_equipos()
    h2h = cargar_h2h()

    partido = generar_partido_ida(1, "Toluca", "Pachuca", db, h2h)
    print(json.dumps(partido, indent=2, ensure_ascii=False))
    print("\nPartido de ida generado y guardado en partidos_liguilla.json")

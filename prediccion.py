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
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    key = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        key = key.replace(a, b)
    return db.get(key)


# =============================
# CONFIG
# =============================

TOTAL_EQUIPOS = 18

K_LOGISTICO  = 4.2
MAX_FAVORITO = 0.68

# Pesos del modelo de fuerza (suman 1.0)
PESO_FORMA          = 0.30
PESO_WINRATE        = 0.22
PESO_GOLES_FAVOR    = 0.12
PESO_GOLES_CONTRA   = 0.12
PESO_POSICION       = 0.08
PESO_TENDENCIA      = 0.06
PESO_STREAK         = 0.10

# Pesos del modelo de empate (suman 1.0)
# El histórico pesa más porque es el predictor más confiable
PESO_EMPATE_BASE      = 0.20   # diferencia de fuerzas
PESO_EMPATE_HISTORICO = 0.65   # tasa histórica situacional (empatados_local / partidos_local)
PESO_EMPATE_MOMENTUM  = 0.15   # D's recientes en últimos 5


# =============================
# HELPERS
# =============================

def limitar(v, a, b):
    return max(a, min(v, b))


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


def nivel_impacto(diferencia_normalizada):
    if diferencia_normalizada >= 0.25:
        return "alto"
    elif diferencia_normalizada >= 0.12:
        return "medio"
    else:
        return "bajo"


def contar_empates_recientes(ultimos_5):
    return ultimos_5.count("D")


def calcular_tasa_empate(equipo, es_local):
    """
    Tasa de empate situacional:
    - Local:     empatados_local  / partidos_local
    - Visitante: empatados_visita / partidos_visita
    """
    if es_local:
        partidos  = equipo.get("partidos_local", 0)
        empatados = equipo.get("empatados_local", 0)
    else:
        partidos  = equipo.get("partidos_visita", 0)
        empatados = equipo.get("empatados_visita", 0)

    if partidos == 0:
        return 0.25  # fallback neutro

    return limitar(empatados / partidos, 0.0, 1.0)


# =============================
# FUERZA
# =============================

def calcular_fuerza(equipo, es_local):
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
# EMPATE MEJORADO
# =============================

def calcular_prob_empate(f_local, f_visitante, equipo_local, equipo_visitante):
    """
    Tres componentes:
    1. Base (0.20):      diferencia de fuerzas — partidos parejos empatan más
    2. Histórico (0.65): tasa situacional real de cada equipo
    3. Momentum (0.15):  D's recientes en últimos 5 — patrón de forma actual

    El empate se calcula PRIMERO y el resto se distribuye proporcionalmente,
    evitando que la normalización lo comprima.
    """

    # 1. Base: equipos parejos → empate más probable
    diferencia = abs(f_local - f_visitante)
    base = limitar(0.28 - (diferencia / 0.40) * 0.18, 0.10, 0.28)

    # 2. Histórico situacional
    tasa_local     = calcular_tasa_empate(equipo_local,     es_local=True)
    tasa_visitante = calcular_tasa_empate(equipo_visitante, es_local=False)
    # Usamos el máximo: si CUALQUIERA de los dos es muy empatador, sube la prob
    historico = max(tasa_local, tasa_visitante)

    # 3. Momentum: cada D reciente suma ~7%, cap en 0.35
    d_local     = contar_empates_recientes(equipo_local.get("ultimos_5", []))
    d_visitante = contar_empates_recientes(equipo_visitante.get("ultimos_5", []))
    momentum    = limitar((d_local + d_visitante) * 0.07, 0.0, 0.35)

    prob_empate = (
        base      * PESO_EMPATE_BASE      +
        historico * PESO_EMPATE_HISTORICO +
        momentum  * PESO_EMPATE_MOMENTUM
    )

    return limitar(prob_empate, 0.08, 0.46)


# =============================
# PROBABILIDADES
# =============================

def predecir_probabilidades(equipo_local, equipo_visitante):
    f_local     = calcular_fuerza(equipo_local,     es_local=True)
    f_visitante = calcular_fuerza(equipo_visitante, es_local=False)

    score   = f_local - f_visitante
    ratio_l = 1 / (1 + math.exp(-K_LOGISTICO * score))
    ratio_v = 1 - ratio_l

    if ratio_l > MAX_FAVORITO:
        ratio_l = MAX_FAVORITO
        ratio_v = 1 - ratio_l
    if ratio_v > MAX_FAVORITO:
        ratio_v = MAX_FAVORITO
        ratio_l = 1 - ratio_v

    # Empate se calcula primero — el resto se distribuye en proporción al ratio
    prob_empate = calcular_prob_empate(f_local, f_visitante, equipo_local, equipo_visitante)
    restante    = 1.0 - prob_empate
    prob_local     = restante * ratio_l
    prob_visitante = restante * ratio_v

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
    }


# =============================
# ANÁLISIS ESTRUCTURADO
# =============================

def generar_analisis(local, visitante, nombre_local, nombre_visitante):
    factores = []

    # ── 1. FORMA RECIENTE ────────────────────────────
    fl    = local["forma_ponderada"]
    fv    = visitante["forma_ponderada"]
    ul5_l = local.get("ultimos_5", [])
    ul5_v = visitante.get("ultimos_5", [])
    wins_l   = ul5_l.count("W")
    wins_v   = ul5_v.count("W")
    losses_l = ul5_l.count("L")
    losses_v = ul5_v.count("L")
    d_l      = ul5_l.count("D")
    d_v      = ul5_v.count("D")

    if fl > fv:
        if wins_l >= 4:
            interp = (f"{nombre_local} atraviesa su mejor racha del torneo: {wins_l} victorias "
                      f"en los últimos 5 partidos (índice {fl:.2f}/1.0). "
                      f"{nombre_visitante} muestra mayor irregularidad con {wins_v} victorias "
                      f"y {losses_v} derrotas en ese mismo período (índice {fv:.2f}/1.0).")
        else:
            interp = (f"{nombre_local} llega con mejor momentum reciente: índice {fl:.2f}/1.0 "
                      f"frente a {fv:.2f}/1.0 de {nombre_visitante}. "
                      f"En los últimos 5, {nombre_local} acumula {wins_l} victorias "
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
                      f"En los últimos 5, {nombre_visitante} acumula {wins_v} victorias "
                      f"contra {wins_l} del rival.")
    else:
        interp = (f"Ambos equipos llegan en condiciones similares: "
                  f"{nombre_local} con índice {fl:.2f}/1.0 y {nombre_visitante} con {fv:.2f}/1.0.")

    if d_l >= 2 or d_v >= 2:
        interp += (f" Nota: {nombre_local} suma {d_l} empate(s) y "
                   f"{nombre_visitante} {d_v} empate(s) en sus últimos 5, "
                   f"lo que eleva la probabilidad de un resultado igualado.")

    factores.append({
        "factor":         "Forma reciente",
        "impacto":        nivel_impacto(abs(fl - fv)),
        "tipo":           "forma",
        "local":          {"valor": round(fl, 2), "ultimos_5": ul5_l, "nombre": nombre_local},
        "visitante":      {"valor": round(fv, 2), "ultimos_5": ul5_v, "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 2. RENDIMIENTO SITUACIONAL ───────────────────
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
                  f"en casa ({gl_l}G/{el_l}E/{pl_l}P), mientras {nombre_visitante} "
                  f"apenas convierte el {wrv*100:.0f}% de visita ({gv_v}G/{ev_v}E/{pv_v}P). "
                  f"La localía es determinante en este cruce.")
    elif wrl >= 0.55:
        interp = (f"{nombre_local} es dominante en casa: {wrl*100:.0f}% de victorias "
                  f"({gl_l}G/{el_l}E/{pl_l}P). {nombre_visitante} respondió con "
                  f"{wrv*100:.0f}% de efectividad de visita ({gv_v}G/{ev_v}E/{pv_v}P).")
    elif wrv <= 0.30:
        interp = (f"{nombre_visitante} tiene dificultades fuera de casa: {wrv*100:.0f}% "
                  f"de victorias como visitante ({gv_v}G/{ev_v}E/{pv_v}P). "
                  f"{nombre_local} gana el {wrl*100:.0f}% en casa ({gl_l}G/{el_l}E/{pl_l}P).")
    else:
        interp = (f"Rendimiento situacional equilibrado: {nombre_local} gana el {wrl*100:.0f}% "
                  f"en casa ({gl_l}G/{el_l}E/{pl_l}P) y {nombre_visitante} el {wrv*100:.0f}% "
                  f"de visita ({gv_v}G/{ev_v}E/{pv_v}P).")

    factores.append({
        "factor":    "Rendimiento situacional",
        "impacto":   nivel_impacto(abs(wrl - wrv)),
        "tipo":      "barras",
        "local":     {"etiqueta": "Win rate local",  "valor": round(wrl, 2), "detalle": f"{gl_l}G / {el_l}E / {pl_l}P", "nombre": nombre_local},
        "visitante": {"etiqueta": "Win rate visita", "valor": round(wrv, 2), "detalle": f"{gv_v}G / {ev_v}E / {pv_v}P", "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 3. POTENCIAL OFENSIVO Y DEFENSIVO ────────────
    gf_l = local["goles_favor_promedio"]
    gc_l = local["goles_contra_promedio"]
    gf_v = visitante["goles_favor_promedio"]
    gc_v = visitante["goles_contra_promedio"]
    ventaja_of  = gf_l - gf_v
    ventaja_def = gc_v - gc_l

    if ventaja_of >= 0.4 and ventaja_def >= 0.3:
        interp = (f"Superioridad ofensiva y defensiva de {nombre_local}: anota {gf_l:.2f} goles "
                  f"por partido frente a {gf_v:.2f}, y recibe {gc_l:.2f} frente a {gc_v:.2f}.")
    elif ventaja_of >= 0.4:
        interp = (f"{nombre_local} tiene mayor potencia ofensiva: {gf_l:.2f} goles/partido "
                  f"contra {gf_v:.2f} de {nombre_visitante}. En defensa: {gc_l:.2f} vs {gc_v:.2f}.")
    elif ventaja_of <= -0.4:
        interp = (f"{nombre_visitante} genera más peligro ofensivo: {gf_v:.2f} goles/partido "
                  f"frente a {gf_l:.2f} de {nombre_local}. En defensa: {gc_l:.2f} vs {gc_v:.2f}.")
    else:
        interp = (f"Producción ofensiva similar: {nombre_local} promedia {gf_l:.2f} goles/partido "
                  f"y {nombre_visitante} {gf_v:.2f}. En defensa: {gc_l:.2f} vs {gc_v:.2f}.")

    factores.append({
        "factor":    "Potencial ofensivo y defensivo",
        "impacto":   nivel_impacto(abs(ventaja_of) * 0.5 + abs(ventaja_def) * 0.5),
        "tipo":      "doble_barra",
        "local":     {"nombre": nombre_local,    "goles_favor": round(gf_l, 2), "goles_contra": round(gc_l, 2)},
        "visitante": {"nombre": nombre_visitante, "goles_favor": round(gf_v, 2), "goles_contra": round(gc_v, 2)},
        "interpretacion": interp,
    })

    # ── 4. PERFIL EMPATADOR ──────────────────────────
    tasa_emp_l  = calcular_tasa_empate(local,     es_local=True)
    tasa_emp_v  = calcular_tasa_empate(visitante, es_local=False)
    emp_total_l = local.get("empatados", 0)
    emp_total_v = visitante.get("empatados", 0)
    partidos_l  = local.get("partidos", 1)
    partidos_v  = visitante.get("partidos", 1)
    d_l         = contar_empates_recientes(local.get("ultimos_5", []))
    d_v         = contar_empates_recientes(visitante.get("ultimos_5", []))
    tasa_max    = max(tasa_emp_l, tasa_emp_v)

    if tasa_max >= 0.40:
        equipo_emp = nombre_local if tasa_emp_l >= tasa_emp_v else nombre_visitante
        tasa_alta  = max(tasa_emp_l, tasa_emp_v)
        interp = (f"{equipo_emp} es un equipo marcadamente empatador: empata el "
                  f"{tasa_alta*100:.0f}% de sus partidos en su rol situacional. "
                  f"En los últimos 5, ambos suman {d_l + d_v} empate(s), lo que refuerza "
                  f"la probabilidad de un resultado igualado.")
    elif tasa_max >= 0.25:
        interp = (f"Perfil empatador moderado: {nombre_local} empata el {tasa_emp_l*100:.0f}% "
                  f"en casa ({emp_total_l} empates en {partidos_l} partidos) y "
                  f"{nombre_visitante} el {tasa_emp_v*100:.0f}% de visita "
                  f"({emp_total_v} empates en {partidos_v} partidos). "
                  f"El empate es una opción real.")
    else:
        interp = (f"Ambos equipos tienden a resolver sin empate: {nombre_local} empata el "
                  f"{tasa_emp_l*100:.0f}% en casa y {nombre_visitante} el "
                  f"{tasa_emp_v*100:.0f}% de visita. El partido debería tener un ganador.")

    factores.append({
        "factor":    "Perfil empatador",
        "impacto":   nivel_impacto(tasa_max),
        "tipo":      "barras",
        "local":     {"etiqueta": "Tasa empate local",  "valor": round(tasa_emp_l, 2), "detalle": f"{emp_total_l} empates en {partidos_l} partidos | {d_l}D últimos 5", "nombre": nombre_local},
        "visitante": {"etiqueta": "Tasa empate visita", "valor": round(tasa_emp_v, 2), "detalle": f"{emp_total_v} empates en {partidos_v} partidos | {d_v}D últimos 5", "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 5. POSICIÓN Y TENDENCIA EN TABLA ─────────────
    pos_l  = local["posicion"]
    pos_v  = visitante["posicion"]
    tend_l = local["tendencia_posicion"]
    tend_v = visitante["tendencia_posicion"]
    diff_pos = pos_v - pos_l

    if diff_pos >= 5:
        base_interp = f"{nombre_local} está {diff_pos} posiciones arriba en la tabla (#{pos_l} vs #{pos_v})."
    elif diff_pos <= -5:
        base_interp = f"{nombre_visitante} está {abs(diff_pos)} posiciones arriba en la tabla (#{pos_v} vs #{pos_l})."
    else:
        base_interp = f"Posiciones cercanas en tabla: {nombre_local} #{pos_l}, {nombre_visitante} #{pos_v}."

    tend_interp = ""
    if tend_l > 2 and tend_v <= 0:
        tend_interp = f" Además, {nombre_local} viene subiendo mientras {nombre_visitante} se estanca o baja."
    elif tend_v > 2 and tend_l <= 0:
        tend_interp = f" Además, {nombre_visitante} viene subiendo mientras {nombre_local} se estanca o baja."
    elif tend_l > 2:
        tend_interp = f" {nombre_local} está en ascenso en la tabla."
    elif tend_v > 2:
        tend_interp = f" {nombre_visitante} está en ascenso en la tabla."
    elif tend_l < -2:
        tend_interp = f" {nombre_local} viene cayendo posiciones."
    elif tend_v < -2:
        tend_interp = f" {nombre_visitante} viene cayendo posiciones."

    factores.append({
        "factor":    "Posición y tendencia en tabla",
        "impacto":   nivel_impacto(abs(diff_pos) / TOTAL_EQUIPOS),
        "tipo":      "barras",
        "local":     {"etiqueta": "Posición", "valor": pos_l, "detalle": f"Tendencia: {'+' if tend_l > 0 else ''}{tend_l}", "nombre": nombre_local},
        "visitante": {"etiqueta": "Posición", "valor": pos_v, "detalle": f"Tendencia: {'+' if tend_v > 0 else ''}{tend_v}", "nombre": nombre_visitante},
        "interpretacion": base_interp + tend_interp,
    })

    # ── 6. RACHA SIN PERDER ──────────────────────────
    streak_l = local["imbatido_streak"]
    streak_v = visitante["imbatido_streak"]

    if streak_l >= 4 or streak_v >= 4:
        if streak_l > streak_v:
            interp = (f"{nombre_local} lleva {streak_l} partidos consecutivos sin perder, "
                      f"reflejo de estabilidad y confianza. {nombre_visitante} lleva {streak_v}.")
        elif streak_v > streak_l:
            interp = (f"{nombre_visitante} llega con racha de {streak_v} partidos sin perder, "
                      f"convirtiéndolo en rival incómodo. {nombre_local} lleva {streak_l}.")
        else:
            interp = (f"Ambos llegan con rachas similares: "
                      f"{nombre_local} con {streak_l} y {nombre_visitante} con {streak_v} partidos sin perder.")
    else:
        interp = (f"Ningún equipo llega con racha notable: "
                  f"{nombre_local} lleva {streak_l} partido(s) sin perder "
                  f"y {nombre_visitante} {streak_v}.")

    factores.append({
        "factor":    "Racha sin perder",
        "impacto":   nivel_impacto(abs(streak_l - streak_v) / 10.0),
        "tipo":      "barras",
        "local":     {"etiqueta": "Partidos sin perder", "valor": streak_l, "detalle": f"{streak_l} consecutivos", "nombre": nombre_local},
        "visitante": {"etiqueta": "Partidos sin perder", "valor": streak_v, "detalle": f"{streak_v} consecutivos", "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    return factores


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
            f"❌ Equipo no encontrado: {'local' if not local else 'visitante'}"
        )

    resultado = predecir_probabilidades(local, visitante)

    if resultado["local"] > resultado["visitante"] and resultado["local"] > resultado["empate"]:
        pred = local["nombre"]
    elif resultado["visitante"] > resultado["local"] and resultado["visitante"] > resultado["empate"]:
        pred = visitante["nombre"]
    else:
        pred = "Empate"

    analisis = generar_analisis(local, visitante, local_nombre, visitante_nombre)

    output = {
        "id":               id,
        "fase":             "fase_regular",
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
        "analisis":         analisis,
    }

    guardar_resultado(output)
    return output


# =============================
# TEST
# =============================

if __name__ == "__main__":

    db = cargar_equipos()

    casos = [
        (5, "Real Sociedad", "Betis"),
        (6, "Barcelona", "Real Madrid"),
        (7, "Fulham", "Bournemouth"),
        (8, "Crystal Palace", "Everton"),
        (9, "Stuttgart",    "Leverkusen"),
        (10, "Auxerre",    "Niza"),
        (11, "Groningen",    "Nijmegen"),
        (12, "Atlanta",    "LA Galaxy"),
        (13, "Corinthians",    "Sao Paulo"),
        (14, "Gent",    "Anderlecht"),
        (15, "Celtic",    "Rangers"),
    ]

    for id, local, visitante in casos:
        partido = generar_partido(id, local, visitante, db)
        print(f"\n{'='*50}")
        print(f"  {partido['local']} vs {partido['visitante']}")
        print(f"  Local:     {partido['prob_local']:.1%}")
        print(f"  Empate:    {partido['prob_empate']:.1%}")
        print(f"  Visitante: {partido['prob_visitante']:.1%}")
        print(f"  → Predicción: {partido['prediccion']}")

    print("\n✅ Partidos guardados en partidos.json")
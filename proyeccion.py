import json
import math
import os


# =============================
# CARGAR DATOS
# =============================

def cargar_equipos(carpeta):
    ruta = os.path.join("scrapper", carpeta, "equipos.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_h2h(carpeta):
    ruta = os.path.join("scrapper", carpeta, "h2h.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}   # torneos sin H2H disponible


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

def adaptar_equipo(equipo_raw, liga_key=None):
    """
    Convierte el formato nuevo (con competencias{}) al formato plano
    que usa internamente el modelo.

    liga_key: slug de la competencia principal (ej: "mex.1", "uefa.europa").
              Si es None, el equipo viene de un torneo copa sin liga_key definida
              y se usan los campos de acceso rápido de raíz.

    Lógica de forma:
    ─────────────────────────────────────────────────────────────────
    Liga regular  (liga_key definido):
        forma_ponderada = forma_liga  (de la competencia principal)

    Torneo copa   (liga_key=None):
        Si hay stats del torneo Y forma_liga_local → mezcla 60/40
        Si solo hay stats del torneo               → usa torneo
        Si solo hay forma_liga_local               → usa liga local
        Si no hay nada                             → 0.5 neutro

    El mismo criterio aplica a ultimos_5 e imbatido_streak.
    ─────────────────────────────────────────────────────────────────
    """
    liga = {}
    if liga_key:
        # Liga regular: leer stats situacionales de la competencia principal
        liga = equipo_raw.get("competencias", {}).get(liga_key, {})

    # ── Forma ponderada ──────────────────────────────────────────────────────
    if liga_key:
        # Liga regular: forma de esa liga directamente
        forma_final  = equipo_raw.get("forma_liga", equipo_raw.get("forma_combinada", 0.5))
        ultimos_5    = equipo_raw.get("ultimos_5_liga", [])
        streak_final = equipo_raw.get("imbatido_streak", 0)
    else:
        # Torneo copa: mezclar forma del torneo con forma de liga local
        comp_torneo  = list(equipo_raw.get("competencias", {}).values())
        stats_torneo = comp_torneo[0] if comp_torneo else {}

        forma_torneo     = stats_torneo.get("forma_ponderada", 0.0)
        forma_liga_local = equipo_raw.get("forma_liga_local", 0.0) or 0.0

        if forma_torneo > 0 and forma_liga_local > 0:
            # Ambas disponibles: torneo pesa más (más relevante al contexto)
            forma_final = round(forma_torneo * 0.60 + forma_liga_local * 0.40, 4)
        elif forma_torneo > 0:
            forma_final = forma_torneo
        elif forma_liga_local > 0:
            forma_final = forma_liga_local
        else:
            forma_final = equipo_raw.get("forma_liga", equipo_raw.get("forma_combinada", 0.5))

        # ultimos_5: preferir los del torneo, fallback a liga local
        ultimos_5_torneo     = stats_torneo.get("ultimos_5", [])
        ultimos_5_liga_local = equipo_raw.get("ultimos_5_liga_local", []) or []
        ultimos_5 = ultimos_5_torneo if ultimos_5_torneo else ultimos_5_liga_local

        # streak: el más alto entre torneo y liga local (refleja mejor estado)
        streak_torneo     = stats_torneo.get("imbatido_streak", 0)
        streak_liga_local = equipo_raw.get("imbatido_streak", 0)
        streak_final      = max(streak_torneo, streak_liga_local)

    return {
        "nombre":  equipo_raw.get("nombre", ""),
        "escudo":  equipo_raw.get("escudo", ""),

        "posicion":           equipo_raw.get("posicion", 9),
        "tendencia_posicion": equipo_raw.get("tendencia_posicion", 0),

        "forma_ponderada": forma_final,
        "imbatido_streak": streak_final,
        "ultimos_5":       ultimos_5,

        # Stats situacionales — desde competencia principal si liga_key,
        # desde raíz si torneo copa (el scraper los pone ahí como acceso rápido)
        "win_rate_local":  liga.get("win_rate_local",  equipo_raw.get("win_rate_local",  0.0)),
        "win_rate_visita": liga.get("win_rate_visita", equipo_raw.get("win_rate_visita", 0.0)),

        "goles_favor_promedio":  liga.get("goles_favor_promedio",  equipo_raw.get("goles_favor_promedio",  0.0)),
        "goles_contra_promedio": liga.get("goles_contra_promedio", equipo_raw.get("goles_contra_promedio", 0.0)),

        "partidos":  liga.get("partidos",  equipo_raw.get("partidos",  0)),
        "ganados":   liga.get("ganados",   equipo_raw.get("ganados",   0)),
        "empatados": liga.get("empatados", equipo_raw.get("empatados", 0)),
        "perdidos":  liga.get("perdidos",  equipo_raw.get("perdidos",  0)),

        "partidos_local":  liga.get("partidos_local",  equipo_raw.get("partidos_local",  0)),
        "ganados_local":   liga.get("ganados_local",   equipo_raw.get("ganados_local",   0)),
        "empatados_local": liga.get("empatados_local", equipo_raw.get("empatados_local", 0)),
        "perdidos_local":  liga.get("perdidos_local",  equipo_raw.get("perdidos_local",  0)),

        "partidos_visita":  liga.get("partidos_visita",  equipo_raw.get("partidos_visita",  0)),
        "ganados_visita":   liga.get("ganados_visita",   equipo_raw.get("ganados_visita",   0)),
        "empatados_visita": liga.get("empatados_visita", equipo_raw.get("empatados_visita", 0)),
        "perdidos_visita":  liga.get("perdidos_visita",  equipo_raw.get("perdidos_visita",  0)),
    }


# =============================
# PERFILES DE TORNEO
# =============================
# Cada perfil define cómo se comporta el modelo para ese contexto.
#
# K_LOGISTICO   → qué tan decisiva es la diferencia de fuerzas
#                 alto = liga predecible / bajo = liga muy pareja
# MAX_FAVORITO  → techo de probabilidad del favorito
# ALPHA/BETA    → peso de Poisson vs modelo de fuerza (deben sumar 1.0)
# TOTAL_EQUIPOS → para normalizar posición en tabla
# usa_h2h       → si hay historial directo relevante
# usa_experiencia → si existe índice de experiencia eliminatoria
# usa_vuelta_casa → si el formato tiene ida y vuelta con ventaja de posición
# experiencia_db  → dict con índices de experiencia (vacío si no aplica)
# ─────────────────────────────────────────────────────────────────────────

EXPERIENCIA_LIGUILLA_MX = {
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

PERFILES_TORNEO = {

    # ── Liga MX Liguilla ────────────────────────────────────────────────────
    "liguilla_mx": {
        "nombre":           "Liga MX Liguilla",
        "liga_key":          "mex.1",
        "K_LOGISTICO":      4.2,
        "MAX_FAVORITO":     0.68,
        "ALPHA":            0.70,   # Poisson
        "BETA":             0.30,   # fuerza
        "TOTAL_EQUIPOS":    18,
        "usa_h2h":          True,
        "usa_experiencia":  True,
        "usa_vuelta_casa":  True,
        "experiencia_db":   EXPERIENCIA_LIGUILLA_MX,
        "PESO_BASE":        0.65,
        "PESO_H2H":         0.20,
        "PESO_EXPERIENCIA": 0.10,
        "PESO_VUELTA_CASA": 0.05,
    },

    # ── Concacaf W Champions Cup ────────────────────────────────────────────
    # Equipos de ligas muy distintas (NWSL + Liga MX Femenil).
    # Sin H2H relevante, sin índice de experiencia.
    # K bajo porque la brecha entre ligas genera partidos más abiertos.
    "concacaf_w_champions": {
        "nombre":           "Concacaf W Champions Cup",
        "liga_key":          None,
        "K_LOGISTICO":      3.8,
        "MAX_FAVORITO":     0.72,
        "ALPHA":            0.80,
        "BETA":             0.20,
        "TOTAL_EQUIPOS":    10,
        "usa_h2h":          False,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  False,
        "experiencia_db":   {},
        "PESO_BASE":        0.80,
        "PESO_H2H":         0.00,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.20,   # localía pesa más al no haber H2H ni experiencia
    },

    # ── Concacaf Champions Cup (varonil) ────────────────────────────────────
    "concacaf_champions": {
        "nombre":           "Concacaf Champions Cup",
        "liga_key":          None,
        "K_LOGISTICO":      4.0,
        "MAX_FAVORITO":     0.70,
        "ALPHA":            0.75,
        "BETA":             0.25,
        "TOTAL_EQUIPOS":    16,
        "usa_h2h":          True,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  True,
        "experiencia_db":   {},
        "PESO_BASE":        0.75,
        "PESO_H2H":         0.15,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.10,
    },

    # ── CONMEBOL Libertadores ───────────────────────────────────────────────
    # Alta varianza: equipos de muy distintas ligas sudamericanas.
    # Localía muy importante (altitud, distancia de viaje).
    "libertadores": {
        "nombre":           "CONMEBOL Libertadores",
        "liga_key":          None,
        "K_LOGISTICO":      4.0,
        "MAX_FAVORITO":     0.70,
        "ALPHA":            0.75,
        "BETA":             0.25,
        "TOTAL_EQUIPOS":    32,
        "usa_h2h":          True,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  False,
        "experiencia_db":   {},
        "PESO_BASE":        0.70,
        "PESO_H2H":         0.18,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.12,
    },

    # ── CONMEBOL Sudamericana ───────────────────────────────────────────────
    # Similar a Libertadores pero con equipos de menor jerarquía promedio.
    "sudamericana": {
        "nombre":           "CONMEBOL Sudamericana",
        "liga_key":          None,
        "K_LOGISTICO":      3.9,
        "MAX_FAVORITO":     0.71,
        "ALPHA":            0.76,
        "BETA":             0.24,
        "TOTAL_EQUIPOS":    32,
        "usa_h2h":          True,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  True,
        "experiencia_db":   {},
        "PESO_BASE":        0.72,
        "PESO_H2H":         0.16,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.12,
    },

    # ── UEFA Europa League ──────────────────────────────────────────────────
    # Muy parejo: equipos del top 3-6 de sus ligas nacionales.
    # Poco H2H reciente en el mismo torneo.
    "europa_league": {
        "nombre":           "UEFA Europa League",
        "liga_key":          None,
        "K_LOGISTICO":      3.6,
        "MAX_FAVORITO":     0.74,
        "ALPHA":            0.82,
        "BETA":             0.18,
        "TOTAL_EQUIPOS":    32,
        "usa_h2h":          True,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  False,
        "experiencia_db":   {},
        "PESO_BASE":        0.78,
        "PESO_H2H":         0.12,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.10,
    },

    # ── UEFA Champions League ───────────────────────────────────────────────
    # El torneo más parejo del mundo a nivel de clubes.
    # Poisson domina casi completamente.
    "champions_league": {
        "nombre":           "UEFA Champions League",
        "liga_key":          None,
        "K_LOGISTICO":      3.5,
        "MAX_FAVORITO":     0.75,
        "ALPHA":            0.85,
        "BETA":             0.15,
        "TOTAL_EQUIPOS":    32,
        "usa_h2h":          True,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  True,
        "experiencia_db":   {},
        "PESO_BASE":        0.80,
        "PESO_H2H":         0.12,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.08,
    },

    # ── Fase regular genérica (para uso con el otro modelo) ─────────────────
    "fase_regular": {
        "nombre":           "Fase Regular",
        "liga_key":          "mex.1",
        "K_LOGISTICO":      4.2,
        "MAX_FAVORITO":     0.68,
        "ALPHA":            0.75,
        "BETA":             0.25,
        "TOTAL_EQUIPOS":    18,
        "usa_h2h":          False,
        "usa_experiencia":  False,
        "usa_vuelta_casa":  False,
        "experiencia_db":   {},
        "PESO_BASE":        1.00,
        "PESO_H2H":         0.00,
        "PESO_EXPERIENCIA": 0.00,
        "PESO_VUELTA_CASA": 0.00,
    },
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

def normalizar_posicion(posicion, total_equipos):
    return (total_equipos - posicion) / (total_equipos - 1)

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
# PROMEDIO DE LIGA
# =============================

def calcular_promedio_liga(db):
    equipos = [e for e in db.values() if e.get("partidos", 0) > 0]
    if not equipos:
        return 1.35
    return sum(e.get("goles_favor_promedio", 0) for e in equipos) / len(equipos)


# =============================
# CONFIANZA POR JORNADA
# =============================

def peso_confianza(partidos_jugados):
    if partidos_jugados < 5:
        return 0.30
    elif partidos_jugados < 10:
        return 0.65
    else:
        return 1.0


# =============================
# IPO e ISD
# =============================

def calcular_ipo(equipo, es_local, promedio_liga):
    peso = peso_confianza(equipo.get("partidos", 0))
    ataque_normalizado = equipo["goles_favor_promedio"] / promedio_liga if promedio_liga else 1.0
    ataque_normalizado = peso * ataque_normalizado + (1 - peso) * 1.0
    modificador_forma     = 0.85 + (equipo["forma_ponderada"] * 0.30)
    modificador_localidad = equipo["win_rate_local"] if es_local else equipo["win_rate_visita"]
    modificador_localidad = 0.80 + (modificador_localidad * 0.40)
    return ataque_normalizado * modificador_forma * modificador_localidad


def calcular_isd(equipo, promedio_liga):
    peso = peso_confianza(equipo.get("partidos", 0))
    if equipo["goles_contra_promedio"] == 0:
        defensa_normalizada = 2.0
    else:
        defensa_normalizada = promedio_liga / equipo["goles_contra_promedio"]
    defensa_normalizada = peso * defensa_normalizada + (1 - peso) * 1.0
    modificador_streak = 1.0 + (normalizar_streak(equipo["imbatido_streak"]) * 0.20)
    return defensa_normalizada * modificador_streak


def calcular_lambdas(equipo_local, equipo_visitante, promedio_liga):
    ipo_l = calcular_ipo(equipo_local,     es_local=True,  promedio_liga=promedio_liga)
    ipo_v = calcular_ipo(equipo_visitante, es_local=False, promedio_liga=promedio_liga)
    isd_l = calcular_isd(equipo_local,     promedio_liga=promedio_liga)
    isd_v = calcular_isd(equipo_visitante, promedio_liga=promedio_liga)
    lambda_local     = limitar(ipo_l * isd_v * promedio_liga, 0.3, 5.0)
    lambda_visitante = limitar(ipo_v * isd_l * promedio_liga, 0.3, 5.0)
    return lambda_local, lambda_visitante


def probabilidades_poisson(lambda_local, lambda_visitante, max_goles=7):
    from math import exp, factorial
    def pmf(k, lam):
        return (lam ** k) * exp(-lam) / factorial(k)
    p_l = p_e = p_v = 0.0
    for i in range(max_goles + 1):
        for j in range(max_goles + 1):
            p = pmf(i, lambda_local) * pmf(j, lambda_visitante)
            if   i > j: p_l += p
            elif i == j: p_e += p
            else:        p_v += p
    total = p_l + p_e + p_v
    return p_l/total, p_e/total, p_v/total


# =============================
# FUERZA BASE
# =============================

def calcular_fuerza_base(equipo, es_local, cfg):
    PESO_FORMA        = 0.30
    PESO_WINRATE      = 0.22
    PESO_GOLES_FAVOR  = 0.12
    PESO_GOLES_CONTRA = 0.12
    PESO_POSICION     = 0.08
    PESO_TENDENCIA    = 0.06
    PESO_STREAK       = 0.10

    forma          = equipo["forma_ponderada"]
    win_rate       = equipo["win_rate_local"] if es_local else equipo["win_rate_visita"]
    goles_favor    = normalizar_goles_favor(equipo["goles_favor_promedio"])
    goles_contra   = normalizar_goles_contra(equipo["goles_contra_promedio"])
    posicion       = normalizar_posicion(equipo["posicion"], cfg["TOTAL_EQUIPOS"])
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
        ea = normalizar_nombre(val.get("equipo_a", ""))
        eb = normalizar_nombre(val.get("equipo_b", ""))
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

    # Intenta clausura/apertura para Liga MX, o partidos genéricos para otros torneos
    partidos_a = cruce.get("clausura_2026") or cruce.get("partidos_recientes") or []
    partidos_b = cruce.get("apertura_2025", [])

    wr_a, n_a = win_rate_para(partidos_a, nombre_local)
    wr_b, n_b = win_rate_para(partidos_b, nombre_local)
    total      = n_a + n_b

    if total == 0:
        return 0.5, 0, 0, []

    if wr_a is None:
        score = wr_b
    elif wr_b is None:
        score = wr_a
    else:
        score = (wr_a * 0.60) + (wr_b * 0.40)

    partidos_recientes = (partidos_a + partidos_b)[:5]
    return limitar(score, 0.0, 1.0), n_a, n_b, partidos_recientes


def contar_resultados_h2h(partidos_h2h, nombre_local, nombre_visitante):
    wins_local = wins_visita = empates = 0
    for p in partidos_h2h:
        gl = p["goles_local"]
        gv = p["goles_visitante"]
        es_local = normalizar_nombre(p["local"]) == normalizar_nombre(nombre_local)
        if gl == gv:
            empates += 1
        elif gl > gv:
            if es_local: wins_local  += 1
            else:        wins_visita += 1
        else:
            if es_local: wins_visita += 1
            else:        wins_local  += 1
    return wins_local, empates, wins_visita


def get_experiencia(nombre, experiencia_db):
    if not experiencia_db:
        return 0.50
    key = normalizar_nombre(nombre)
    if key in experiencia_db:
        return experiencia_db[key]
    for k, v in experiencia_db.items():
        if k in key or key in k:
            return v
    return 0.50


# =============================
# EMPATE
# =============================

PESO_EMPATE_BASE      = 0.20
PESO_EMPATE_HISTORICO = 0.65
PESO_EMPATE_MOMENTUM  = 0.15

def calcular_prob_empate(f_local, f_visitante, equipo_local, equipo_visitante):
    diferencia = abs(f_local - f_visitante)
    base = limitar(0.28 - (diferencia / 0.40) * 0.18, 0.10, 0.28)

    tasa_local     = calcular_tasa_empate(equipo_local,     es_local=True)
    tasa_visitante = calcular_tasa_empate(equipo_visitante, es_local=False)
    historico = max(tasa_local, tasa_visitante)

    d_local     = contar_empates_recientes(equipo_local.get("ultimos_5", []))
    d_visitante = contar_empates_recientes(equipo_visitante.get("ultimos_5", []))
    momentum    = limitar((d_local + d_visitante) * 0.07, 0.0, 0.35)

    return limitar(
        base      * PESO_EMPATE_BASE      +
        historico * PESO_EMPATE_HISTORICO +
        momentum  * PESO_EMPATE_MOMENTUM,
        0.08, 0.46
    )


# =============================
# VUELTA EN CASA
# =============================

def quien_juega_vuelta_en_casa(local, visitante):
    return "local" if local["posicion"] <= visitante["posicion"] else "visitante"


# =============================
# PROBABILIDADES — MOTOR CENTRAL
# =============================

def predecir_probabilidades(
    equipo_local, equipo_visitante,
    h2h_data, nombre_local, nombre_visitante,
    promedio_liga, cfg,
):
    """
    Motor único de predicción.
    cfg = perfil del torneo (PERFILES_TORNEO[slug]).
    """

    # ── Capa 1: Poisson ─────────────────────────────────────────────────────
    lambda_local, lambda_visitante = calcular_lambdas(
        equipo_local, equipo_visitante, promedio_liga
    )
    p_local, p_empate, p_visitante = probabilidades_poisson(lambda_local, lambda_visitante)

    # ── Capa 2: Fuerza base ──────────────────────────────────────────────────
    fb_local     = calcular_fuerza_base(equipo_local,     es_local=True,  cfg=cfg)
    fb_visitante = calcular_fuerza_base(equipo_visitante, es_local=False, cfg=cfg)

    # H2H — solo si el perfil lo activa
    if cfg["usa_h2h"] and h2h_data:
        h2h_local, n_a, n_b, partidos_h2h = calcular_h2h_score(
            nombre_local, nombre_visitante, h2h_data
        )
    else:
        h2h_local, n_a, n_b, partidos_h2h = 0.5, 0, 0, []
    h2h_visitante = 1.0 - h2h_local

    # Experiencia — solo si el perfil lo activa
    if cfg["usa_experiencia"]:
        exp_local     = get_experiencia(nombre_local,     cfg["experiencia_db"])
        exp_visitante = get_experiencia(nombre_visitante, cfg["experiencia_db"])
    else:
        exp_local = exp_visitante = 0.50   # neutro: no penaliza ni beneficia

    # Vuelta en casa — solo si el perfil lo activa
    if cfg["usa_vuelta_casa"]:
        vuelta       = quien_juega_vuelta_en_casa(equipo_local, equipo_visitante)
        vuelta_local = 1.0 if vuelta == "local" else 0.0
        vuelta_visit = 1.0 - vuelta_local
    else:
        vuelta       = "ninguno"
        vuelta_local = vuelta_visit = 0.0

    # Fuerza compuesta con pesos del perfil
    PESO_BASE        = cfg["PESO_BASE"]
    PESO_H2H         = cfg["PESO_H2H"]
    PESO_EXPERIENCIA = cfg["PESO_EXPERIENCIA"]
    PESO_VUELTA_CASA = cfg["PESO_VUELTA_CASA"]

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

    # Score logístico con K del perfil
    score   = f_local - f_visitante
    ratio_l = 1 / (1 + math.exp(-cfg["K_LOGISTICO"] * score))
    ratio_v = 1 - ratio_l

    if ratio_l > cfg["MAX_FAVORITO"]:
        ratio_l = cfg["MAX_FAVORITO"]
        ratio_v = 1 - ratio_l
    if ratio_v > cfg["MAX_FAVORITO"]:
        ratio_v = cfg["MAX_FAVORITO"]
        ratio_l = 1 - ratio_v

    # Empate y distribución
    prob_empate_f = calcular_prob_empate(f_local, f_visitante, equipo_local, equipo_visitante)
    restante      = 1.0 - prob_empate_f
    prob_local_f     = restante * ratio_l
    prob_visitante_f = restante * ratio_v

    # Fusión Poisson + fuerza con pesos del perfil
    ALPHA = cfg["ALPHA"]
    BETA  = cfg["BETA"]

    prob_local     = ALPHA * p_local     + BETA * prob_local_f
    prob_empate    = ALPHA * p_empate    + BETA * prob_empate_f
    prob_visitante = ALPHA * p_visitante + BETA * prob_visitante_f

    total          = prob_local + prob_empate + prob_visitante
    prob_local    /= total
    prob_empate   /= total
    prob_visitante /= total

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
        "n_h2h_a":          n_a,
        "n_h2h_b":          n_b,
        "partidos_h2h":     partidos_h2h,
        "vuelta_en_casa":   vuelta,
        "exp_local":        exp_local,
        "exp_visitante":    exp_visitante,
        "fb_local":         fb_local,
        "fb_visitante":     fb_visitante,
        "lambda_local":     lambda_local,
        "lambda_visitante": lambda_visitante,
    }


# =============================
# ANÁLISIS ESTRUCTURADO
# =============================

def generar_analisis(local, visitante, resultado, nombre_local, nombre_visitante, cfg):
    factores = []

    # ── 1. FORMA RECIENTE ────────────────────────────────────────────────────
    fl    = local["forma_ponderada"]
    fv    = visitante["forma_ponderada"]
    ul5_l = local.get("ultimos_5", [])
    ul5_v = visitante.get("ultimos_5", [])
    wins_l   = ul5_l.count("W"); losses_l = ul5_l.count("L")
    wins_v   = ul5_v.count("W"); losses_v = ul5_v.count("L")

    if fl > fv:
        interp = (f"{nombre_local} llega con mejor momentum: índice {fl:.2f}/1.0 "
                  f"frente a {fv:.2f}/1.0 de {nombre_visitante}. "
                  f"Últimos 5: {wins_l}V/{ul5_l.count('D')}E/{losses_l}D vs "
                  f"{wins_v}V/{ul5_v.count('D')}E/{losses_v}D.")
    elif fv > fl:
        interp = (f"{nombre_visitante} llega con mejor momentum: índice {fv:.2f}/1.0 "
                  f"frente a {fl:.2f}/1.0 de {nombre_local}. "
                  f"Últimos 5: {wins_v}V/{ul5_v.count('D')}E/{losses_v}D vs "
                  f"{wins_l}V/{ul5_l.count('D')}E/{losses_l}D.")
    else:
        interp = (f"Momentum similar: {nombre_local} {fl:.2f}/1.0 — "
                  f"{nombre_visitante} {fv:.2f}/1.0.")

    factores.append({
        "factor":         "Forma reciente",
        "impacto":        nivel_impacto(abs(fl - fv)),
        "tipo":           "forma",
        "local":          {"valor": round(fl, 2), "ultimos_5": ul5_l, "nombre": nombre_local},
        "visitante":      {"valor": round(fv, 2), "ultimos_5": ul5_v, "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 2. RENDIMIENTO SITUACIONAL ───────────────────────────────────────────
    wrl  = local["win_rate_local"]
    wrv  = visitante["win_rate_visita"]
    gl_l = local.get("ganados_local", 0);   el_l = local.get("empatados_local", 0);   pl_l = local.get("perdidos_local", 0)
    gv_v = visitante.get("ganados_visita", 0); ev_v = visitante.get("empatados_visita", 0); pv_v = visitante.get("perdidos_visita", 0)

    if wrl >= 0.55 and wrv <= 0.30:
        interp = (f"Contraste marcado: {nombre_local} gana el {wrl*100:.0f}% en casa "
                  f"({gl_l}G/{el_l}E/{pl_l}P), {nombre_visitante} solo el {wrv*100:.0f}% de visita "
                  f"({gv_v}G/{ev_v}E/{pv_v}P). La localía es determinante.")
    elif wrl >= 0.55:
        interp = (f"{nombre_local} domina en casa: {wrl*100:.0f}% ({gl_l}G/{el_l}E/{pl_l}P). "
                  f"{nombre_visitante}: {wrv*100:.0f}% de visita ({gv_v}G/{ev_v}E/{pv_v}P).")
    elif wrv <= 0.30:
        interp = (f"{nombre_visitante} sufre de visita: {wrv*100:.0f}% ({gv_v}G/{ev_v}E/{pv_v}P). "
                  f"{nombre_local} en casa: {wrl*100:.0f}% ({gl_l}G/{el_l}E/{pl_l}P).")
    else:
        interp = (f"Equilibrio situacional: {nombre_local} {wrl*100:.0f}% local "
                  f"— {nombre_visitante} {wrv*100:.0f}% visita.")

    factores.append({
        "factor":    "Rendimiento situacional",
        "impacto":   nivel_impacto(abs(wrl - wrv)),
        "tipo":      "barras",
        "local":     {"etiqueta": "Win rate local",  "valor": round(wrl * 100, 1), "detalle": f"{gl_l}G/{el_l}E/{pl_l}P", "nombre": nombre_local},
        "visitante": {"etiqueta": "Win rate visita", "valor": round(wrv * 100, 1), "detalle": f"{gv_v}G/{ev_v}E/{pv_v}P", "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 3. POTENCIAL OFENSIVO Y DEFENSIVO ────────────────────────────────────
    gf_l = local["goles_favor_promedio"];   gc_l = local["goles_contra_promedio"]
    gf_v = visitante["goles_favor_promedio"]; gc_v = visitante["goles_contra_promedio"]
    ventaja_of = gf_l - gf_v; ventaja_def = gc_v - gc_l

    if ventaja_of >= 0.4 and ventaja_def >= 0.3:
        interp = (f"Superioridad integral de {nombre_local}: {gf_l:.2f} goles/partido "
                  f"(vs {gf_v:.2f}) y solo {gc_l:.2f} recibidos (vs {gc_v:.2f}).")
    elif ventaja_of >= 0.4:
        interp = (f"{nombre_local} más ofensivo: {gf_l:.2f} vs {gf_v:.2f} goles/partido. "
                  f"Defensa: {gc_l:.2f} vs {gc_v:.2f}.")
    elif ventaja_of <= -0.4:
        interp = (f"{nombre_visitante} más ofensivo: {gf_v:.2f} vs {gf_l:.2f} goles/partido. "
                  f"Defensa: {gc_l:.2f} vs {gc_v:.2f}.")
    else:
        interp = (f"Producción similar: {nombre_local} {gf_l:.2f} goles/partido — "
                  f"{nombre_visitante} {gf_v:.2f}. Defensa: {gc_l:.2f} vs {gc_v:.2f}.")

    factores.append({
        "factor":    "Potencial ofensivo y defensivo",
        "impacto":   nivel_impacto(abs(ventaja_of)*0.5 + abs(ventaja_def)*0.5),
        "tipo":      "doble_barra",
        "local":     {"nombre": nombre_local,     "goles_favor": round(gf_l,2), "goles_contra": round(gc_l,2)},
        "visitante": {"nombre": nombre_visitante, "goles_favor": round(gf_v,2), "goles_contra": round(gc_v,2)},
        "interpretacion": interp,
    })

    # ── 4. H2H (solo si el perfil lo activa y hay datos) ────────────────────
    n_total = resultado["n_h2h_a"] + resultado["n_h2h_b"]
    if cfg["usa_h2h"] and n_total > 0:
        h2h_score = resultado["h2h_local"]
        wins_l, empates, wins_v = contar_resultados_h2h(
            resultado["partidos_h2h"], nombre_local, nombre_visitante
        )
        if h2h_score >= 0.60:
            interp = (f"{nombre_local} domina el historial: {wins_l}V/{empates}E/{wins_v}D "
                      f"en {n_total} enfrentamientos recientes.")
        elif h2h_score <= 0.40:
            interp = (f"{nombre_visitante} lleva ventaja: {wins_v}V/{empates}E/{wins_l}D "
                      f"en {n_total} enfrentamientos recientes.")
        else:
            interp = (f"Historial equilibrado: {wins_l}V/{empates}E/{wins_v}D "
                      f"en {n_total} enfrentamientos. Sin dominancia clara.")

        factores.append({
            "factor":        "Historial directo",
            "impacto":       nivel_impacto(abs(h2h_score - 0.5) * 2),
            "tipo":          "h2h",
            "local":         {"nombre": nombre_local,     "victorias": wins_l},
            "visitante":     {"nombre": nombre_visitante, "victorias": wins_v},
            "empates":       empates,
            "partidos":      resultado["partidos_h2h"],
            "total":         n_total,
            "interpretacion": interp,
        })

    # ── 5. EXPERIENCIA ELIMINATORIA (solo Liga MX) ───────────────────────────
    if cfg["usa_experiencia"]:
        exp_l  = resultado["exp_local"]
        exp_v  = resultado["exp_visitante"]
        diff   = exp_l - exp_v
        if abs(diff) >= 0.15:
            eq_exp   = nombre_local if diff > 0 else nombre_visitante
            eq_inexp = nombre_visitante if diff > 0 else nombre_local
            interp = (f"{eq_exp} tiene mayor experiencia eliminatoria "
                      f"(índice {max(exp_l,exp_v):.2f} vs {min(exp_l,exp_v):.2f} de {eq_inexp}). "
                      f"La presión de eliminación suele favorecer al más rodado.")
        else:
            interp = (f"Experiencia similar: {nombre_local} {exp_l:.2f} — "
                      f"{nombre_visitante} {exp_v:.2f}. Factor sin impacto decisivo.")

        factores.append({
            "factor":    "Experiencia eliminatoria",
            "impacto":   nivel_impacto(abs(diff)),
            "tipo":      "barras",
            "local":     {"etiqueta": "Índice liguilla", "valor": round(exp_l,2), "nombre": nombre_local},
            "visitante": {"etiqueta": "Índice liguilla", "valor": round(exp_v,2), "nombre": nombre_visitante},
            "interpretacion": interp,
        })

    # ── 6. VUELTA EN CASA (si aplica) ────────────────────────────────────────
    if cfg["usa_vuelta_casa"] and resultado["vuelta_en_casa"] != "ninguno":
        vuelta      = resultado["vuelta_en_casa"]
        eq_vuelta   = nombre_local   if vuelta == "local"     else nombre_visitante
        eq_sin_vuelta = nombre_visitante if vuelta == "local" else nombre_local
        pos_l = local["posicion"]; pos_v = visitante["posicion"]

        interp = (f"{eq_vuelta} jugará la vuelta en casa "
                  f"(posición {pos_l if vuelta=='local' else pos_v} vs "
                  f"{pos_v if vuelta=='local' else pos_l} en tabla). "
                  f"Puede especular en la ida y resolver la eliminatoria ante su afición. "
                  f"{eq_sin_vuelta} deberá avanzar jugando el partido decisivo de visitante.")

        factores.append({
            "factor":        "Ventaja de vuelta en casa",
            "impacto":       "medio",
            "tipo":          "vuelta",
            "equipo_vuelta": eq_vuelta,
            "local":         {"nombre": nombre_local,     "posicion": pos_l},
            "visitante":     {"nombre": nombre_visitante, "posicion": pos_v},
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

def generar_partido(
    id,
    local_nombre,
    visitante_nombre,
    db,
    h2h            = None,
    perfil_slug    = "liguilla_mx",
    archivo_salida = "partidos.json",
):
    """
    Punto de entrada único para generar una proyección.

    Parámetros:
    - perfil_slug: clave de PERFILES_TORNEO
    - h2h: dict con datos de historial directo (None si no aplica)
    - archivo_salida: dónde guardar el resultado
    """
    cfg = PERFILES_TORNEO.get(perfil_slug)
    if not cfg:
        raise ValueError(f"Perfil '{perfil_slug}' no encontrado. "
                         f"Opciones: {list(PERFILES_TORNEO.keys())}")

    local_raw     = obtener_equipo(local_nombre,     db)
    visitante_raw = obtener_equipo(visitante_nombre, db)

    if not local_raw:
        raise ValueError(f"Equipo local no encontrado: '{local_nombre}'")
    if not visitante_raw:
        raise ValueError(f"Equipo visitante no encontrado: '{visitante_nombre}'")

    liga_key  = cfg.get("liga_key")   # slug de competencia principal del perfil
    local     = adaptar_equipo(local_raw,     liga_key=liga_key)
    visitante = adaptar_equipo(visitante_raw, liga_key=liga_key)

    promedio_liga = calcular_promedio_liga(db)
    h2h_data      = h2h or {}

    resultado = predecir_probabilidades(
        local, visitante, h2h_data,
        local_nombre, visitante_nombre,
        promedio_liga, cfg,
    )

    maxima = max(resultado["local"], resultado["empate"], resultado["visitante"])
    if   maxima == resultado["local"]:   pred = local["nombre"]
    elif maxima == resultado["empate"]:  pred = "Empate"
    else:                                pred = visitante["nombre"]

    analisis = generar_analisis(
        local, visitante, resultado,
        local_nombre, visitante_nombre, cfg,
    )

    output = {
        "id":               id,
        "torneo":           cfg["nombre"],
        "perfil":           perfil_slug,
        "local":            local["nombre"],
        "visitante":        visitante["nombre"],
        "logo_local":       local_raw.get("escudo"),
        "logo_visitante":   visitante_raw.get("escudo"),
        "prob_local":       resultado["local"],
        "prob_empate":      resultado["empate"],
        "prob_visitante":   resultado["visitante"],
        "fuerza_local":     resultado["fuerza_local"],
        "fuerza_visitante": resultado["fuerza_visitante"],
        "diferencia":       resultado["diferencia"],
        "confianza":        resultado["confianza"],
        "prediccion":       pred,
        "vuelta_en_casa":   resultado["vuelta_en_casa"],
        "lambda_local":     resultado["lambda_local"],
        "lambda_visitante": resultado["lambda_visitante"],
        "analisis":         analisis,
    }

    guardar_resultado(output, archivo_salida)
    return output


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    # ── Bases de datos disponibles ────────────────────────────────────────────
    # Agrega o quita según los torneos que vayas a proyectar ese día.
    # carpeta → debe existir en scrapper/<CARPETA>/equipos.json
    DBS = {
        # Ligas regulares
        "liga_mx":          cargar_equipos("LIGA-MX"),
        "liga_mx_exp":      cargar_equipos("LIGA-MX-EXPANSION"),
        "premier":          cargar_equipos("PREMIER-LEAGUE"),
        "la_liga":          cargar_equipos("LALIGA"),
        "bundesliga":       cargar_equipos("BUNDESLIGA"),
        "ligue1":           cargar_equipos("LIGUE-1"),
        "eredivisie":       cargar_equipos("EREDIVISIE"),
        "belgian":          cargar_equipos("BELGIAN-PRO-LEAGUE"),
        "brasileirao":      cargar_equipos("BRASILEIRAO-SERIE-A"),
        "mls":              cargar_equipos("MLS"),
        "premiership":      cargar_equipos("SCOTTISH-PREMIERSHIP"),
        "grecia":           cargar_equipos("SUPERLIGA-GRECIA"),
        "rusia":            cargar_equipos("LIGAPREMIER-RUSIA"),
        # Torneos eliminatorios / internacionales
        "liguilla_mx":      cargar_equipos("LIGA-MX"),
        "concacaf_w":       cargar_equipos("CONCACAF-W-CHAMPIONSHIP"),
        "libertadores":     cargar_equipos("LIBERTADORES"),
        "sudamericana":     cargar_equipos("SUDAMERICANA"),
        "europa_league":    cargar_equipos("EUROPA-LEAGUE"),
    }

    # ── H2H disponibles ───────────────────────────────────────────────────────
    # Solo Liga MX tiene H2H por ahora. El resto devuelve {} automáticamente.
    H2H = {
        "liguilla_mx": cargar_h2h("LIGA-MX"),
    }

    # ── Casos a proyectar ─────────────────────────────────────────────────────
    # Formato: (id, local, visitante, db_key, perfil_slug, archivo_salida)
    #
    # db_key      → clave en DBS de arriba
    # perfil_slug → clave en PERFILES_TORNEO:
    #               "fase_regular"        ligas normales (Premier, MX, etc.)
    #               "liguilla_mx"         liguilla Liga MX ida
    #               "concacaf_w_champions" Concacaf W Champions Cup
    #               "concacaf_champions"  Concacaf Champions Cup varonil
    #               "libertadores"        CONMEBOL Libertadores
    #               "sudamericana"        CONMEBOL Sudamericana
    #               "europa_league"       UEFA Europa League
    #               "champions_league"    UEFA Champions League
    #
    # archivo_salida → JSON donde se guardan los resultados
    # ─────────────────────────────────────────────────────────────────────────

    CASOS = [
        # id   local                 visitante              db_key          perfil               salida
        (1,  "Cruz Azul",          "Pumas UNAM",         "liguilla_mx",   "liguilla_mx",     "partidos.json"),
        (2,  "SC Freiburg",         "Aston Villa",        "europa_league", "europa_league",   "partidos.json"),
        (3,  "America Femenil",    "Gotham FC",          "concacaf_w",    "concacaf_w_champions", "partidos.json"),
        (4,  "Washington Spirit",  "Pachuca Femenil",    "concacaf_w",    "concacaf_w_champions", "partidos.json"),
        (5,  "Independiente Santa Fe", "Platense",       "libertadores",  "libertadores",    "partidos.json"),
        (6,  "Boca Juniors",       "Cruzeiro",           "libertadores",  "libertadores",    "partidos.json"),
        (7,  "Liga de Quito",      "Lanús",              "libertadores",  "libertadores",    "partidos.json"),
        (8,  "Penarol",            "Corinthians",        "libertadores",  "libertadores",    "partidos.json"),
        (9,  "Santos",             "San Lorenzo",        "sudamericana",   "sudamericana",    "partidos.json"),
    ]


    # ── Ejecución ─────────────────────────────────────────────────────────────
    print(f"\n🚀 Generando {len(CASOS)} proyecciones...\n" + "="*55)

    for caso in CASOS:
        id, local, visitante, db_key, perfil, salida = caso
        try:
            db  = DBS[db_key]
            h2h = H2H.get(db_key, {})   # {} si no hay H2H para ese torneo

            p = generar_partido(
                id, local, visitante,
                db=db, h2h=h2h,
                perfil_slug=perfil,
                archivo_salida=salida,
            )
            print(f"  ⚽ {p['local']:<25} vs {p['visitante']:<25}")
            print(f"     {p['prob_local']:.1%} / {p['prob_empate']:.1%} / {p['prob_visitante']:.1%}"
                  f"  →  {p['prediccion']}  [{p['confianza']}]")
            print(f"     Torneo: {p['torneo']} | Guardado: {salida}")
            print()
        except Exception as e:
            print(f"  ❌ Error en partido {id} ({local} vs {visitante}): {e}")
            print()

    print("✅ Proyecciones completadas.")
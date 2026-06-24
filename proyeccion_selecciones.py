import json
import math
import os


# =============================
# CARGAR DATOS
# =============================

def cargar_selecciones(carpeta):
    ruta = os.path.join("mundial", carpeta, "selecciones.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_fixture(carpeta):
    ruta = os.path.join("mundial", carpeta, "fixture.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_h2h(carpeta):
    ruta = os.path.join("mundial", carpeta, "h2h.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def obtener_seleccion(nombre, db):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    key = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        key = key.replace(a, b)
    if key in db:
        return db[key]
    for k, v in db.items():
        norm_k = k.lower().replace(" ", "")
        for a, b in reemplazos.items():
            norm_k = norm_k.replace(a, b)
        if norm_k == key:
            return v
    return None


# =============================
# MODELO DE ALTITUD
# =============================

def calcular_factor_altitud(altitud_sede, altitud_base_equipo):
    diferencia = altitud_sede - altitud_base_equipo
    if diferencia <= 0:
        return 1.0
    penalizacion = diferencia / 20000.0
    return max(0.80, 1.0 - penalizacion)


def modificador_altitud_goles(altitud_sede, altitud_base_equipo):
    if altitud_sede < 1500:
        return 1.0
    elif altitud_sede < 2500:
        return 1.03
    elif altitud_sede < 3200:
        return 1.06
    else:
        return 1.09


# =============================
# NORMALIZACIÓN
# =============================

def normalizar_nombre(nombre):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


def limitar(v, a, b):
    return max(a, min(v, b))


def normalizar_goles_favor(promedio, maximo=3.5):
    return limitar(promedio / maximo, 0.0, 1.0)


def normalizar_goles_contra(promedio, maximo=3.5):
    return limitar(1.0 - (promedio / maximo), 0.0, 1.0)


def normalizar_streak(streak):
    return limitar(streak / 8.0, 0.0, 1.0)


def nivel_impacto(diferencia_normalizada):
    if diferencia_normalizada >= 0.25:
        return "alto"
    elif diferencia_normalizada >= 0.12:
        return "medio"
    else:
        return "bajo"


# =============================
# RANKING FIFA NORMALIZADO
# =============================

def normalizar_ranking_fifa(seleccion):
    ranking = seleccion.get("ranking_fifa", 999)
    puntos  = seleccion.get("puntos_fifa",  0.0) or 0.0

    if puntos > 0:
        return limitar((puntos - 800) / 1050, 0.0, 1.0)
    else:
        ranking_efectivo = min(ranking, 210)
        return limitar(1.0 - (ranking_efectivo - 1) / 209, 0.0, 1.0)


# =============================
# ADAPTADOR DE SELECCIÓN
# =============================

def adaptar_seleccion(seleccion_raw):
    forma_final = seleccion_raw.get("forma", 0.0) or 0.0
    if forma_final == 0.0:
        fo = seleccion_raw.get("forma_oficial",   0.0) or 0.0
        fa = seleccion_raw.get("forma_amistosos", 0.0) or 0.0
        if fo > 0 and fa > 0:
            forma_final = (fo + fa) / 2.0
        elif fo > 0:
            forma_final = fo
        elif fa > 0:
            forma_final = fa
        else:
            forma_final = 0.5

    ul5_mixto    = seleccion_raw.get("ultimos_5",         []) or []
    ul5_oficial  = seleccion_raw.get("ultimos_5_oficial",  []) or []
    ul5_amistoso = seleccion_raw.get("ultimos_5_amistoso", []) or []

    p_of  = seleccion_raw.get("partidos_oficial",  0) or 0
    p_am  = seleccion_raw.get("partidos_amistoso", 0) or 0
    gf_of = seleccion_raw.get("goles_favor_oficial",   0.0) or 0.0
    gc_of = seleccion_raw.get("goles_contra_oficial",  0.0) or 0.0
    gf_am = seleccion_raw.get("goles_favor_amistoso",  0.0) or 0.0
    gc_am = seleccion_raw.get("goles_contra_amistoso", 0.0) or 0.0

    total_p = p_of + p_am
    if total_p > 0:
        gf_ponderado = (gf_of * p_of + gf_am * p_am) / total_p
        gc_ponderado = (gc_of * p_of + gc_am * p_am) / total_p
    elif gf_of > 0:
        gf_ponderado, gc_ponderado = gf_of, gc_of
    elif gf_am > 0:
        gf_ponderado, gc_ponderado = gf_am, gc_am
    else:
        gf_ponderado, gc_ponderado = 1.0, 1.0

    total_partidos  = p_of + p_am
    total_ganados   = (seleccion_raw.get("ganados_oficial",   0) or 0) + (seleccion_raw.get("ganados_amistoso",   0) or 0)
    total_empatados = (seleccion_raw.get("empatados_oficial", 0) or 0) + (seleccion_raw.get("empatados_amistoso", 0) or 0)
    total_perdidos  = (seleccion_raw.get("perdidos_oficial",  0) or 0) + (seleccion_raw.get("perdidos_amistoso",  0) or 0)

    empatados_local  = (seleccion_raw.get("empatados_local",  0) or 0)
    empatados_visita = (seleccion_raw.get("empatados_visita", 0) or 0)

    return {
        "nombre":            seleccion_raw.get("nombre", ""),
        "escudo":            seleccion_raw.get("escudo", ""),
        "confederacion":     seleccion_raw.get("confederacion", ""),
        "ranking_fifa":      seleccion_raw.get("ranking_fifa", 999),
        "puntos_fifa":       seleccion_raw.get("puntos_fifa",  0.0) or 0.0,
        "altitud_base":      seleccion_raw.get("altitud_base", 0),
        "forma_ponderada":   forma_final,
        "imbatido_streak":   seleccion_raw.get("imbatido_streak", 0),
        "ultimos_5":         ul5_mixto,
        "win_rate_local":    seleccion_raw.get("win_rate_local",  0.5),
        "win_rate_visita":   seleccion_raw.get("win_rate_visita", 0.5),
        "win_rate_neutro":   seleccion_raw.get("win_rate_neutro", 0.5),
        "goles_favor_promedio":  round(gf_ponderado, 3),
        "goles_contra_promedio": round(gc_ponderado, 3),
        "partidos":   total_partidos,
        "ganados":    total_ganados,
        "empatados":  total_empatados,
        "perdidos":   total_perdidos,
        "partidos_local":   seleccion_raw.get("partidos_local",  0),
        "ganados_local":    seleccion_raw.get("ganados_local",   0),
        "empatados_local":  empatados_local,
        "perdidos_local":   seleccion_raw.get("perdidos_local",  0),
        "partidos_visita":  seleccion_raw.get("partidos_visita",  0),
        "ganados_visita":   seleccion_raw.get("ganados_visita",   0),
        "empatados_visita": empatados_visita,
        "perdidos_visita":  seleccion_raw.get("perdidos_visita",  0),
        "partidos_oficial":   p_of,
        "forma_oficial":      seleccion_raw.get("forma_oficial",   0.0) or 0.0,
        "ultimos_5_oficial":  ul5_oficial,
        "partidos_amistoso":  p_am,
        "forma_amistosos":    seleccion_raw.get("forma_amistosos", 0.0) or 0.0,
        "ultimos_5_amistoso": ul5_amistoso,
    }


# =============================
# PERFILES DE COMPETENCIA
# =============================

PERFILES_SELECCIONES = {
    "amistoso": {
        "nombre":       "Amistoso Internacional",
        "K_LOGISTICO":  2.8,
        "MAX_FAVORITO": 0.56,
        "ALPHA":        0.60,
        "BETA":         0.40,
        "usa_h2h":      False,
        "usa_altitud":  True,
        "PESO_BASE":    0.90,
        "PESO_H2H":     0.00,
        "PESO_ALTITUD": 0.10,
    },
    "eliminatoria_conmebol": {
        "nombre":       "Eliminatoria CONMEBOL",
        "K_LOGISTICO":  4.2,
        "MAX_FAVORITO": 0.62,
        "ALPHA":        0.70,
        "BETA":         0.30,
        "usa_h2h":      True,
        "usa_altitud":  True,
        "PESO_BASE":    0.66,
        "PESO_H2H":     0.24,
        "PESO_ALTITUD": 0.10,
    },
    "eliminatoria_concacaf": {
        "nombre":       "Eliminatoria CONCACAF",
        "K_LOGISTICO":  4.0,
        "MAX_FAVORITO": 0.63,
        "ALPHA":        0.72,
        "BETA":         0.28,
        "usa_h2h":      True,
        "usa_altitud":  True,
        "PESO_BASE":    0.71,
        "PESO_H2H":     0.21,
        "PESO_ALTITUD": 0.08,
    },
    "copa_america": {
        "nombre":       "Copa América / Torneo Continental",
        "K_LOGISTICO":  4.1,
        "MAX_FAVORITO": 0.63,
        "ALPHA":        0.71,
        "BETA":         0.29,
        "usa_h2h":      True,
        "usa_altitud":  True,
        "PESO_BASE":    0.70,
        "PESO_H2H":     0.22,
        "PESO_ALTITUD": 0.08,
    },
    "mundial_grupos": {
        "nombre":       "Copa del Mundo FIFA — Fase de Grupos",
        "K_LOGISTICO":  2.2,
        "MAX_FAVORITO": 0.39,
        "ALPHA":        0.72,
        "BETA":         0.28,
        "usa_h2h":      True,
        "usa_altitud":  True,
        "PESO_BASE":    0.66,
        "PESO_H2H":     0.22,
        "PESO_ALTITUD": 0.12,
    },
    "mundial_eliminatoria": {
        "nombre":       "Copa del Mundo FIFA — Eliminatorias",
        "K_LOGISTICO":  3.6,
        "MAX_FAVORITO": 0.60,
        "ALPHA":        0.63,
        "BETA":         0.37,
        "usa_h2h":      True,
        "usa_altitud":  True,
        "PESO_BASE":    0.63,
        "PESO_H2H":     0.25,
        "PESO_ALTITUD": 0.12,
    },
}


# =============================
# PROMEDIO GLOBAL DE GOL
# =============================

PROMEDIO_GLOBAL_MIN = 1.50
PROMEDIO_GLOBAL_MAX = 2.20

def calcular_promedio_global(db):
    selecciones = [v for v in db.values() if v.get("partidos", 0) > 0]
    if not selecciones:
        return 1.75
    raw = sum(v.get("goles_favor_promedio", 1.75) for v in selecciones) / len(selecciones)
    return limitar(raw, PROMEDIO_GLOBAL_MIN, PROMEDIO_GLOBAL_MAX)


# =============================
# CONFIANZA POR MUESTRA
# =============================

def peso_confianza(partidos_jugados):
    if partidos_jugados < 3:
        return 0.35
    elif partidos_jugados < 6:
        return 0.60
    elif partidos_jugados < 10:
        return 0.80
    else:
        return 1.0


# =============================
# HELPER: WIN RATE CON FALLBACK
# =============================
# FIX: cuando un equipo no tiene partidos en una situación (visita/local/neutro),
# en lugar de usar el valor 0.0 del JSON se regresa a 0.5 (neutral).
# Esto evita que equipos como Argentina, con 0 partidos de visita,
# colapsen su fuerza base por un win_rate_visita de 0.0 sin respaldo estadístico.

def _wr_con_fallback(seleccion, es_neutro, es_local):
    """
    Devuelve (wr_raw, partidos_sit).
    Si no hay muestra para la situación concreta, retorna wr_raw=0.5.
    Para partidos neutros se suma local+visita como proxy de muestra total.
    """
    if es_neutro:
        p_sit  = seleccion.get("partidos_local", 0) + seleccion.get("partidos_visita", 0)
        wr_raw = seleccion.get("win_rate_neutro", 0.5)
        if p_sit == 0:
            wr_raw = 0.5
    elif es_local:
        p_sit  = seleccion.get("partidos_local", 0)
        wr_raw = seleccion.get("win_rate_local", 0.5)
        if p_sit == 0:
            wr_raw = 0.5
    else:
        p_sit  = seleccion.get("partidos_visita", 0)
        wr_raw = seleccion.get("win_rate_visita", 0.5)
        if p_sit == 0:
            wr_raw = 0.5
    return wr_raw, p_sit


# =============================
# IPO e ISD
# =============================

def calcular_ipo_seleccion(equipo, contexto, promedio_global):
    peso         = peso_confianza(equipo.get("partidos", 0))
    altitud_sede = contexto.get("altitud_sede", 0)
    altitud_base = equipo.get("altitud_base", 0)
    es_local     = contexto.get("es_local", False)
    es_neutro    = contexto.get("es_neutro", False)

    ataque = equipo["goles_favor_promedio"] / promedio_global if promedio_global else 1.0
    ataque = peso * ataque + (1 - peso) * 1.0

    mod_forma = 0.85 + (equipo["forma_ponderada"] * 0.30)

    # FIX: usar helper con fallback en lugar de acceso directo al JSON
    wr_raw, _ = _wr_con_fallback(equipo, es_neutro, es_local)
    mod_localidad = 0.80 + (wr_raw * 0.40)

    factor_alt    = calcular_factor_altitud(altitud_sede, altitud_base)
    mod_goles_alt = modificador_altitud_goles(altitud_sede, altitud_base)

    ipo = ataque * mod_forma * mod_localidad * factor_alt * mod_goles_alt
    return ipo


def calcular_isd_seleccion(equipo, contexto, promedio_global):
    peso         = peso_confianza(equipo.get("partidos", 0))
    altitud_sede = contexto.get("altitud_sede", 0)
    altitud_base = equipo.get("altitud_base", 0)

    gc = equipo["goles_contra_promedio"]
    if gc == 0:
        isd_raw = 2.5
    else:
        isd_raw = promedio_global / gc

    techo_isd = 1.8 + (peso * 0.7)
    isd_raw   = limitar(isd_raw, 0.5, techo_isd)
    isd       = peso * isd_raw + (1 - peso) * 1.0

    mod_streak = 1.0 + (normalizar_streak(equipo["imbatido_streak"]) * 0.10)
    isd *= mod_streak

    factor_alt = calcular_factor_altitud(altitud_sede, altitud_base)
    isd *= (0.7 + factor_alt * 0.3)

    return limitar(isd, 0.5, 2.5)


def calcular_lambdas(seleccion_local, seleccion_visitante, contexto, promedio_global):
    contexto_l = {**contexto, "es_local": True,  "es_neutro": contexto.get("es_neutro", False)}
    contexto_v = {**contexto, "es_local": False, "es_neutro": contexto.get("es_neutro", False)}

    ipo_l = calcular_ipo_seleccion(seleccion_local,     contexto_l, promedio_global)
    ipo_v = calcular_ipo_seleccion(seleccion_visitante, contexto_v, promedio_global)
    isd_l = calcular_isd_seleccion(seleccion_local,     contexto_l, promedio_global)
    isd_v = calcular_isd_seleccion(seleccion_visitante, contexto_v, promedio_global)

    lambda_local     = limitar((ipo_l * promedio_global) / isd_v, 0.2, 5.0)
    lambda_visitante = limitar((ipo_v * promedio_global) / isd_l, 0.2, 5.0)
    return lambda_local, lambda_visitante


def probabilidades_poisson(lambda_local, lambda_visitante, max_goles=8):
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
# MARCADORES MÁS PROBABLES
# =============================

def ajustar_lambdas_por_probabilidades(lambda_local, lambda_visitante,
                                        prob_local, prob_visitante):
    suma_lv = prob_local + prob_visitante
    if suma_lv <= 0:
        return lambda_local, lambda_visitante

    ratio_modelo  = prob_local / suma_lv
    suma_lambda   = lambda_local + lambda_visitante
    if suma_lambda <= 0:
        return lambda_local, lambda_visitante

    ratio_poisson = lambda_local / suma_lambda
    if ratio_poisson <= 0:
        return lambda_local, lambda_visitante

    factor = ratio_modelo / ratio_poisson
    factor = limitar(factor, 0.70, 1.43)

    lam_l_nuevo = limitar(lambda_local * factor, 0.2, 5.0)
    lam_v_nuevo = limitar(suma_lambda - lam_l_nuevo, 0.2, 5.0)

    return lam_l_nuevo, lam_v_nuevo


def marcadores_probables(lambda_local, lambda_visitante, top_n=5, max_goles=6,
                          prob_local=None, prob_visitante=None):
    from math import exp, factorial

    if prob_local is not None and prob_visitante is not None:
        lambda_local, lambda_visitante = ajustar_lambdas_por_probabilidades(
            lambda_local, lambda_visitante, prob_local, prob_visitante
        )

    def pmf(k, lam):
        return (lam ** k) * exp(-lam) / factorial(k)

    resultados = []
    for i in range(max_goles + 1):
        for j in range(max_goles + 1):
            prob = pmf(i, lambda_local) * pmf(j, lambda_visitante)
            if i > j:
                tipo = "local"
            elif i == j:
                tipo = "empate"
            else:
                tipo = "visitante"
            resultados.append({
                "marcador":         f"{i}-{j}",
                "goles_local":      i,
                "goles_visitante":  j,
                "probabilidad":     round(prob, 6),
                "tipo":             tipo,
            })

    resultados.sort(key=lambda x: x["probabilidad"], reverse=True)
    return resultados[:top_n]


def marcadores_para_carrusel(lambda_local, lambda_visitante, prediccion,
                              nombre_local, nombre_visitante,
                              prob_local, prob_visitante,
                              top_n=5, max_goles=6):
    lambda_local_adj, lambda_visitante_adj = ajustar_lambdas_por_probabilidades(
        lambda_local, lambda_visitante, prob_local, prob_visitante
    )

    todos = marcadores_probables(
        lambda_local_adj, lambda_visitante_adj,
        top_n=(max_goles + 1) ** 2,
        max_goles=max_goles,
    )

    if prediccion == nombre_local:
        tipo_pred = "local"
    elif prediccion == nombre_visitante:
        tipo_pred = "visitante"
    else:
        tipo_pred = "empate"

    destacado = next((m for m in todos if m["tipo"] == tipo_pred), None)
    top_general = todos[:top_n]

    if destacado is None:
        return top_general

    resto = [m for m in top_general if m["marcador"] != destacado["marcador"]]
    carrusel = [destacado] + resto
    return carrusel[:top_n]


# =============================
# FUERZA BASE  (con ranking FIFA)
# =============================

def calcular_fuerza_base(seleccion, contexto, cfg):
    PESO_FORMA        = 0.28
    PESO_WINRATE      = 0.20
    PESO_GOLES_FAVOR  = 0.13
    PESO_GOLES_CONTRA = 0.13
    PESO_STREAK       = 0.10
    PESO_FIFA         = 0.16

    confianza_forma = peso_confianza(seleccion.get("partidos", 0))
    forma_raw = seleccion["forma_ponderada"]
    forma = confianza_forma * forma_raw + (1 - confianza_forma) * 0.5

    altitud_sede = contexto.get("altitud_sede", 0)
    altitud_base = seleccion.get("altitud_base", 0)
    es_neutro    = contexto.get("es_neutro", False)
    es_local     = contexto.get("es_local", False)

    # FIX: usar helper con fallback para win_rate
    wr_raw, partidos_sit = _wr_con_fallback(seleccion, es_neutro, es_local)
    confianza_wr = peso_confianza(partidos_sit)
    win_rate = confianza_wr * wr_raw + (1 - confianza_wr) * 0.45

    confianza_goles = peso_confianza(seleccion.get("partidos", 0))
    gf_raw       = normalizar_goles_favor(seleccion["goles_favor_promedio"])
    gc_raw       = normalizar_goles_contra(seleccion["goles_contra_promedio"])
    goles_favor  = confianza_goles * gf_raw + (1 - confianza_goles) * 0.5
    goles_contra = confianza_goles * gc_raw + (1 - confianza_goles) * 0.5
    streak       = normalizar_streak(seleccion["imbatido_streak"])

    fifa_score = normalizar_ranking_fifa(seleccion)

    fuerza = (
        forma        * PESO_FORMA        +
        win_rate     * PESO_WINRATE      +
        goles_favor  * PESO_GOLES_FAVOR  +
        goles_contra * PESO_GOLES_CONTRA +
        streak       * PESO_STREAK       +
        fifa_score   * PESO_FIFA
    )

    factor_alt = calcular_factor_altitud(altitud_sede, altitud_base)
    fuerza *= (0.5 + factor_alt * 0.5)

    return fuerza


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
        return 0.5, 0, []

    partidos = cruce.get("partidos_recientes", []) or cruce.get("partidos", []) or []
    if not partidos:
        return 0.5, 0, []

    victorias = 0
    for p in partidos:
        gl = p.get("goles_local", 0)
        gv = p.get("goles_visitante", 0)
        es_local_ref = normalizar_nombre(p.get("local", "")) == nl
        if gl == gv:
            continue
        gano_local = gl > gv
        if (es_local_ref and gano_local) or (not es_local_ref and not gano_local):
            victorias += 1

    score = victorias / len(partidos) if partidos else 0.5
    return limitar(score, 0.0, 1.0), len(partidos), partidos[:5]


def contar_resultados_h2h(partidos_h2h, nombre_local, nombre_visitante):
    wins_local = wins_visita = empates = 0
    nl = normalizar_nombre(nombre_local)
    for p in partidos_h2h:
        gl = p.get("goles_local", 0)
        gv = p.get("goles_visitante", 0)
        es_local = normalizar_nombre(p.get("local", "")) == nl
        if gl == gv:
            empates += 1
        elif gl > gv:
            if es_local: wins_local  += 1
            else:        wins_visita += 1
        else:
            if es_local: wins_visita += 1
            else:        wins_local  += 1
    return wins_local, empates, wins_visita


# =============================
# EMPATE  (con corrección por ranking)
# =============================

def calcular_tasa_empate(seleccion):
    partidos  = seleccion.get("partidos", 0)
    empatados = seleccion.get("empatados", 0)
    if partidos == 0:
        return 0.22, 0.0
    tasa = limitar(empatados / partidos, 0.0, 1.0)
    conf = peso_confianza(partidos)
    return tasa, conf


def contar_empates_recientes(ultimos_5):
    return ultimos_5.count("D")


def calcular_prob_empate(f_local, f_visitante, sel_local, sel_visitante, es_neutro=False):
    diferencia  = abs(f_local - f_visitante)
    base_empate = 0.28 if es_neutro else 0.24
    base = limitar(base_empate - (diferencia / 0.50) * 0.10, 0.14, base_empate)

    tasa_l, conf_l = calcular_tasa_empate(sel_local)
    tasa_v, conf_v = calcular_tasa_empate(sel_visitante)

    conf_total = conf_l + conf_v
    if conf_total > 0:
        historico  = (tasa_l * conf_l + tasa_v * conf_v) / conf_total
        peso_hist  = 0.35 + (min(conf_l, conf_v) * 0.20)
    else:
        historico  = 0.22
        peso_hist  = 0.20

    peso_base = 0.55 - peso_hist
    peso_mom  = max(0.05, 1.0 - peso_base - peso_hist)

    d_local     = contar_empates_recientes(sel_local.get("ultimos_5", []))
    d_visitante = contar_empates_recientes(sel_visitante.get("ultimos_5", []))
    momentum    = limitar((d_local + d_visitante) * 0.06, 0.0, 0.28)

    prob = (
        base      * peso_base +
        historico * peso_hist +
        momentum  * peso_mom
    )

    rank_l = sel_local.get("ranking_fifa", 100)
    rank_v = sel_visitante.get("ranking_fifa", 100)
    rank_l_ef = min(rank_l, 210)
    rank_v_ef = min(rank_v, 210)
    diff_ranking = abs(rank_l_ef - rank_v_ef)
    if diff_ranking > 30:
        factor_ranking = limitar(1.0 - (diff_ranking - 30) / 300, 0.70, 1.0)
        prob *= factor_ranking

    piso = 0.18 if conf_total == 0 else 0.14
    return limitar(prob, piso, 0.44)


# =============================
# AJUSTE LAMBDA
# =============================

def ajuste_empate_por_lambdas(prob_local, prob_empate, prob_visitante,
                               lambda_local, lambda_visitante):
    suma_lambda = lambda_local + lambda_visitante
    diff_lambda = abs(lambda_local - lambda_visitante)

    boost = 0.0

    if suma_lambda < 2.2 and diff_lambda < 0.40:
        intensidad = limitar((2.2 - suma_lambda) / 1.2, 0.0, 1.0)
        boost += 0.10 * intensidad

    if diff_lambda < 0.40 and suma_lambda < 2.8:
        intensidad = limitar((0.40 - diff_lambda) / 0.40, 0.0, 1.0)
        boost += 0.09 * intensidad

    if diff_lambda < 0.15:
        boost += 0.05

    if boost <= 0.0:
        return prob_local, prob_empate, prob_visitante

    boost = limitar(boost, 0.0, 0.20)

    total_lv = prob_local + prob_visitante
    if total_lv <= 0:
        return prob_local, prob_empate, prob_visitante

    quita_l = boost * (prob_local    / total_lv)
    quita_v = boost * (prob_visitante / total_lv)

    prob_local     -= quita_l
    prob_visitante -= quita_v
    prob_empate    += boost

    MAX_EMPATE = 0.44
    if prob_empate > MAX_EMPATE:
        exceso         = prob_empate - MAX_EMPATE
        prob_empate    = MAX_EMPATE
        total_lv       = prob_local + prob_visitante
        if total_lv > 0:
            prob_local     += exceso * (prob_local     / total_lv)
            prob_visitante += exceso * (prob_visitante / total_lv)

    total = prob_local + prob_empate + prob_visitante
    return prob_local / total, prob_empate / total, prob_visitante / total


# =============================
# PREDICCIÓN INTELIGENTE
# =============================

def prediccion_inteligente(prob_local, prob_empate, prob_visitante,
                            lambda_local, lambda_visitante,
                            nombre_local, nombre_visitante):
    suma_lambda = lambda_local + lambda_visitante
    diff_lambda = abs(lambda_local - lambda_visitante)

    if prob_empate >= prob_local and prob_empate >= prob_visitante:
        return "Empate"

    if suma_lambda < 2.3 and diff_lambda < 0.35:
        return "Empate"

    if diff_lambda < 0.40 and prob_empate > 0.24:
        favorito_prob = max(prob_local, prob_visitante)
        if favorito_prob - prob_empate < 0.10:
            return "Empate"

    if prob_local >= prob_visitante:
        return nombre_local
    else:
        return nombre_visitante


# =============================
# COHERENCIA PREDICCIÓN / PROBABILIDADES
# =============================

def garantizar_coherencia(pred, prob_local, prob_empate, prob_visitante,
                           nombre_local, nombre_visitante):
    if pred == "Empate":
        favorito = max(prob_local, prob_visitante)
        if prob_empate < favorito:
            if prob_local >= prob_visitante:
                exceso = prob_local - prob_empate + 0.001
                prob_local  -= exceso
                prob_empate += exceso
            else:
                exceso = prob_visitante - prob_empate + 0.001
                prob_visitante -= exceso
                prob_empate    += exceso

    elif pred == nombre_local:
        if prob_local < max(prob_empate, prob_visitante):
            if prob_empate >= prob_visitante:
                exceso = prob_empate - prob_local + 0.001
                prob_empate -= exceso
                prob_local  += exceso
            else:
                exceso = prob_visitante - prob_local + 0.001
                prob_visitante -= exceso
                prob_local     += exceso

    else:  # pred == nombre_visitante
        if prob_visitante < max(prob_local, prob_empate):
            if prob_local >= prob_empate:
                exceso = prob_local - prob_visitante + 0.001
                prob_local     -= exceso
                prob_visitante += exceso
            else:
                exceso = prob_empate - prob_visitante + 0.001
                prob_empate    -= exceso
                prob_visitante += exceso

    total = prob_local + prob_empate + prob_visitante
    return prob_local / total, prob_empate / total, prob_visitante / total


# =============================
# CAP FINAL
# =============================

def _aplicar_cap_final(prob_local, prob_empate, prob_visitante, max_favorito):
    prob_max = max(prob_local, prob_visitante)
    if prob_max <= max_favorito:
        return prob_local, prob_empate, prob_visitante

    if prob_local >= prob_visitante:
        # Local es el favorito recortado: exceso va más al visitante que al empate
        exceso          = prob_local - max_favorito
        prob_local      = max_favorito
        prob_empate    += exceso * 0.30
        prob_visitante += exceso * 0.70
    else:
        # Visitante es el favorito recortado: exceso va más al empate que al local
        # para evitar que el local (débil) supere al favorito recortado
        exceso          = prob_visitante - max_favorito
        prob_visitante  = max_favorito
        prob_empate    += exceso * 0.70
        prob_local     += exceso * 0.30

    total = prob_local + prob_empate + prob_visitante
    return prob_local / total, prob_empate / total, prob_visitante / total


# =============================
# MOTOR CENTRAL
# =============================

def predecir_probabilidades(
    sel_local, sel_visitante,
    h2h_data, nombre_local, nombre_visitante,
    contexto, promedio_global, cfg,
):
    es_neutro = contexto.get("es_neutro", False)
    ctx_l = {**contexto, "es_local": True}
    ctx_v = {**contexto, "es_local": False}

    lambda_local, lambda_visitante = calcular_lambdas(
        sel_local, sel_visitante, contexto, promedio_global
    )
    p_local, p_empate, p_visitante = probabilidades_poisson(lambda_local, lambda_visitante)

    fb_local     = calcular_fuerza_base(sel_local,     ctx_l, cfg)
    fb_visitante = calcular_fuerza_base(sel_visitante, ctx_v, cfg)

    if cfg["usa_h2h"] and h2h_data:
        h2h_local, n_h2h, partidos_h2h = calcular_h2h_score(
            nombre_local, nombre_visitante, h2h_data
        )
    else:
        h2h_local, n_h2h, partidos_h2h = 0.5, 0, []
    h2h_visitante = 1.0 - h2h_local

    if cfg["usa_altitud"]:
        alt_sede     = contexto.get("altitud_sede", 0)
        factor_alt_l = calcular_factor_altitud(alt_sede, sel_local.get("altitud_base", 0))
        factor_alt_v = calcular_factor_altitud(alt_sede, sel_visitante.get("altitud_base", 0))
        total_alt    = factor_alt_l + factor_alt_v
        alt_norm_l   = factor_alt_l / total_alt if total_alt > 0 else 0.5
        alt_norm_v   = factor_alt_v / total_alt if total_alt > 0 else 0.5
    else:
        alt_norm_l = alt_norm_v = 0.5

    PESO_BASE    = cfg["PESO_BASE"]
    PESO_H2H     = cfg["PESO_H2H"]
    PESO_ALTITUD = cfg["PESO_ALTITUD"]

    f_local = (
        fb_local    * PESO_BASE    +
        h2h_local   * PESO_H2H    +
        alt_norm_l  * PESO_ALTITUD
    )
    f_visitante = (
        fb_visitante  * PESO_BASE    +
        h2h_visitante * PESO_H2H    +
        alt_norm_v    * PESO_ALTITUD
    )

    score   = f_local - f_visitante
    ratio_l = 1 / (1 + math.exp(-cfg["K_LOGISTICO"] * score))
    ratio_v = 1 - ratio_l

    if ratio_l > cfg["MAX_FAVORITO"]:
        ratio_l = cfg["MAX_FAVORITO"]
        ratio_v = 1 - ratio_l
    if ratio_v > cfg["MAX_FAVORITO"]:
        ratio_v = cfg["MAX_FAVORITO"]
        ratio_l = 1 - ratio_v

    prob_empate_f    = calcular_prob_empate(f_local, f_visitante, sel_local, sel_visitante, es_neutro)
    restante         = 1.0 - prob_empate_f
    prob_local_f     = restante * ratio_l
    prob_visitante_f = restante * ratio_v

    ALPHA = cfg["ALPHA"]
    BETA  = cfg["BETA"]

    prob_local     = ALPHA * p_local     + BETA * prob_local_f
    prob_empate    = ALPHA * p_empate    + BETA * prob_empate_f
    prob_visitante = ALPHA * p_visitante + BETA * prob_visitante_f

    total = prob_local + prob_empate + prob_visitante
    prob_local    /= total
    prob_empate   /= total
    prob_visitante /= total

    prob_local, prob_empate, prob_visitante = _aplicar_cap_final(
        prob_local, prob_empate, prob_visitante, cfg["MAX_FAVORITO"]
    )

    prob_local, prob_empate, prob_visitante = ajuste_empate_por_lambdas(
        prob_local, prob_empate, prob_visitante,
        lambda_local, lambda_visitante,
    )

    gap       = abs(prob_local - prob_visitante)
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
        "n_h2h":            n_h2h,
        "partidos_h2h":     partidos_h2h,
        "fb_local":         fb_local,
        "fb_visitante":     fb_visitante,
        "lambda_local":     lambda_local,
        "lambda_visitante": lambda_visitante,
        "factor_altitud_local":     calcular_factor_altitud(contexto.get("altitud_sede",0), sel_local.get("altitud_base",0)),
        "factor_altitud_visitante": calcular_factor_altitud(contexto.get("altitud_sede",0), sel_visitante.get("altitud_base",0)),
    }


# =============================
# ANÁLISIS ESTRUCTURADO
# =============================

def generar_analisis(local, visitante, resultado, nombre_local, nombre_visitante,
                      contexto, cfg, top_marcadores):
    factores     = []
    altitud_sede = contexto.get("altitud_sede", 0)
    ciudad_sede  = contexto.get("ciudad_sede", "")
    es_neutro    = contexto.get("es_neutro", False)

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
        "factor":    "Forma reciente",
        "impacto":   nivel_impacto(abs(fl - fv)),
        "tipo":      "forma",
        "local":     {"valor": round(fl, 2), "ultimos_5": ul5_l, "nombre": nombre_local},
        "visitante": {"valor": round(fv, 2), "ultimos_5": ul5_v, "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    alt_l = local.get("altitud_base", 0)
    alt_v = visitante.get("altitud_base", 0)
    fa_l  = resultado["factor_altitud_local"]
    fa_v  = resultado["factor_altitud_visitante"]

    if altitud_sede >= 1500:
        contexto_altitud = contexto.get("contexto_altitud", f"Sede a {altitud_sede}m")
        diff_l = altitud_sede - alt_l
        diff_v = altitud_sede - alt_v
        if diff_l > diff_v + 500:
            interp = (f"{contexto_altitud}. {nombre_local} viene de {alt_l}m "
                      f"(diferencia: {diff_l}m) frente a {nombre_visitante} de {alt_v}m "
                      f"(diferencia: {diff_v}m). La altitud afecta más a {nombre_local}. "
                      f"Factor de rendimiento: {fa_l:.2f} vs {fa_v:.2f}.")
        elif diff_v > diff_l + 500:
            interp = (f"{contexto_altitud}. {nombre_visitante} llega desde {alt_v}m "
                      f"con {diff_v}m de diferencia; {nombre_local} desde {alt_l}m "
                      f"({diff_l}m diferencia). La altitud favorece a {nombre_local}. "
                      f"Factor: {fa_l:.2f} vs {fa_v:.2f}.")
        else:
            interp = (f"{contexto_altitud}. Ambas selecciones enfrentan condiciones similares "
                      f"de aclimatación ({diff_l}m vs {diff_v}m de diferencia). "
                      f"Factor altitud: {fa_l:.2f} vs {fa_v:.2f}.")
    else:
        interp = (f"Sede en condiciones normales ({altitud_sede}m). "
                  f"La altitud no es un factor diferenciador en este partido.")

    factores.append({
        "factor":    "Factor altitud",
        "impacto":   nivel_impacto(abs(fa_l - fa_v)),
        "tipo":      "altitud",
        "altitud_sede": altitud_sede,
        "ciudad_sede":  ciudad_sede,
        "local":     {"nombre": nombre_local,     "altitud_base": alt_l, "factor": round(fa_l,3)},
        "visitante": {"nombre": nombre_visitante, "altitud_base": alt_v, "factor": round(fa_v,3)},
        "interpretacion": interp,
    })

    gf_l = local["goles_favor_promedio"];     gc_l = local["goles_contra_promedio"]
    gf_v = visitante["goles_favor_promedio"]; gc_v = visitante["goles_contra_promedio"]
    ventaja_of = gf_l - gf_v

    if ventaja_of >= 0.4:
        interp = (f"{nombre_local} más ofensivo: {gf_l:.2f} goles/partido "
                  f"(vs {gf_v:.2f}). Defensiva: {gc_l:.2f} vs {gc_v:.2f}.")
    elif ventaja_of <= -0.4:
        interp = (f"{nombre_visitante} más ofensivo: {gf_v:.2f} vs {gf_l:.2f} goles/partido. "
                  f"Defensiva: {gc_l:.2f} vs {gc_v:.2f}.")
    else:
        interp = (f"Producción similar: {nombre_local} {gf_l:.2f} — "
                  f"{nombre_visitante} {gf_v:.2f} goles/partido. "
                  f"Defensa: {gc_l:.2f} vs {gc_v:.2f}.")

    factores.append({
        "factor":    "Potencial ofensivo y defensivo",
        "impacto":   nivel_impacto(abs(ventaja_of) * 0.5),
        "tipo":      "doble_barra",
        "local":     {"nombre": nombre_local,     "goles_favor": round(gf_l,2), "goles_contra": round(gc_l,2)},
        "visitante": {"nombre": nombre_visitante, "goles_favor": round(gf_v,2), "goles_contra": round(gc_v,2)},
        "interpretacion": interp,
    })

    ll = resultado["lambda_local"]
    lv = resultado["lambda_visitante"]
    suma_l = ll + lv
    diff_l = abs(ll - lv)

    if suma_l < 1.6:
        tipo_partido = "partido muy trabado"
        interp_l = (f"Los lambdas proyectan un {tipo_partido}: "
                    f"{nombre_local} {ll:.2f} goles esperados vs {nombre_visitante} {lv:.2f}. "
                    f"Con solo {suma_l:.2f} goles totales esperados, el empate es el resultado más probable.")
    elif diff_l < 0.30:
        tipo_partido = "partido muy equilibrado"
        interp_l = (f"Lambdas muy similares ({ll:.2f} vs {lv:.2f}): {tipo_partido}. "
                    f"La diferencia de solo {diff_l:.2f} goles esperados entre ambos equipos "
                    f"sugiere un resultado cerrado.")
    elif ll > lv:
        interp_l = (f"{nombre_local} genera más peligro ofensivo según el modelo: "
                    f"{ll:.2f} goles esperados vs {lv:.2f} de {nombre_visitante}.")
    else:
        interp_l = (f"{nombre_visitante} genera más peligro ofensivo según el modelo: "
                    f"{lv:.2f} goles esperados vs {ll:.2f} de {nombre_local}.")

    factores.append({
        "factor":    "Proyección de goles (λ)",
        "impacto":   nivel_impacto(diff_l * 0.5),
        "tipo":      "lambda",
        "local":     {"nombre": nombre_local,     "lambda": round(ll, 3)},
        "visitante": {"nombre": nombre_visitante, "lambda": round(lv, 3)},
        "suma":      round(suma_l, 3),
        "interpretacion": interp_l,
    })

    marcador_top = top_marcadores[0]

    probs_tipo = {
        "local":     resultado["local"],
        "empate":    resultado["empate"],
        "visitante": resultado["visitante"],
    }
    tipo_favorito_1x2 = max(probs_tipo, key=probs_tipo.get)

    tipo_map = {"local": nombre_local, "empate": "el empate", "visitante": nombre_visitante}
    gana_str = tipo_map.get(marcador_top["tipo"], "el empate")

    if marcador_top["tipo"] == tipo_favorito_1x2:
        interp_m = (
            f"El marcador más probable es {marcador_top['marcador']} "
            f"({marcador_top['probabilidad']*100:.1f}%), coherente con "
            f"{gana_str} como resultado favorito del modelo."
        )
    else:
        favorito_str = tipo_map.get(tipo_favorito_1x2, "el empate")
        interp_m = (
            f"El marcador individual más probable es {marcador_top['marcador']} "
            f"({marcador_top['probabilidad']*100:.1f}%), favoreciendo a {gana_str}. "
            f"Aunque el modelo da como favorito a {favorito_str} por probabilidad "
            f"acumulada, esa probabilidad se reparte entre varios marcadores distintos."
        )

    factores.append({
        "factor":      "Marcadores más probables",
        "impacto":     "informativo",
        "tipo":        "marcadores",
        "marcadores":  [m["marcador"] for m in top_marcadores],
        "lambda_local":     round(ll, 3),
        "lambda_visitante": round(lv, 3),
        "interpretacion":   interp_m,
    })

    rank_l  = local.get("ranking_fifa", 999)
    rank_v  = visitante.get("ranking_fifa", 999)
    pts_l   = local.get("puntos_fifa", 0.0) or 0.0
    pts_v   = visitante.get("puntos_fifa", 0.0) or 0.0
    fifa_l  = normalizar_ranking_fifa(local)
    fifa_v  = normalizar_ranking_fifa(visitante)

    if rank_l < rank_v:
        interp_fifa = (f"{nombre_local} es objetivamente superior en el ranking FIFA "
                       f"(#{rank_l} / {pts_l:.0f} pts vs #{rank_v} / {pts_v:.0f} pts). "
                       f"Score normalizado: {fifa_l:.2f} vs {fifa_v:.2f}.")
    elif rank_v < rank_l:
        interp_fifa = (f"{nombre_visitante} es objetivamente superior en el ranking FIFA "
                       f"(#{rank_v} / {pts_v:.0f} pts vs #{rank_l} / {pts_l:.0f} pts). "
                       f"Score normalizado: {fifa_v:.2f} vs {fifa_l:.2f}.")
    else:
        interp_fifa = (f"Equipos similares en ranking FIFA (#{rank_l} vs #{rank_v}). "
                       f"Score: {fifa_l:.2f} vs {fifa_v:.2f}.")

    factores.append({
        "factor":    "Ranking FIFA",
        "impacto":   nivel_impacto(abs(fifa_l - fifa_v)),
        "tipo":      "fifa",
        "local":     {"nombre": nombre_local,     "ranking": rank_l, "puntos": round(pts_l,1), "score": round(fifa_l,3)},
        "visitante": {"nombre": nombre_visitante, "ranking": rank_v, "puntos": round(pts_v,1), "score": round(fifa_v,3)},
        "interpretacion": interp_fifa,
    })

    n_h2h = resultado["n_h2h"]
    if cfg["usa_h2h"] and n_h2h > 0:
        h2h_score = resultado["h2h_local"]
        wins_lh, empates_h, wins_vh = contar_resultados_h2h(
            resultado["partidos_h2h"], nombre_local, nombre_visitante
        )
        if h2h_score >= 0.60:
            interp = (f"{nombre_local} domina el historial: {wins_lh}V/{empates_h}E/{wins_vh}D "
                      f"en {n_h2h} enfrentamientos recientes.")
        elif h2h_score <= 0.40:
            interp = (f"{nombre_visitante} lleva ventaja: {wins_vh}V/{empates_h}E/{wins_lh}D "
                      f"en {n_h2h} enfrentamientos recientes.")
        else:
            interp = (f"Historial equilibrado: {wins_lh}V/{empates_h}E/{wins_vh}D "
                      f"en {n_h2h} enfrentamientos. Sin dominancia clara.")

        factores.append({
            "factor":    "Historial directo",
            "impacto":   nivel_impacto(abs(h2h_score - 0.5) * 2),
            "tipo":      "h2h",
            "local":     {"nombre": nombre_local,     "victorias": wins_lh},
            "visitante": {"nombre": nombre_visitante, "victorias": wins_vh},
            "empates":   empates_h,
            "partidos":  resultado["partidos_h2h"],
            "total":     n_h2h,
            "interpretacion": interp,
        })

    return factores


# =============================
# GUARDAR
# =============================

def guardar_resultado(partido, archivo="proyecciones.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    data = [p for p in data if p.get("id") != partido.get("id")]
    data.append(partido)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================
# GENERAR PARTIDO
# =============================

def generar_partido(
    fixture_item,
    db_selecciones,
    h2h            = None,
    perfil_slug    = "amistoso",
    archivo_salida = "proyecciones.json",
):
    cfg = PERFILES_SELECCIONES.get(perfil_slug)
    if not cfg:
        raise ValueError(f"Perfil '{perfil_slug}' no encontrado. "
                         f"Opciones: {list(PERFILES_SELECCIONES.keys())}")

    nombre_local     = fixture_item["local"]
    nombre_visitante = fixture_item["visitante"]

    local_raw     = obtener_seleccion(nombre_local,     db_selecciones)
    visitante_raw = obtener_seleccion(nombre_visitante, db_selecciones)

    if not local_raw:
        raise ValueError(f"Selección local no encontrada: '{nombre_local}'")
    if not visitante_raw:
        raise ValueError(f"Selección visitante no encontrada: '{nombre_visitante}'")

    local     = adaptar_seleccion(local_raw)
    visitante = adaptar_seleccion(visitante_raw)

    altitud_sede = fixture_item.get("altitud_sede", 0)
    pais_sede    = fixture_item.get("pais_sede", "")
    es_neutro = pais_sede.lower() not in [
        normalizar_nombre(nombre_local),
        normalizar_nombre(nombre_visitante),
        local_raw.get("nombre", "").lower(),
        visitante_raw.get("nombre", "").lower(),
    ]
    es_neutro = fixture_item.get("es_neutro", es_neutro)

    contexto = {
        "altitud_sede":     altitud_sede,
        "ciudad_sede":      fixture_item.get("ciudad_sede", ""),
        "pais_sede":        pais_sede,
        "estadio":          fixture_item.get("estadio", ""),
        "es_neutro":        es_neutro,
        "contexto_altitud": fixture_item.get("contexto_altitud", f"Sede a {altitud_sede}m"),
    }

    promedio_global = calcular_promedio_global(db_selecciones)
    h2h_data        = h2h or {}

    resultado = predecir_probabilidades(
        local, visitante, h2h_data,
        nombre_local, nombre_visitante,
        contexto, promedio_global, cfg,
    )

    pred = prediccion_inteligente(
        resultado["local"],
        resultado["empate"],
        resultado["visitante"],
        resultado["lambda_local"],
        resultado["lambda_visitante"],
        local["nombre"],
        visitante["nombre"],
    )

    prob_local, prob_empate, prob_visitante = garantizar_coherencia(
        pred,
        resultado["local"],
        resultado["empate"],
        resultado["visitante"],
        local["nombre"],
        visitante["nombre"],
    )
    resultado["local"]     = prob_local
    resultado["empate"]    = prob_empate
    resultado["visitante"] = prob_visitante

    top_marcadores = marcadores_para_carrusel(
        resultado["lambda_local"],
        resultado["lambda_visitante"],
        pred,
        local["nombre"],
        visitante["nombre"],
        resultado["local"],
        resultado["visitante"],
        top_n=5,
    )
    marcadores_solo_resultado = [m["marcador"] for m in top_marcadores]

    analisis = generar_analisis(
        local, visitante, resultado,
        nombre_local, nombre_visitante,
        contexto, cfg, top_marcadores,
    )

    output = {
        "id":               fixture_item.get("id", ""),
        "fecha":            fixture_item.get("fecha", ""),
        "torneo":           cfg["nombre"],
        "perfil":           perfil_slug,
        "local":            local["nombre"],
        "visitante":        visitante["nombre"],
        "logo_local":       local_raw.get("escudo"),
        "logo_visitante":   visitante_raw.get("escudo"),
        "estadio":          fixture_item.get("estadio", ""),
        "ciudad_sede":      fixture_item.get("ciudad_sede", ""),
        "pais_sede":        pais_sede,
        "altitud_sede":     altitud_sede,
        "es_neutro":        es_neutro,
        "prob_local":       resultado["local"],
        "prob_empate":      resultado["empate"],
        "prob_visitante":   resultado["visitante"],
        "fuerza_local":     resultado["fuerza_local"],
        "fuerza_visitante": resultado["fuerza_visitante"],
        "diferencia":       resultado["diferencia"],
        "confianza":        resultado["confianza"],
        "prediccion":       pred,
        "lambda_local":     resultado["lambda_local"],
        "lambda_visitante": resultado["lambda_visitante"],
        "factor_altitud_local":     resultado["factor_altitud_local"],
        "factor_altitud_visitante": resultado["factor_altitud_visitante"],
        "marcadores_probables":     marcadores_solo_resultado,
        "analisis":                 analisis,
    }

    guardar_resultado(output, archivo_salida)
    return output


# =============================
# CONFIGURACIÓN CENTRAL
# =============================

DB_CONFIG = {
    "mundial_jun2026": {
        "carpeta":  "data",
        "perfil":   "mundial_grupos",
        "salida":   "partidos.json",
    },
}


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    cfg_db  = DB_CONFIG["mundial_jun2026"]
    carpeta = cfg_db["carpeta"]

    print("📂 Cargando datos...\n")
    db_selecciones = cargar_selecciones(carpeta)
    fixture        = cargar_fixture(carpeta)
    h2h_data       = cargar_h2h(carpeta)

    print(f"  ✓ {len(db_selecciones)} selecciones cargadas")
    print(f"  ✓ {len(fixture)} partidos en fixture")
    print(f"  ✓ H2H: {'cargado' if h2h_data else 'no disponible'}")
    print()

    try:
        os.remove(cfg_db["salida"])
    except FileNotFoundError:
        pass

    print(f"🚀 Generando {len(fixture)} proyecciones...\n" + "="*60)

    errores = 0
    for partido in fixture:
        try:
            p = generar_partido(
                fixture_item   = partido,
                db_selecciones = db_selecciones,
                h2h            = h2h_data,
                perfil_slug    = cfg_db["perfil"],
                archivo_salida = cfg_db["salida"],
            )

            alt     = p["altitud_sede"]
            tag_alt = ""
            if alt >= 2500:
                tag_alt = f" 🏔 {alt}m"
            elif alt >= 1500:
                tag_alt = f" ⛰ {alt}m"

            sede   = f"{p['ciudad_sede']}{tag_alt}"
            neutro = " [NEUTRO]" if p["es_neutro"] else ""

            print(f"  ⚽ {p['local']:<20} vs {p['visitante']:<20}  {sede}{neutro}")
            print(f"     {p['prob_local']:.1%} / {p['prob_empate']:.1%} / {p['prob_visitante']:.1%}"
                  f"  →  {p['prediccion']}  [{p['confianza']}]")
            print(f"     λ {p['lambda_local']:.2f} / {p['lambda_visitante']:.2f}"
                  f"  |  Alt: {p['factor_altitud_local']:.3f} vs {p['factor_altitud_visitante']:.3f}")
            print(f"     Marcadores: " + "  ".join(p["marcadores_probables"]))
            print()

        except Exception as e:
            errores += 1
            print(f"  ❌ Error en {partido.get('local','?')} vs {partido.get('visitante','?')}: {e}")
            print()

    print("="*60)
    print(f"✅ Completado. {len(fixture)-errores} proyecciones generadas → {cfg_db['salida']}")
    if errores:
        print(f"  ⚠  {errores} errores (revisa los nombres en selecciones.json y fixture.json)")
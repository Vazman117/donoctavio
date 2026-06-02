import json
import math
import os


# =============================
# CARGAR DATOS
# =============================

def cargar_selecciones(carpeta):
    ruta = os.path.join("scrapper", carpeta, "selecciones.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_fixture(carpeta):
    ruta = os.path.join("scrapper", carpeta, "fixture.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_h2h(carpeta):
    ruta = os.path.join("scrapper", carpeta, "h2h.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def obtener_seleccion(nombre, db):
    """Busca una selección por nombre, con normalización básica."""
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    key = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        key = key.replace(a, b)
    # Búsqueda exacta
    if key in db:
        return db[key]
    # Búsqueda parcial (ej: "costarica" dentro de las claves)
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
# El fútbol de selecciones tiene un factor crucial que los clubes
# casi no tienen: la sede puede estar a 3600m (Quito, La Paz, Bogotá).
# El impacto es asimétrico: favorece al equipo más aclimatado
# y penaliza al visitante que no está adaptado.
#
# ACLIMATACIÓN: se mide como la diferencia entre la altitud de
# la sede y la altitud base del equipo (donde entrena/vive).
# A mayor diferencia, mayor penalización fisiológica.
#
# UMBRALES:
#   < 1000m  → sin impacto significativo
#   1000-2000m → impacto leve
#   2000-3000m → impacto moderado (Bogotá ~2600m)
#   > 3000m  → impacto alto (La Paz ~3600m, Quito ~2850m)
# ─────────────────────────────────────────────────────────────────

def calcular_factor_altitud(altitud_sede, altitud_base_equipo):
    """
    Retorna un modificador de rendimiento basado en la diferencia
    de altitud entre la sede y la base del equipo.

    - Si el equipo ya vive/entrena a esa altitud → sin penalización
    - Si viene de nivel del mar a 2600m → penalización notable
    Devuelve valor entre 0.0 (máx penalización) y 1.0 (sin penalización).
    """
    diferencia = altitud_sede - altitud_base_equipo

    if diferencia <= 0:
        # El equipo está aclimatado o en condición igual/mejor
        return 1.0

    # Penalización progresiva
    # A 2600m de diferencia (Bogotá vs equipo de nivel del mar): ~0.88
    # A 3600m (La Paz): ~0.84
    penalizacion = diferencia / 20000.0   # escala suave
    return max(0.80, 1.0 - penalizacion)


def modificador_altitud_goles(altitud_sede, altitud_base_equipo):
    """
    En alta altitud el balón viaja más rápido y los jugadores se
    fatigan antes → más goles abiertos, partidos más físicos.
    Retorna multiplicador para lambda (goles esperados).
    """
    if altitud_sede < 1500:
        return 1.0
    elif altitud_sede < 2500:
        return 1.03
    elif altitud_sede < 3200:
        return 1.06   # Bogotá ~2600m → +6% de goles
    else:
        return 1.09   # La Paz, Quito → +9%


# =============================
# NORMALIZACIÓN DE DATOS
# =============================

def normalizar_nombre(nombre):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


def limitar(v, a, b):
    return max(a, min(v, b))


def normalizar_ranking_fifa(ranking, total=210):
    """Ranking 1 = mejor → normalizar a 0..1 donde 1 es mejor."""
    return limitar((total - ranking) / (total - 1), 0.0, 1.0)


def normalizar_puntos_fifa(puntos, maximo=2000.0):
    """Normaliza puntos FIFA a escala 0..1."""
    return limitar(puntos / maximo, 0.0, 1.0)


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
# ADAPTADOR DE SELECCIÓN
# =============================

def adaptar_seleccion(seleccion_raw):
    """
    Convierte los datos crudos de una selección al formato interno
    que usa el motor de predicción.

    Lógica de forma:
    - Si hay partidos oficiales recientes, esos dominan (peso 0.70)
    - Los amistosos recientes complementan (peso 0.30)
    - Si solo hay una fuente, se usa directamente
    """
    forma_oficial   = seleccion_raw.get("forma_oficial",   0.0) or 0.0
    forma_amistoso  = seleccion_raw.get("forma_amistosos", 0.0) or 0.0

    if forma_oficial > 0 and forma_amistoso > 0:
        forma_final = round(forma_oficial * 0.70 + forma_amistoso * 0.30, 4)
    elif forma_oficial > 0:
        forma_final = forma_oficial
    elif forma_amistoso > 0:
        forma_final = forma_amistoso
    else:
        forma_final = 0.5

    # Últimos 5: priorizar oficiales, rellenar con amistosos
    ul5_oficial  = seleccion_raw.get("ultimos_5_oficial",  []) or []
    ul5_amistoso = seleccion_raw.get("ultimos_5_amistoso", []) or []
    ul5_mixto = (ul5_oficial + ul5_amistoso)[:5]

    # Partidos totales (oficial + amistoso)
    total_partidos = (
        seleccion_raw.get("partidos_oficial", 0) +
        seleccion_raw.get("partidos_amistoso", 0)
    )
    total_ganados = (
        seleccion_raw.get("ganados_oficial", 0) +
        seleccion_raw.get("ganados_amistoso", 0)
    )
    total_empatados = (
        seleccion_raw.get("empatados_oficial", 0) +
        seleccion_raw.get("empatados_amistoso", 0)
    )
    total_perdidos = (
        seleccion_raw.get("perdidos_oficial", 0) +
        seleccion_raw.get("perdidos_amistoso", 0)
    )

    # Goles ponderados (oficial pesa más)
    gf_oficial  = seleccion_raw.get("goles_favor_oficial",  0.0) or 0.0
    gc_oficial  = seleccion_raw.get("goles_contra_oficial", 0.0) or 0.0
    gf_amistoso = seleccion_raw.get("goles_favor_amistoso", 0.0) or 0.0
    gc_amistoso = seleccion_raw.get("goles_contra_amistoso",0.0) or 0.0

    if gf_oficial > 0 and gf_amistoso > 0:
        gf_ponderado = gf_oficial * 0.70 + gf_amistoso * 0.30
        gc_ponderado = gc_oficial * 0.70 + gc_amistoso * 0.30
    elif gf_oficial > 0:
        gf_ponderado = gf_oficial
        gc_ponderado = gc_oficial
    elif gf_amistoso > 0:
        gf_ponderado = gf_amistoso
        gc_ponderado = gc_amistoso
    else:
        gf_ponderado = 1.0
        gc_ponderado = 1.0

    return {
        "nombre":     seleccion_raw.get("nombre", ""),
        "escudo":     seleccion_raw.get("escudo", ""),
        "confederacion": seleccion_raw.get("confederacion", ""),

        # Ranking FIFA (factor de calidad objetiva)
        "ranking_fifa":  seleccion_raw.get("ranking_fifa",  50),
        "puntos_fifa":   seleccion_raw.get("puntos_fifa",   1000.0),

        # Altitud base del equipo
        "altitud_base":  seleccion_raw.get("altitud_base", 0),

        # Forma ponderada
        "forma_ponderada": forma_final,
        "imbatido_streak": seleccion_raw.get("imbatido_streak", 0),
        "ultimos_5":       ul5_mixto,

        # Rendimiento situacional
        "win_rate_local":  seleccion_raw.get("win_rate_local",  0.5),
        "win_rate_visita": seleccion_raw.get("win_rate_visita", 0.5),
        "win_rate_neutro": seleccion_raw.get("win_rate_neutro", 0.5),

        # Goles
        "goles_favor_promedio":  round(gf_ponderado, 3),
        "goles_contra_promedio": round(gc_ponderado, 3),

        # Stats globales
        "partidos":  total_partidos,
        "ganados":   total_ganados,
        "empatados": total_empatados,
        "perdidos":  total_perdidos,

        # Stats locales/visita (para referencia en análisis)
        "partidos_local":  seleccion_raw.get("partidos_local",  0),
        "ganados_local":   seleccion_raw.get("ganados_local",   0),
        "empatados_local": 0,
        "perdidos_local":  seleccion_raw.get("perdidos_local",  0),

        "partidos_visita":  seleccion_raw.get("partidos_visita",  0),
        "ganados_visita":   seleccion_raw.get("ganados_visita",   0),
        "empatados_visita": 0,
        "perdidos_visita":  seleccion_raw.get("perdidos_visita",  0),

        # Detalle por tipo de partido (para análisis)
        "partidos_oficial":  seleccion_raw.get("partidos_oficial",  0),
        "forma_oficial":     forma_oficial,
        "ultimos_5_oficial": ul5_oficial,
        "partidos_amistoso": seleccion_raw.get("partidos_amistoso", 0),
        "forma_amistosos":   forma_amistoso,
    }


# =============================
# PERFILES DE COMPETENCIA
# =============================
# Para selecciones los perfiles cambian respecto a clubes:
# - El ranking FIFA es un factor objetivo de peso
# - La altitud puede ser determinante
# - Los empates son más frecuentes en partidos neutrales
# - En mundiales el K_LOGISTICO sube (mayor diferencia entre selecciones)
# - En amistosos baja (equipos no juegan al máximo)
# ─────────────────────────────────────────────────────────────────

PERFILES_SELECCIONES = {

    # ── Amistoso internacional ──────────────────────────────────────────────
    # Equipos no juegan al 100%, rotaciones frecuentes.
    # La forma reciente y el ranking FIFA pesan más que el contexto.
    "amistoso": {
        "nombre":           "Amistoso Internacional",
        "K_LOGISTICO":      3.8,
        "MAX_FAVORITO":     0.70,
        "ALPHA":            0.72,   # Poisson
        "BETA":             0.28,   # fuerza
        "usa_h2h":          False,
        "usa_ranking_fifa": True,
        "usa_altitud":      True,
        "PESO_BASE":        0.75,
        "PESO_H2H":         0.00,
        "PESO_RANKING":     0.15,
        "PESO_ALTITUD":     0.10,
    },

    # ── Eliminatoria CONMEBOL ───────────────────────────────────────────────
    # Altitud muy importante, H2H relevante, partidos de altísima tensión.
    "eliminatoria_conmebol": {
        "nombre":           "Eliminatoria CONMEBOL",
        "K_LOGISTICO":      4.2,
        "MAX_FAVORITO":     0.68,
        "ALPHA":            0.70,
        "BETA":             0.30,
        "usa_h2h":          True,
        "usa_ranking_fifa": True,
        "usa_altitud":      True,
        "PESO_BASE":        0.60,
        "PESO_H2H":         0.18,
        "PESO_RANKING":     0.12,
        "PESO_ALTITUD":     0.10,
    },

    # ── Eliminatoria CONCACAF ───────────────────────────────────────────────
    "eliminatoria_concacaf": {
        "nombre":           "Eliminatoria CONCACAF",
        "K_LOGISTICO":      4.0,
        "MAX_FAVORITO":     0.70,
        "ALPHA":            0.72,
        "BETA":             0.28,
        "usa_h2h":          True,
        "usa_ranking_fifa": True,
        "usa_altitud":      True,
        "PESO_BASE":        0.65,
        "PESO_H2H":         0.15,
        "PESO_RANKING":     0.12,
        "PESO_ALTITUD":     0.08,
    },

    # ── Copa América / CONCACAF Gold Cup ────────────────────────────────────
    "copa_america": {
        "nombre":           "Copa América / Torneo Continental",
        "K_LOGISTICO":      4.1,
        "MAX_FAVORITO":     0.71,
        "ALPHA":            0.71,
        "BETA":             0.29,
        "usa_h2h":          True,
        "usa_ranking_fifa": True,
        "usa_altitud":      True,
        "PESO_BASE":        0.62,
        "PESO_H2H":         0.16,
        "PESO_RANKING":     0.14,
        "PESO_ALTITUD":     0.08,
    },

    # ── Mundial FIFA — Fase de Grupos ────────────────────────────────────────
    # El más competitivo. FIFA enforces sedes neutrales normalmente.
    # El ranking FIFA es el factor más objetivo disponible.
    "mundial_grupos": {
        "nombre":           "Copa del Mundo FIFA — Fase de Grupos",
        "K_LOGISTICO":      4.3,
        "MAX_FAVORITO":     0.72,
        "ALPHA":            0.68,
        "BETA":             0.32,
        "usa_h2h":          True,
        "usa_ranking_fifa": True,
        "usa_altitud":      True,
        "PESO_BASE":        0.58,
        "PESO_H2H":         0.16,
        "PESO_RANKING":     0.18,
        "PESO_ALTITUD":     0.08,
    },

    # ── Mundial FIFA — Eliminatorias (octavos en adelante) ──────────────────
    # Mayor presión, experiencia en grandes competencias cuenta más.
    "mundial_eliminatoria": {
        "nombre":           "Copa del Mundo FIFA — Eliminatorias",
        "K_LOGISTICO":      4.5,
        "MAX_FAVORITO":     0.73,
        "ALPHA":            0.66,
        "BETA":             0.34,
        "usa_h2h":          True,
        "usa_ranking_fifa": True,
        "usa_altitud":      True,
        "PESO_BASE":        0.55,
        "PESO_H2H":         0.18,
        "PESO_RANKING":     0.20,
        "PESO_ALTITUD":     0.07,
    },
}


# =============================
# PROMEDIO DE GOL (global)
# =============================

def calcular_promedio_global(db):
    """Promedio de goles por partido de todas las selecciones con datos."""
    selecciones = [v for v in db.values() if v.get("partidos", 0) > 0]
    if not selecciones:
        return 1.35   # fallback internacional
    return sum(v.get("goles_favor_promedio", 1.35) for v in selecciones) / len(selecciones)


# =============================
# CONFIANZA POR MUESTRA
# =============================

def peso_confianza(partidos_jugados):
    """
    Las selecciones juegan mucho menos que los clubes.
    Ajustamos los umbrales a la realidad de selecciones.
    """
    if partidos_jugados < 3:
        return 0.35
    elif partidos_jugados < 6:
        return 0.60
    elif partidos_jugados < 10:
        return 0.80
    else:
        return 1.0


# =============================
# IPO e ISD (adaptados para selecciones)
# =============================

def calcular_ipo_seleccion(equipo, contexto, promedio_global):
    """
    Índice de Potencial Ofensivo para selecciones.
    Considera:
    - Goles promedio ponderados por muestra
    - Forma ponderada (oficial + amistosos)
    - Win rate situacional (local/visita/neutro según sede)
    - Factor de altitud (penalización si viene de muy abajo)
    """
    peso   = peso_confianza(equipo.get("partidos", 0))
    altitud_sede = contexto.get("altitud_sede", 0)
    altitud_base = equipo.get("altitud_base", 0)
    es_local     = contexto.get("es_local", False)
    es_neutro    = contexto.get("es_neutro", False)

    # Ataque normalizado por promedio global
    ataque = equipo["goles_favor_promedio"] / promedio_global if promedio_global else 1.0
    ataque = peso * ataque + (1 - peso) * 1.0   # suavizado por muestra

    # Forma reciente
    mod_forma = 0.85 + (equipo["forma_ponderada"] * 0.30)

    # Win rate situacional
    if es_neutro:
        wr_raw = equipo.get("win_rate_neutro", 0.5)
    elif es_local:
        wr_raw = equipo.get("win_rate_local", 0.5)
    else:
        wr_raw = equipo.get("win_rate_visita", 0.5)
    mod_localidad = 0.80 + (wr_raw * 0.40)

    # Factor de altitud: penaliza si el equipo no está aclimatado
    factor_alt = calcular_factor_altitud(altitud_sede, altitud_base)
    # Modificador de goles por altitud (balón más rápido, más cansancio)
    mod_goles_alt = modificador_altitud_goles(altitud_sede, altitud_base)

    ipo = ataque * mod_forma * mod_localidad * factor_alt * mod_goles_alt
    return ipo


def calcular_isd_seleccion(equipo, contexto, promedio_global):
    """
    Índice de Solidez Defensiva para selecciones.

    CONVENCIÓN: ISD es un "factor de concesión" que va en el DENOMINADOR
    de la fórmula de lambda del rival.
       lambda_rival = IPO_rival * promedio / ISD_este_equipo

    ISD > 1.0 → buena defensa (reduce goles del rival)
    ISD = 1.0 → defensa promedio
    ISD < 1.0 → defensa débil (aumenta goles del rival)

    Derivación:
       ISD = promedio / goles_contra_promedio
       → Si goles_contra = 0.2 y promedio = 1.35: ISD = 6.75 → capeamos a 2.5
       → Regresión a la media según muestra disponible

    Límites: [0.5, 2.5]
    """
    peso = peso_confianza(equipo.get("partidos", 0))
    altitud_sede = contexto.get("altitud_sede", 0)
    altitud_base = equipo.get("altitud_base", 0)

    gc = equipo["goles_contra_promedio"]
    if gc == 0:
        isd_raw = 2.5   # defensa perfecta en muestra → máximo razonable
    else:
        isd_raw = promedio_global / gc

    # Capear: ninguna selección tiene defensa de 2.5x la media o peor que 0.5x
    isd_raw = limitar(isd_raw, 0.5, 2.5)

    # Regresión a la media según confianza de la muestra
    isd = peso * isd_raw + (1 - peso) * 1.0

    # Streak de imbatibilidad suma hasta 10% adicional a la defensa
    mod_streak = 1.0 + (normalizar_streak(equipo["imbatido_streak"]) * 0.10)
    isd *= mod_streak

    # La altitud también afecta movilidad defensiva del equipo no aclimatado
    factor_alt = calcular_factor_altitud(altitud_sede, altitud_base)
    isd *= (0.7 + factor_alt * 0.3)   # impacto suavizado: altitud degrada la defensa levemente

    return limitar(isd, 0.5, 2.5)


def calcular_lambdas(seleccion_local, seleccion_visitante, contexto, promedio_global):
    """
    Fórmula Dixon-Coles adaptada:
        lambda_local     = IPO_local     * promedio / ISD_visitante
        lambda_visitante = IPO_visitante * promedio / ISD_local

    ISD en el denominador: defensa fuerte → reduce los goles del rival ✓
    """
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
# FUERZA BASE (selecciones)
# =============================

def calcular_fuerza_base(seleccion, contexto, cfg):
    """
    Calcula la fuerza base de la selección combinando:
    - Forma ponderada (oficial + amistosos)
    - Win rate situacional
    - Goles a favor / en contra
    - Ranking FIFA normalizado (si el perfil lo usa)
    - Imbatido streak
    """
    PESO_FORMA        = 0.28
    PESO_WINRATE      = 0.20
    PESO_GOLES_FAVOR  = 0.12
    PESO_GOLES_CONTRA = 0.12
    PESO_RANKING_FIFA = 0.18
    PESO_STREAK       = 0.10

    # El ranking FIFA siempre está disponible para selecciones
    ranking_norm = normalizar_ranking_fifa(seleccion["ranking_fifa"])
    puntos_norm  = normalizar_puntos_fifa(seleccion["puntos_fifa"])
    # Combinar ranking y puntos para mayor robustez
    factor_fifa  = ranking_norm * 0.50 + puntos_norm * 0.50

    forma = seleccion["forma_ponderada"]

    altitud_sede = contexto.get("altitud_sede", 0)
    altitud_base = seleccion.get("altitud_base", 0)
    es_neutro    = contexto.get("es_neutro", False)
    es_local     = contexto.get("es_local", False)

    partidos_sit = seleccion.get("partidos_local" if es_local else "partidos_visita", 0)
    confianza_wr = peso_confianza(partidos_sit)
    if es_neutro:
        wr_raw = seleccion.get("win_rate_neutro", 0.5)
    elif es_local:
        wr_raw = seleccion.get("win_rate_local", 0.5)
    else:
        wr_raw = seleccion.get("win_rate_visita", 0.5)
    win_rate = confianza_wr * wr_raw + (1 - confianza_wr) * 0.45

    goles_favor  = normalizar_goles_favor(seleccion["goles_favor_promedio"])
    goles_contra = normalizar_goles_contra(seleccion["goles_contra_promedio"])
    streak       = normalizar_streak(seleccion["imbatido_streak"])

    fuerza = (
        forma        * PESO_FORMA        +
        win_rate     * PESO_WINRATE      +
        goles_favor  * PESO_GOLES_FAVOR  +
        goles_contra * PESO_GOLES_CONTRA +
        factor_fifa  * PESO_RANKING_FIFA +
        streak       * PESO_STREAK
    )

    # Ajuste por altitud: reduce levemente la fuerza si hay penalización
    factor_alt = calcular_factor_altitud(altitud_sede, altitud_base)
    # Solo aplicamos la mitad del impacto aquí (el resto ya está en IPO/ISD)
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
# EMPATE
# =============================

def calcular_tasa_empate(seleccion, es_neutro=False):
    if es_neutro:
        partidos  = seleccion.get("partidos", 0)
        empatados = seleccion.get("empatados", 0)
    else:
        partidos  = seleccion.get("partidos", 0)
        empatados = seleccion.get("empatados", 0)
    if partidos == 0:
        return 0.22
    return limitar(empatados / partidos, 0.0, 1.0)


def contar_empates_recientes(ultimos_5):
    return ultimos_5.count("D")


PESO_EMPATE_BASE      = 0.22
PESO_EMPATE_HISTORICO = 0.63
PESO_EMPATE_MOMENTUM  = 0.15

def calcular_prob_empate(f_local, f_visitante, sel_local, sel_visitante, es_neutro=False):
    diferencia = abs(f_local - f_visitante)
    # En partidos neutros los empates son más probables
    base_empate = 0.30 if es_neutro else 0.26
    base = limitar(base_empate - (diferencia / 0.40) * 0.15, 0.10, base_empate)

    tasa_local     = calcular_tasa_empate(sel_local,     es_neutro)
    tasa_visitante = calcular_tasa_empate(sel_visitante, es_neutro)
    historico = max(tasa_local, tasa_visitante)

    d_local     = contar_empates_recientes(sel_local.get("ultimos_5", []))
    d_visitante = contar_empates_recientes(sel_visitante.get("ultimos_5", []))
    momentum    = limitar((d_local + d_visitante) * 0.07, 0.0, 0.35)

    return limitar(
        base      * PESO_EMPATE_BASE      +
        historico * PESO_EMPATE_HISTORICO +
        momentum  * PESO_EMPATE_MOMENTUM,
        0.10, 0.46
    )


# =============================
# MOTOR CENTRAL DE PREDICCIÓN
# =============================

def predecir_probabilidades(
    sel_local, sel_visitante,
    h2h_data, nombre_local, nombre_visitante,
    contexto, promedio_global, cfg,
):
    """
    Motor de predicción adaptado para selecciones.
    cfg = perfil del torneo (PERFILES_SELECCIONES[slug]).
    contexto = datos del partido (altitud_sede, es_neutro, etc.)
    """
    es_neutro = contexto.get("es_neutro", False)
    ctx_l = {**contexto, "es_local": True}
    ctx_v = {**contexto, "es_local": False}

    # ── Capa 1: Poisson ──────────────────────────────────────────────────────
    lambda_local, lambda_visitante = calcular_lambdas(
        sel_local, sel_visitante, contexto, promedio_global
    )
    p_local, p_empate, p_visitante = probabilidades_poisson(lambda_local, lambda_visitante)

    # ── Capa 2: Fuerza base ──────────────────────────────────────────────────
    fb_local     = calcular_fuerza_base(sel_local,     ctx_l, cfg)
    fb_visitante = calcular_fuerza_base(sel_visitante, ctx_v, cfg)

    # ── H2H ─────────────────────────────────────────────────────────────────
    if cfg["usa_h2h"] and h2h_data:
        h2h_local, n_h2h, partidos_h2h = calcular_h2h_score(
            nombre_local, nombre_visitante, h2h_data
        )
    else:
        h2h_local, n_h2h, partidos_h2h = 0.5, 0, []
    h2h_visitante = 1.0 - h2h_local

    # ── Ranking FIFA ─────────────────────────────────────────────────────────
    if cfg["usa_ranking_fifa"]:
        rank_l = normalizar_ranking_fifa(sel_local["ranking_fifa"])
        rank_v = normalizar_ranking_fifa(sel_visitante["ranking_fifa"])
    else:
        rank_l = rank_v = 0.5   # neutro

    # ── Altitud (como factor de fuerza relativa) ─────────────────────────────
    if cfg["usa_altitud"]:
        alt_sede = contexto.get("altitud_sede", 0)
        factor_alt_l = calcular_factor_altitud(alt_sede, sel_local.get("altitud_base", 0))
        factor_alt_v = calcular_factor_altitud(alt_sede, sel_visitante.get("altitud_base", 0))
        # Normalizar a 0..1 (si son iguales → 0.5 para ambos)
        total_alt = factor_alt_l + factor_alt_v
        alt_norm_l = factor_alt_l / total_alt if total_alt > 0 else 0.5
        alt_norm_v = factor_alt_v / total_alt if total_alt > 0 else 0.5
    else:
        alt_norm_l = alt_norm_v = 0.5

    # ── Fuerza compuesta ─────────────────────────────────────────────────────
    PESO_BASE    = cfg["PESO_BASE"]
    PESO_H2H     = cfg["PESO_H2H"]
    PESO_RANKING = cfg["PESO_RANKING"]
    PESO_ALTITUD = cfg["PESO_ALTITUD"]

    f_local = (
        fb_local      * PESO_BASE    +
        h2h_local     * PESO_H2H     +
        rank_l        * PESO_RANKING +
        alt_norm_l    * PESO_ALTITUD
    )
    f_visitante = (
        fb_visitante  * PESO_BASE    +
        h2h_visitante * PESO_H2H     +
        rank_v        * PESO_RANKING +
        alt_norm_v    * PESO_ALTITUD
    )

    # ── Score logístico ──────────────────────────────────────────────────────
    score   = f_local - f_visitante
    ratio_l = 1 / (1 + math.exp(-cfg["K_LOGISTICO"] * score))
    ratio_v = 1 - ratio_l

    if ratio_l > cfg["MAX_FAVORITO"]:
        ratio_l = cfg["MAX_FAVORITO"]
        ratio_v = 1 - ratio_l
    if ratio_v > cfg["MAX_FAVORITO"]:
        ratio_v = cfg["MAX_FAVORITO"]
        ratio_l = 1 - ratio_v

    # ── Empate ───────────────────────────────────────────────────────────────
    prob_empate_f = calcular_prob_empate(f_local, f_visitante, sel_local, sel_visitante, es_neutro)
    restante      = 1.0 - prob_empate_f
    prob_local_f     = restante * ratio_l
    prob_visitante_f = restante * ratio_v

    # ── Fusión Poisson + fuerza ──────────────────────────────────────────────
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
        "n_h2h":            n_h2h,
        "partidos_h2h":     partidos_h2h,
        "fb_local":         fb_local,
        "fb_visitante":     fb_visitante,
        "lambda_local":     lambda_local,
        "lambda_visitante": lambda_visitante,
        "factor_altitud_local":     calcular_factor_altitud(contexto.get("altitud_sede",0), sel_local.get("altitud_base",0)),
        "factor_altitud_visitante": calcular_factor_altitud(contexto.get("altitud_sede",0), sel_visitante.get("altitud_base",0)),
        "rank_l":           rank_l,
        "rank_v":           rank_v,
    }


# =============================
# ANÁLISIS ESTRUCTURADO
# =============================

def generar_analisis(local, visitante, resultado, nombre_local, nombre_visitante, contexto, cfg):
    factores = []
    altitud_sede = contexto.get("altitud_sede", 0)
    ciudad_sede  = contexto.get("ciudad_sede", "")
    es_neutro    = contexto.get("es_neutro", False)

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
        "factor":    "Forma reciente",
        "impacto":   nivel_impacto(abs(fl - fv)),
        "tipo":      "forma",
        "local":     {"valor": round(fl, 2), "ultimos_5": ul5_l, "nombre": nombre_local},
        "visitante": {"valor": round(fv, 2), "ultimos_5": ul5_v, "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 2. RANKING FIFA ──────────────────────────────────────────────────────
    rl = local["ranking_fifa"]
    rv = visitante["ranking_fifa"]
    pl = local["puntos_fifa"]
    pv = visitante["puntos_fifa"]
    dif_rank = abs(rl - rv)
    favorito_rank = nombre_local if rl < rv else nombre_visitante
    if dif_rank >= 30:
        interp = (f"Diferencia significativa en ranking FIFA: #{rl} {nombre_local} "
                  f"({pl:.0f} pts) vs #{rv} {nombre_visitante} ({pv:.0f} pts). "
                  f"{favorito_rank} tiene ventaja objetiva de calidad.")
    elif dif_rank >= 10:
        interp = (f"Leve diferencia en ranking: #{rl} {nombre_local} vs "
                  f"#{rv} {nombre_visitante}. El factor puede influir en momentos clave.")
    else:
        interp = (f"Selecciones parejas en ranking FIFA: #{rl} vs #{rv}. "
                  f"La calidad individual no diferencia decisivamente.")

    factores.append({
        "factor":    "Ranking FIFA",
        "impacto":   nivel_impacto(dif_rank / 200.0),
        "tipo":      "barras",
        "local":     {"etiqueta": f"#{rl} FIFA", "valor": round(resultado["rank_l"],3), "puntos": round(pl,1), "nombre": nombre_local},
        "visitante": {"etiqueta": f"#{rv} FIFA", "valor": round(resultado["rank_v"],3), "puntos": round(pv,1), "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 3. ALTITUD ───────────────────────────────────────────────────────────
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

    # ── 4. POTENCIAL OFENSIVO Y DEFENSIVO ────────────────────────────────────
    gf_l = local["goles_favor_promedio"];    gc_l = local["goles_contra_promedio"]
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

    # ── 5. H2H (si aplica) ───────────────────────────────────────────────────
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
    # Reemplazar si ya existe el mismo id
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
    """
    Genera la proyección de un partido a partir de un ítem del fixture.

    fixture_item: dict con los datos del partido (del fixture.json)
    db_selecciones: dict con todas las selecciones
    h2h: dict con historial directo (opcional)
    perfil_slug: clave de PERFILES_SELECCIONES
    """
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

    # Contexto del partido (incluye altitud, sede, etc.)
    altitud_sede = fixture_item.get("altitud_sede", 0)
    pais_sede    = fixture_item.get("pais_sede", "")
    es_neutro    = pais_sede.lower() not in [
        normalizar_nombre(nombre_local),
        normalizar_nombre(nombre_visitante),
        local_raw.get("nombre", "").lower(),
        visitante_raw.get("nombre", "").lower(),
    ]
    # Refinamiento: si el país de sede coincide con el nombre del local, no es neutro
    # Esto es simplista; para una mayor precisión, se puede enriquecer con un campo
    # "es_neutro" directamente en el fixture.
    es_neutro = fixture_item.get("es_neutro", es_neutro)

    contexto = {
        "altitud_sede":    altitud_sede,
        "ciudad_sede":     fixture_item.get("ciudad_sede", ""),
        "pais_sede":       pais_sede,
        "estadio":         fixture_item.get("estadio", ""),
        "es_neutro":       es_neutro,
        "contexto_altitud": fixture_item.get("contexto_altitud", f"Sede a {altitud_sede}m"),
    }

    promedio_global = calcular_promedio_global(db_selecciones)
    h2h_data        = h2h or {}

    resultado = predecir_probabilidades(
        local, visitante, h2h_data,
        nombre_local, nombre_visitante,
        contexto, promedio_global, cfg,
    )

    maxima = max(resultado["local"], resultado["empate"], resultado["visitante"])
    if   maxima == resultado["local"]:   pred = local["nombre"]
    elif maxima == resultado["empate"]:  pred = "Empate"
    else:                                pred = visitante["nombre"]

    analisis = generar_analisis(
        local, visitante, resultado,
        nombre_local, nombre_visitante,
        contexto, cfg,
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
        "analisis":         analisis,
    }

    guardar_resultado(output, archivo_salida)
    return output


# =============================
# CONFIGURACIÓN CENTRAL
# =============================

DB_CONFIG = {
    "amistosos_jun2026": {
        "carpeta":  "amistosos-jun2026",
        "perfil":   "amistoso",
        "salida":   "proyecciones.json",
    },
    # En el futuro:
    # "mundial_grupos": {
    #     "carpeta": "mundial-2026-grupos",
    #     "perfil":  "mundial_grupos",
    #     "salida":  "mundial_grupos.json",
    # },
    # "eliminatorias_conmebol": {
    #     "carpeta": "eliminatorias-conmebol",
    #     "perfil":  "eliminatoria_conmebol",
    #     "salida":  "eliminatorias.json",
    # },
}


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    # ── Cargar DB y fixture ───────────────────────────────────────────────────
    cfg_db = DB_CONFIG["amistosos_jun2026"]
    carpeta = cfg_db["carpeta"]

    print("📂 Cargando datos...\n")
    db_selecciones = cargar_selecciones(carpeta)
    fixture        = cargar_fixture(carpeta)
    h2h_data       = cargar_h2h(carpeta)  # vacío si no existe

    print(f"  ✓ {len(db_selecciones)} selecciones cargadas")
    print(f"  ✓ {len(fixture)} partidos en fixture")
    print(f"  ✓ H2H: {'cargado' if h2h_data else 'no disponible'}")
    print()

    # ── Limpiar proyecciones anteriores ──────────────────────────────────────
    try:
        os.remove(cfg_db["salida"])
    except FileNotFoundError:
        pass

    # ── Generar proyecciones ──────────────────────────────────────────────────
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

            # Indicadores de altitud
            alt = p["altitud_sede"]
            tag_alt = ""
            if alt >= 2500:
                tag_alt = f" 🏔 {alt}m"
            elif alt >= 1500:
                tag_alt = f" ⛰ {alt}m"

            sede = f"{p['ciudad_sede']}{tag_alt}"
            neutro = " [NEUTRO]" if p["es_neutro"] else ""

            print(f"  ⚽ {p['local']:<20} vs {p['visitante']:<20}  {sede}{neutro}")
            print(f"     {p['prob_local']:.1%} / {p['prob_empate']:.1%} / {p['prob_visitante']:.1%}"
                  f"  →  {p['prediccion']}  [{p['confianza']}]")
            print(f"     λ {p['lambda_local']:.2f} / {p['lambda_visitante']:.2f}"
                  f"  |  Alt: {p['factor_altitud_local']:.3f} vs {p['factor_altitud_visitante']:.3f}")
            print()

        except Exception as e:
            errores += 1
            print(f"  ❌ Error en {partido.get('local','?')} vs {partido.get('visitante','?')}: {e}")
            print()

    print("="*60)
    print(f"✅ Completado. {len(fixture)-errores} proyecciones generadas → {cfg_db['salida']}")
    if errores:
        print(f"  ⚠  {errores} errores (revisa los nombres en selecciones.json y fixture.json)")
"""
=============================================================
  MODELO DE PROBABILIDADES POR GRUPO — MUNDIAL 2026
  Don Octavio Web
  v2.0 — Actualizado con factor SEDE y ALTITUD
=============================================================

MÉTRICA PRINCIPAL:
    prob_lider  →  % de veces que cada equipo queda 1° del grupo
                   Los 4 equipos de cada grupo suman exactamente 100%.

NOVEDADES v2.0:
    ✦ Factor sede real: cada partido se juega en una ciudad
      específica; si una selección es "local" (anfitriona) en
      esa ciudad recibe un bono. Si ya está acostumbrada a la
      altitud de esa ciudad, recibe un bono adicional.
    ✦ Factor altitud: diferencia de metros s.n.m. entre
      la ciudad de origen del equipo y la sede del partido.
      A mayor diferencia → penalización de rendimiento.
    ✦ Los dos factores se aplican partido a partido (no al
      grupo en conjunto) y se promedian sobre los 3 partidos
      de cada equipo para obtener un ajuste neto por equipo.

USO:
    python mundial/data/modelo_grupos.py

SALIDA:
    mundial/data/probabilidades_grupos.json

DEPENDENCIAS:
    Ninguna — Python puro (3.8+)
"""

import json
import math
import random
import re
import sys
from pathlib import Path


# =============================================================
#  RUTAS
# =============================================================

BASE_DIR    = Path(__file__).parent
RUTA_GRUPOS = BASE_DIR / "grupos.json"
RUTA_SELEC  = BASE_DIR / "selecciones.json"
RUTA_SALIDA = BASE_DIR / "probabilidades_grupos.json"


# =============================================================
#  PESOS DEL MODELO (v1 — sin cambios)
# =============================================================

PESOS = {
    "puntos_fifa":     0.38,
    "forma_oficial":   0.22,
    "win_rate_neutro": 0.18,
    "diff_goles":      0.12,
    "win_rate_visita": 0.07,
    "win_rate_local":  0.03,
}

FIFA_MAX = 1900.0


# =============================================================
#  SEDES DEL MUNDIAL 2026
#  altitud_m : metros sobre el nivel del mar
#  pais      : país anfitrión de la sede
# =============================================================

SEDES = {
    "Mexico City":       {"altitud_m": 2240, "pais": "Mexico"},
    "Guadalajara":       {"altitud_m": 1566, "pais": "Mexico"},
    "Monterrey":         {"altitud_m":  538, "pais": "Mexico"},
    "New York":          {"altitud_m":    5, "pais": "USA"},
    "Los Angeles":       {"altitud_m":   71, "pais": "USA"},
    "Dallas":            {"altitud_m":  183, "pais": "USA"},
    "Atlanta":           {"altitud_m":  320, "pais": "USA"},
    "Miami":             {"altitud_m":    2, "pais": "USA"},
    "Houston":           {"altitud_m":   15, "pais": "USA"},
    "Kansas City":       {"altitud_m":  270, "pais": "USA"},
    "Philadelphia":      {"altitud_m":   12, "pais": "USA"},
    "San Francisco":     {"altitud_m":   16, "pais": "USA"},
    "Seattle":           {"altitud_m":   56, "pais": "USA"},
    "Boston":            {"altitud_m":   43, "pais": "USA"},
    "Toronto":           {"altitud_m":   76, "pais": "Canada"},
    "Vancouver":         {"altitud_m":    2, "pais": "Canada"},
}


# =============================================================
#  ALTITUD APROXIMADA DE LAS CAPITALES / CIUDADES PRINCIPALES
#  DE CADA SELECCIÓN (metros s.n.m.)
#  Usada para calcular la diferencia de altitud con la sede.
# =============================================================

ALTITUD_PAIS = {
    # CONCACAF (anfitriones)
    "Mexico":          2240,   # Ciudad de México
    "USA":               15,   # promedio ponderado (NY, LA, etc.)
    "Canada":            76,   # Toronto / Ottawa

    # CONMEBOL
    "Argentina":         25,
    "Brazil":            10,
    "Uruguay":           43,
    "Colombia":        2625,   # Bogotá — ya acostumbrados a altitud
    "Ecuador":         2850,   # Quito
    "Paraguay":        124,
    "Chile":           567,
    "Bolivia":        3640,   # La Paz — extremo
    "Venezuela":      900,
    "Peru":           154,

    # UEFA
    "France":           35,
    "England":          11,
    "Spain":           655,
    "Germany":         34,
    "Portugal":         92,
    "Netherlands":       5,
    "Belgium":          37,
    "Italy":            21,
    "Switzerland":     540,
    "Croatia":          158,
    "Austria":          171,
    "Sweden":            28,
    "Norway":            23,
    "Denmark":            7,
    "Serbia":           117,
    "Poland":            90,
    "Czechia":          399,
    "Slovakia":         152,
    "Hungary":          108,
    "Scotland":          35,
    "Wales":             62,
    "Turkey":           938,   # Ankara
    "Romania":           69,
    "Kosovo":           652,
    "Bosnia and Herzegovina": 511,
    "Ukraine":         179,
    "Greece":            24,
    "North Macedonia":  245,

    # CAF
    "Morocco":         590,
    "Senegal":           22,
    "Tunisia":           34,
    "Algeria":          730,
    "Egypt":             23,
    "South Africa":    1753,   # Johannesburgo
    "Nigeria":           41,
    "Cameroon":        726,
    "Ghana":            61,
    "Ivory Coast":       23,
    "DR Congo":        312,
    "Haiti":             30,
    "Cape Verde":        17,
    "Curaçao":            3,

    # AFC
    "South Korea":       38,
    "Japan":              17,
    "Saudi Arabia":      648,
    "Australia":          35,
    "Iran":             1191,
    "Iraq":              34,
    "Jordan":           774,
    "New Zealand":       37,
    "Uzbekistan":       455,

    # Por defecto para desconocidos
    "_default":          50,
}


# =============================================================
#  PARTIDOS DE GRUPO — Mundial 2026
#  Fuente: calendario oficial FIFA / MLS Soccer / ESPN
#  Formato: (equipo_1, equipo_2, sede)
# =============================================================

PARTIDOS_GRUPO = [
    # ── GRUPO A ──────────────────────────────────────────────
    ("Mexico",      "South Africa",  "Mexico City"),
    ("South Korea", "Czechia",       "Guadalajara"),
    ("Czechia",     "South Africa",  "Atlanta"),
    ("Mexico",      "South Korea",   "Guadalajara"),
    ("South Africa","South Korea",   "Monterrey"),
    ("Czechia",     "Mexico",        "Mexico City"),

    # ── GRUPO B ──────────────────────────────────────────────
    ("Canada",      "Bosnia and Herzegovina", "Toronto"),
    ("Qatar",       "Switzerland",            "San Francisco"),
    ("Switzerland", "Bosnia and Herzegovina", "Los Angeles"),
    ("Canada",      "Qatar",                  "Vancouver"),
    ("Switzerland", "Canada",                 "Vancouver"),
    ("Bosnia and Herzegovina", "Qatar",        "Seattle"),

    # ── GRUPO C ──────────────────────────────────────────────
    ("Brazil",      "Morocco",   "New York"),
    ("Haiti",       "Scotland",  "Boston"),
    ("Scotland",    "Morocco",   "Boston"),
    ("Brazil",      "Haiti",     "Philadelphia"),
    ("Morocco",     "Haiti",     "Atlanta"),
    ("Scotland",    "Brazil",    "Philadelphia"),

    # ── GRUPO D ──────────────────────────────────────────────
    ("USA",         "Paraguay",  "Los Angeles"),
    ("Australia",   "Turkey",    "Vancouver"),
    ("USA",         "Australia", "Seattle"),
    ("Turkey",      "Paraguay",  "San Francisco"),
    ("Turkey",      "USA",       "Los Angeles"),
    ("Paraguay",    "Australia", "Miami"),

    # ── GRUPO E ──────────────────────────────────────────────
    ("Germany",     "Curaçao",   "Houston"),
    ("Ivory Coast", "Ecuador",   "Philadelphia"),
    ("Ecuador",     "Curaçao",   "Kansas City"),
    ("Germany",     "Ivory Coast","New York"),
    ("Ecuador",     "Germany",   "New York"),
    ("Curaçao",     "Ivory Coast","Miami"),

    # ── GRUPO F ──────────────────────────────────────────────
    ("Netherlands", "Japan",     "Dallas"),
    ("Sweden",      "Tunisia",   "Monterrey"),
    ("Netherlands", "Sweden",    "Houston"),
    ("Japan",       "Tunisia",   "Monterrey"),
    ("Japan",       "Sweden",    "Dallas"),
    ("Tunisia",     "Netherlands","Kansas City"),

    # ── GRUPO G ──────────────────────────────────────────────
    ("Belgium",     "Egypt",     "Seattle"),
    ("Iran",        "New Zealand","Los Angeles"),
    ("Belgium",     "Iran",      "Los Angeles"),
    ("Egypt",       "New Zealand","Miami"),
    ("Belgium",     "New Zealand","San Francisco"),
    ("Iran",        "Egypt",     "Dallas"),

    # ── GRUPO H ──────────────────────────────────────────────
    ("Spain",       "Cape Verde","Atlanta"),
    ("Saudi Arabia","Uruguay",   "Miami"),
    ("Spain",       "Saudi Arabia","Atlanta"),
    ("Uruguay",     "Cape Verde","Houston"),
    ("Uruguay",     "Spain",     "Guadalajara"),
    ("Cape Verde",  "Saudi Arabia","Houston"),

    # ── GRUPO I ──────────────────────────────────────────────
    ("France",      "Senegal",   "New York"),
    ("Iraq",        "Norway",    "Boston"),
    ("Norway",      "France",    "Boston"),
    ("Senegal",     "Iraq",      "Toronto"),
    ("France",      "Iraq",      "Kansas City"),
    ("Senegal",     "Norway",    "Philadelphia"),

    # ── GRUPO J ──────────────────────────────────────────────
    ("Argentina",   "Algeria",   "Kansas City"),
    ("Austria",     "Jordan",    "San Francisco"),
    ("Argentina",   "Austria",   "Dallas"),
    ("Algeria",     "Jordan",    "Philadelphia"),
    ("Jordan",      "Argentina", "Dallas"),
    ("Algeria",     "Austria",   "Kansas City"),

    # ── GRUPO K ──────────────────────────────────────────────
    ("Portugal",    "DR Congo",  "Houston"),
    ("Uzbekistan",  "Colombia",  "Mexico City"),
    ("Portugal",    "Uzbekistan","Houston"),
    ("Colombia",    "DR Congo",  "Guadalajara"),
    ("Colombia",    "Portugal",  "Seattle"),
    ("DR Congo",    "Uzbekistan","Atlanta"),

    # ── GRUPO L ──────────────────────────────────────────────
    ("England",     "Croatia",   "Dallas"),
    ("Ghana",       "Panama",    "Toronto"),
    ("England",     "Ghana",     "Boston"),
    ("Panama",      "Croatia",   "New York"),
    ("Croatia",     "Ghana",     "Philadelphia"),
    ("Panama",      "England",   "Miami"),
]


# =============================================================
#  NACIONES ANFITRIONAS y sus ventajas
# =============================================================

NACIONES_ANFITRIONAS = {
    "Mexico":  "Mexico",
    "USA":     "USA",
    "Canada":  "Canada",
}

# Bono de localía: fracción que se suma a la fuerza del equipo
# cuando juega en su propio país anfitrión.
BONO_LOCAL   = 0.04   # 4% de la fuerza → ventaja de afición/logística
# Penalización por altitud: reducción de fuerza por cada 1000 m de diferencia
PENALIZACION_ALTITUD_POR_1000M = 0.025   # 2.5% por cada 1000 m de diferencia


# =============================================================
#  UTILIDADES
# =============================================================

def clamp(valor, minimo=0.0, maximo=1.0):
    return max(minimo, min(maximo, valor))


def normalizar_clave(nombre):
    texto = nombre.lower().strip()
    reemplazos = {
        "á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n",
        "à":"a","è":"e","ì":"i","ò":"o","ù":"u",
        "â":"a","ê":"e","î":"i","ô":"o","û":"u",
        "ã":"a","õ":"o","ç":"c",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def normal_sample(mu=0.0, sigma=1.0):
    while True:
        u1 = random.random()
        u2 = random.random()
        if u1 > 0.0:
            break
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


# =============================================================
#  ALTITUD DE PAÍS (con fallback)
# =============================================================

def get_altitud_pais(nombre_equipo):
    for k, v in ALTITUD_PAIS.items():
        if normalizar_clave(k) == normalizar_clave(nombre_equipo):
            return v
    return ALTITUD_PAIS["_default"]


# =============================================================
#  CÁLCULO DE AJUSTE SEDE+ALTITUD PARA UN EQUIPO
#
#  Para cada partido del grupo en que participa el equipo:
#    1. Bono local si juega en su país anfitrión
#    2. Penalización por diferencia de altitud con la sede
#  El ajuste neto se promedia sobre los 3 partidos.
#
#  Devuelve un multiplicador: 1.0 = sin efecto,
#    > 1.0 = ventaja neta,  < 1.0 = desventaja neta.
# =============================================================

def calcular_ajuste_sede(nombre_equipo):
    alt_origen = get_altitud_pais(nombre_equipo)
    pais_anfitrion = NACIONES_ANFITRIONAS.get(nombre_equipo)

    ajustes = []
    for eq1, eq2, ciudad in PARTIDOS_GRUPO:
        if normalizar_clave(eq1) != normalizar_clave(nombre_equipo) and \
           normalizar_clave(eq2) != normalizar_clave(nombre_equipo):
            continue

        sede_info = SEDES.get(ciudad, {"altitud_m": 50, "pais": "USA"})
        alt_sede  = sede_info["altitud_m"]

        # Diferencia de altitud en metros
        diff_alt = abs(alt_sede - alt_origen)
        # Convertir a penalización (máximo ~10% a 4000 m de diferencia)
        pen_alt  = (diff_alt / 1000.0) * PENALIZACION_ALTITUD_POR_1000M

        # Bono local si el equipo es anfitrión y juega en su propio país
        bono = BONO_LOCAL if (pais_anfitrion and sede_info["pais"] == pais_anfitrion) else 0.0

        ajuste_partido = 1.0 + bono - pen_alt
        ajustes.append(ajuste_partido)

    if not ajustes:
        return 1.0

    return sum(ajustes) / len(ajustes)


# =============================================================
#  CÁLCULO DE FUERZA INDIVIDUAL
# =============================================================

def calcular_fuerza(sel):
    f_fifa   = clamp(sel.get("puntos_fifa", 0.0) / FIFA_MAX)
    f_forma  = clamp(sel.get("forma_oficial", 0.0))
    f_neutro = clamp(sel.get("win_rate_neutro", 0.0))
    f_local  = clamp(sel.get("win_rate_local", 0.0))
    f_visita = clamp(sel.get("win_rate_visita", 0.0))

    diff   = sel.get("goles_favor_oficial", 0.0) - sel.get("goles_contra_oficial", 0.0)
    f_diff = clamp((diff + 3.0) / 6.0)

    return (
        f_fifa    * PESOS["puntos_fifa"]     +
        f_forma   * PESOS["forma_oficial"]   +
        f_neutro  * PESOS["win_rate_neutro"] +
        f_diff    * PESOS["diff_goles"]      +
        f_visita  * PESOS["win_rate_visita"] +
        f_local   * PESOS["win_rate_local"]
    )


# =============================================================
#  MONTE CARLO — con fuerzas ajustadas por sede/altitud
# =============================================================

def monte_carlo(fuerzas, n_sim=100_000, seed=2026):
    random.seed(seed)
    n       = len(fuerzas)
    media   = sum(fuerzas) / n
    sigma   = media * 0.35
    conteos = [[0] * n for _ in range(n)]

    for _ in range(n_sim):
        sim   = [max(0.001, f + normal_sample(0, sigma)) for f in fuerzas]
        orden = sorted(range(n), key=lambda i: sim[i], reverse=True)
        for pos, idx in enumerate(orden):
            conteos[idx][pos] += 1

    return [[c / n_sim for c in fila] for fila in conteos]


# =============================================================
#  BUSCAR SELECCIÓN
# =============================================================

def buscar_seleccion(nombre_eq, selecciones):
    clave = normalizar_clave(nombre_eq)
    if clave in selecciones:
        return selecciones[clave]
    for k, v in selecciones.items():
        if normalizar_clave(k) == clave:
            return v
        if normalizar_clave(v.get("nombre", "")) == clave:
            return v
    return None


# =============================================================
#  CÁLCULO DE PROBABILIDADES POR GRUPO
# =============================================================

def calcular_grupo(grupo_raw, selecciones):
    nombre_grupo   = grupo_raw["grupo"]
    equipos_raw    = grupo_raw["equipos"]
    no_encontrados = []

    equipos = []
    for eq in equipos_raw:
        nombre_eq = eq["equipo"]
        sel       = buscar_seleccion(nombre_eq, selecciones)

        if sel is None:
            no_encontrados.append(nombre_eq)
            sel = {
                "nombre":               nombre_eq,
                "puntos_fifa":          800.0,
                "forma_oficial":        0.3,
                "win_rate_neutro":      0.3,
                "goles_favor_oficial":  1.0,
                "goles_contra_oficial": 1.5,
                "win_rate_local":       0.3,
                "win_rate_visita":      0.3,
            }

        fuerza_base = max(0.01, calcular_fuerza(sel))

        # ── Ajuste sede + altitud ──────────────────────────
        ajuste_sede = calcular_ajuste_sede(nombre_eq)
        fuerza_ajustada = max(0.01, fuerza_base * ajuste_sede)

        equipos.append({
            "raw":            eq,
            "sel":            sel,
            "nombre":         nombre_eq,
            "fuerza_base":    fuerza_base,
            "ajuste_sede":    round(ajuste_sede, 4),
            "fuerza":         fuerza_ajustada,
        })

    fuerzas = [e["fuerza"] for e in equipos]
    probs   = monte_carlo(fuerzas)

    resultado_equipos = []
    for i, eq in enumerate(equipos):
        raw = eq["raw"]
        sel = eq["sel"]
        resultado_equipos.append({
            "equipo":          eq["nombre"],
            "abreviacion":     raw.get("abreviacion", ""),
            "escudo":          raw.get("escudo", sel.get("escudo", "")),
            "posicion_sorteo": raw.get("posicion", i + 1),
            "ranking_fifa":    sel.get("ranking_fifa", 999),
            "puntos_fifa":     sel.get("puntos_fifa", 0),
            "fuerza_modelo":   round(eq["fuerza_base"], 4),
            "ajuste_sede":     eq["ajuste_sede"],
            "fuerza_ajustada": round(eq["fuerza"], 4),

            "prob_lider":   round(probs[i][0] * 100, 2),
            "prob_segundo": round(probs[i][1] * 100, 2),
            "prob_tercero": round(probs[i][2] * 100, 2),
            "prob_cuarto":  round(probs[i][3] * 100, 2),

            "tabla": {
                "partidos":         raw.get("partidos", 0),
                "ganados":          raw.get("ganados", 0),
                "empatados":        raw.get("empatados", 0),
                "perdidos":         raw.get("perdidos", 0),
                "goles_favor":      raw.get("goles_favor", 0),
                "goles_contra":     raw.get("goles_contra", 0),
                "diferencia_goles": raw.get("diferencia_goles", 0),
                "puntos":           raw.get("puntos", 0),
            },
        })

    resultado_equipos.sort(key=lambda x: x["prob_lider"], reverse=True)
    resultado_equipos[0]["es_favorito"] = True
    for eq in resultado_equipos[1:]:
        eq["es_favorito"] = False

    suma = sum(eq["prob_lider"] for eq in resultado_equipos)

    return {
        "grupo":           nombre_grupo,
        "equipos":         resultado_equipos,
        "favorito":        resultado_equipos[0]["equipo"],
        "suma_prob_lider": round(suma, 2),
        "no_encontrados":  no_encontrados,
    }


# =============================================================
#  ENTRY POINT
# =============================================================

def main():
    for ruta in [RUTA_GRUPOS, RUTA_SELEC]:
        if not ruta.exists():
            print(f"ERROR: No se encontró '{ruta}'")
            sys.exit(1)

    with open(RUTA_GRUPOS, "r", encoding="utf-8") as f:
        grupos_raw = json.load(f)

    with open(RUTA_SELEC, "r", encoding="utf-8") as f:
        selecciones = json.load(f)

    if isinstance(grupos_raw, dict):
        grupos_raw = grupos_raw.get("grupos", list(grupos_raw.values()))

    print(f"Selecciones cargadas : {len(selecciones)}")
    print(f"Grupos a procesar    : {len(grupos_raw)}")
    print()

    resultados = {}
    for grupo_raw in grupos_raw:
        resultado = calcular_grupo(grupo_raw, selecciones)
        letra     = resultado["grupo"].replace("Group ", "").strip()
        resultados[letra] = resultado

        print(f"  Grupo {letra}  (favorito: {resultado['favorito']})  [suma lider: {resultado['suma_prob_lider']}%]")
        for eq in resultado["equipos"]:
            marca = "★" if eq["es_favorito"] else " "
            print(
                f"    {marca} {eq['equipo']:<26}"
                f"FIFA #{eq['ranking_fifa']:<4} "
                f"Fuerza base:{eq['fuerza_modelo']:.4f} "
                f"AjusteSede:{eq['ajuste_sede']:+.4f}  "
                f"Lider:{eq['prob_lider']:>5.1f}%  "
                f"(2°:{eq['prob_segundo']:>4.1f}% / 3°:{eq['prob_tercero']:>4.1f}% / 4°:{eq['prob_cuarto']:>4.1f}%)"
            )
        if resultado["no_encontrados"]:
            print(f"    ⚠  Sin datos: {resultado['no_encontrados']}")
        print()

    salida = {
        "meta": {
            "fuente":        "Don Octavio Web",
            "mundial":       "FIFA World Cup 2026",
            "version":       "2.0",
            "metodo":        "Fuerza compuesta + Ajuste Sede/Altitud + Monte Carlo 100k simulaciones",
            "metrica_clave": (
                "prob_lider: % de veces que el equipo queda 1° del grupo. "
                "Los 4 equipos de cada grupo suman 100%."
            ),
            "pesos_modelo":  PESOS,
            "factores_v2": {
                "bono_local_pct":           BONO_LOCAL * 100,
                "penalizacion_por_1000m":   PENALIZACION_ALTITUD_POR_1000M * 100,
                "descripcion_ajuste_sede": (
                    "ajuste_sede es un multiplicador sobre la fuerza base. "
                    "Se calcula partido a partido y se promedia. "
                    "> 1.0 = ventaja neta (local + altitud favorable), "
                    "< 1.0 = desventaja neta."
                ),
            },
        },
        "grupos": resultados,
    }

    with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Listo → {RUTA_SALIDA}")


if __name__ == "__main__":
    main()
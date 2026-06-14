"""
=============================================================
  MODELO DE PROBABILIDADES POR GRUPO — MUNDIAL 2026
  Don Octavio Web
  v2.2 — Nuevo: Monte Carlo parte de tabla real
=============================================================

CAMBIOS v2.2 respecto a v2.1:
    ✦ NUEVO — Monte Carlo con tabla base real:
        El modelo ahora toma los puntos/goles/dif ya acumulados
        en grupos.json como punto de partida fijo.
        Solo simula los partidos que aún están en PARTIDOS_GRUPO.

    FLUJO DE USO:
        1. Cuando se juega un partido, elimínalo de PARTIDOS_GRUPO.
        2. Actualiza grupos.json con los resultados reales
           (puntos, ganados, goles_favor, goles_contra, etc.)
        3. Corre el script → las probabilidades se recalculan
           partiendo de la tabla real.

=============================================================

(Todos los fixes de v2.1 se mantienen)
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
#  PESOS DEL MODELO
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

FACTOR_COMPRESION = 0.70
SIGMA_MINIMO      = 0.07
FIFA_FALLBACK     = 1050.0


# =============================================================
#  SEDES DEL MUNDIAL 2026
# =============================================================

SEDES = {
    "Mexico City":  {"altitud_m": 2240, "pais": "Mexico"},
    "Guadalajara":  {"altitud_m": 1566, "pais": "Mexico"},
    "Monterrey":    {"altitud_m":  538, "pais": "Mexico"},
    "New York":     {"altitud_m":    5, "pais": "USA"},
    "Los Angeles":  {"altitud_m":   71, "pais": "USA"},
    "Dallas":       {"altitud_m":  183, "pais": "USA"},
    "Atlanta":      {"altitud_m":  320, "pais": "USA"},
    "Miami":        {"altitud_m":    2, "pais": "USA"},
    "Houston":      {"altitud_m":   15, "pais": "USA"},
    "Kansas City":  {"altitud_m":  270, "pais": "USA"},
    "Philadelphia": {"altitud_m":   12, "pais": "USA"},
    "San Francisco":{"altitud_m":   16, "pais": "USA"},
    "Seattle":      {"altitud_m":   56, "pais": "USA"},
    "Boston":       {"altitud_m":   43, "pais": "USA"},
    "Toronto":      {"altitud_m":   76, "pais": "Canada"},
    "Vancouver":    {"altitud_m":    2, "pais": "Canada"},
}


# =============================================================
#  ALTITUD APROXIMADA POR SELECCIÓN
# =============================================================

ALTITUD_PAIS = {
    "Mexico": 2240, "USA": 15, "Canada": 76,
    "Argentina": 25, "Brazil": 10, "Uruguay": 43,
    "Colombia": 2625, "Ecuador": 2850, "Paraguay": 124,
    "Chile": 567, "Bolivia": 3640, "Venezuela": 900, "Peru": 154,
    "France": 35, "England": 11, "Spain": 655, "Germany": 34,
    "Portugal": 92, "Netherlands": 5, "Belgium": 37, "Italy": 21,
    "Switzerland": 540, "Croatia": 158, "Austria": 171,
    "Sweden": 28, "Norway": 23, "Denmark": 7, "Serbia": 117,
    "Poland": 90, "Czechia": 399, "Slovakia": 152, "Hungary": 108,
    "Scotland": 35, "Wales": 62, "Turkey": 938, "Romania": 69,
    "Kosovo": 652, "Bosnia and Herzegovina": 511, "Ukraine": 179,
    "Greece": 24, "North Macedonia": 245,
    "Morocco": 590, "Senegal": 22, "Tunisia": 34, "Algeria": 730,
    "Egypt": 23, "South Africa": 1753, "Nigeria": 41,
    "Cameroon": 726, "Ghana": 61, "Ivory Coast": 23,
    "DR Congo": 312, "Cape Verde": 17, "Curaçao": 3,
    "South Korea": 38, "Japan": 17, "Saudi Arabia": 648,
    "Australia": 35, "Iran": 1191, "Iraq": 34, "Jordan": 774,
    "New Zealand": 37, "Uzbekistan": 455, "Qatar": 11,
    "Haiti": 30, "Panama": 43,
    "_default": 50,
}


# =============================================================
#  PARTIDOS PENDIENTES — Mundial 2026
#  ⚠ Elimina manualmente los partidos ya jugados.
#    El modelo solo simulará los que queden aquí.
# =============================================================

PARTIDOS_GRUPO = [
    # ── GRUPO A ──────────────────────────────────────────────
    # ("Mexico",      "South Africa",  "Mexico City"),   # JUGADO: 2-0
    # ("South Korea", "Czechia",       "Guadalajara"),   # JUGADO: 2-1
    ("Czechia",     "South Africa",  "Atlanta"),
    ("Mexico",      "South Korea",   "Guadalajara"),
    ("South Africa","South Korea",   "Monterrey"),
    ("Czechia",     "Mexico",        "Mexico City"),

    # ── GRUPO B ──────────────────────────────────────────────
    # ("Canada",      "Bosnia-Herzegovina", "Toronto"),  # JUGADO: 1-1
    # ("Qatar",       "Switzerland",  "San Francisco"),  # JUGADO: 1-1
    ("Switzerland", "Bosnia-Herzegovina", "Los Angeles"),
    ("Canada",      "Qatar",                  "Vancouver"),
    ("Switzerland", "Canada",                 "Vancouver"),
    ("Bosnia-Herzegovina", "Qatar",        "Seattle"),

    # ── GRUPO C ──────────────────────────────────────────────
    # ("Brazil",      "Morocco",   "New York"),  # JUGADO 1-1
    # ("Haiti",       "Scotland",  "Boston"),    # JUGADO 0-1
    ("Scotland",    "Morocco",   "Boston"),
    ("Brazil",      "Haiti",     "Philadelphia"),
    ("Morocco",     "Haiti",     "Atlanta"),
    ("Scotland",    "Brazil",    "Philadelphia"),

    # ── GRUPO D ──────────────────────────────────────────────
    # ("USA",         "Paraguay",  "Los Angeles"),   # JUGADO 4-1
    # ("Australia",   "Türkiye",    "Vancouver"),    # JUGADO 2-0
    ("United States", "Australia", "Seattle"),
    ("Türkiye",      "Paraguay",  "San Francisco"),
    ("Türkiye",  "United States", "Los Angeles"),
    ("Paraguay",    "Australia", "Miami"),

    # ── GRUPO E ──────────────────────────────────────────────
    ("Germany",     "Curaçao",    "Houston"),
    ("Ivory Coast", "Ecuador",    "Philadelphia"),
    ("Ecuador",     "Curaçao",    "Kansas City"),
    ("Germany",     "Ivory Coast","New York"),
    ("Ecuador",     "Germany",    "New York"),
    ("Curaçao",     "Ivory Coast","Miami"),

    # ── GRUPO F ──────────────────────────────────────────────
    ("Netherlands", "Japan",      "Dallas"),
    ("Sweden",      "Tunisia",    "Monterrey"),
    ("Netherlands", "Sweden",     "Houston"),
    ("Japan",       "Tunisia",    "Monterrey"),
    ("Japan",       "Sweden",     "Dallas"),
    ("Tunisia",     "Netherlands","Kansas City"),

    # ── GRUPO G ──────────────────────────────────────────────
    ("Belgium",     "Egypt",      "Seattle"),
    ("Iran",        "New Zealand","Los Angeles"),
    ("Belgium",     "Iran",       "Los Angeles"),
    ("Egypt",       "New Zealand","Miami"),
    ("Belgium",     "New Zealand","San Francisco"),
    ("Iran",        "Egypt",      "Dallas"),

    # ── GRUPO H ──────────────────────────────────────────────
    ("Spain",       "Cape Verde", "Atlanta"),
    ("Saudi Arabia","Uruguay",    "Miami"),
    ("Spain",       "Saudi Arabia","Atlanta"),
    ("Uruguay",     "Cape Verde", "Houston"),
    ("Uruguay",     "Spain",      "Guadalajara"),
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
    ("Portugal",    "Congo DR",  "Houston"),
    ("Uzbekistan",  "Colombia",  "Mexico City"),
    ("Portugal",    "Uzbekistan","Houston"),
    ("Colombia",    "Congo DR",  "Guadalajara"),
    ("Colombia",    "Portugal",  "Seattle"),
    ("Congo DR",    "Uzbekistan","Atlanta"),

    # ── GRUPO L ──────────────────────────────────────────────
    ("England",     "Croatia",   "Dallas"),
    ("Ghana",       "Panama",    "Toronto"),
    ("England",     "Ghana",     "Boston"),
    ("Panama",      "Croatia",   "New York"),
    ("Croatia",     "Ghana",     "Philadelphia"),
    ("Panama",      "England",   "Miami"),
]


# =============================================================
#  NACIONES ANFITRIONAS
# =============================================================

NACIONES_ANFITRIONAS = {"Mexico": "Mexico", "USA": "USA", "Canada": "Canada"}

BONO_LOCAL                     = 0.04
PENALIZACION_ALTITUD_POR_1000M = 0.025
TECHO_PENALIZACION_ALTITUD     = 0.06


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


def get_altitud_pais(nombre_equipo):
    for k, v in ALTITUD_PAIS.items():
        if normalizar_clave(k) == normalizar_clave(nombre_equipo):
            return v
    return ALTITUD_PAIS["_default"]


# =============================================================
#  AJUSTE SEDE + ALTITUD
# =============================================================

def calcular_ajuste_sede(nombre_equipo):
    alt_origen     = get_altitud_pais(nombre_equipo)
    pais_anfitrion = NACIONES_ANFITRIONAS.get(nombre_equipo)

    ajustes = []
    for eq1, eq2, ciudad in PARTIDOS_GRUPO:
        if normalizar_clave(eq1) != normalizar_clave(nombre_equipo) and \
           normalizar_clave(eq2) != normalizar_clave(nombre_equipo):
            continue

        sede_info = SEDES.get(ciudad, {"altitud_m": 50, "pais": "USA"})
        alt_sede  = sede_info["altitud_m"]
        diff_alt  = abs(alt_sede - alt_origen)

        pen_alt = min(
            (diff_alt / 1000.0) * PENALIZACION_ALTITUD_POR_1000M,
            TECHO_PENALIZACION_ALTITUD
        )

        bono = BONO_LOCAL if (pais_anfitrion and sede_info["pais"] == pais_anfitrion) else 0.0
        ajustes.append(1.0 + bono - pen_alt)

    return sum(ajustes) / len(ajustes) if ajustes else 1.0


# =============================================================
#  FUERZA INDIVIDUAL
# =============================================================

def calcular_fuerza(sel):
    f_fifa   = clamp(sel.get("puntos_fifa", 0.0) / FIFA_MAX)
    f_forma  = clamp(sel.get("forma_oficial", 0.0))
    f_neutro = clamp(sel.get("win_rate_neutro", 0.0))
    f_local  = clamp(sel.get("win_rate_local", 0.0))
    f_visita = clamp(sel.get("win_rate_visita", 0.0))
    diff     = sel.get("goles_favor_oficial", 0.0) - sel.get("goles_contra_oficial", 0.0)
    f_diff   = clamp((diff + 3.0) / 6.0)

    return (
        f_fifa    * PESOS["puntos_fifa"]     +
        f_forma   * PESOS["forma_oficial"]   +
        f_neutro  * PESOS["win_rate_neutro"] +
        f_diff    * PESOS["diff_goles"]      +
        f_visita  * PESOS["win_rate_visita"] +
        f_local   * PESOS["win_rate_local"]
    )


# =============================================================
#  ▼ NUEVO v2.2 — MONTE CARLO CON TABLA BASE REAL
# =============================================================

def monte_carlo_con_tabla(equipos_info, partidos_pendientes_grupo, n_sim=100_000, seed=2026):
    """
    Monte Carlo que:
      1. Parte de los puntos/goles REALES ya acumulados en grupos.json
      2. Solo simula los partidos que quedan en partidos_pendientes_grupo
      3. Ordena la tabla final por puntos → dif goles → goles a favor
    """
    random.seed(seed)
    n       = len(equipos_info)
    nombres = [e["nombre"] for e in equipos_info]

    # Fuerzas con compresión
    fuerzas_raw = [e["fuerza"] for e in equipos_info]
    media       = sum(fuerzas_raw) / n
    fuerzas     = {
        e["nombre"]: FACTOR_COMPRESION * e["fuerza"] + (1 - FACTOR_COMPRESION) * media
        for e in equipos_info
    }
    sigma   = max(media * 0.35, SIGMA_MINIMO)
    conteos = [[0] * n for _ in range(n)]

    # Tabla base: puntos/goles ya reales
    tabla_base = {
        e["nombre"]: {
            "puntos": float(e["raw"].get("puntos", 0)),
            "dg":     float(e["raw"].get("diferencia_goles", 0)),
            "gf":     float(e["raw"].get("goles_favor", 0)),
        }
        for e in equipos_info
    }

    # Índice de nombre → posición en lista (para conteos)
    idx_map = {nom: i for i, nom in enumerate(nombres)}

    for _ in range(n_sim):
        # Copiar tabla real como punto de partida
        pts = {nom: tabla_base[nom]["puntos"] for nom in nombres}
        dg  = {nom: tabla_base[nom]["dg"]     for nom in nombres}
        gf  = {nom: tabla_base[nom]["gf"]     for nom in nombres}

        # Simular solo partidos pendientes de este grupo
        for eq1, eq2, _ in partidos_pendientes_grupo:
            # Normalizar nombres para buscar en fuerzas
            nom1 = next((n for n in nombres if normalizar_clave(n) == normalizar_clave(eq1)), None)
            nom2 = next((n for n in nombres if normalizar_clave(n) == normalizar_clave(eq2)), None)
            if nom1 is None or nom2 is None:
                continue

            f1 = max(0.001, fuerzas[nom1] + normal_sample(0, sigma))
            f2 = max(0.001, fuerzas[nom2] + normal_sample(0, sigma))

            # Goles simulados (escala simple)
            g1 = max(0, round(f1 * 2.5 + normal_sample(0, 0.8)))
            g2 = max(0, round(f2 * 2.5 + normal_sample(0, 0.8)))

            # Puntos
            if g1 > g2:
                pts[nom1] += 3
            elif g2 > g1:
                pts[nom2] += 3
            else:
                pts[nom1] += 1
                pts[nom2] += 1

            # Goles
            dg[nom1] += g1 - g2
            dg[nom2] += g2 - g1
            gf[nom1] += g1
            gf[nom2] += g2

        # Ordenar tabla: puntos → dif goles → goles a favor
        orden = sorted(
            nombres,
            key=lambda nom: (pts[nom], dg[nom], gf[nom]),
            reverse=True
        )
        for pos, nom in enumerate(orden):
            conteos[idx_map[nom]][pos] += 1

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
#  CÁLCULO POR GRUPO  (actualizado para v2.2)
# =============================================================

def calcular_grupo(grupo_raw, selecciones):
    nombre_grupo   = grupo_raw["grupo"]
    equipos_raw    = grupo_raw["equipos"]
    no_encontrados = []

    # Nombres normalizados de este grupo
    nombres_grupo = {normalizar_clave(eq["equipo"]) for eq in equipos_raw}

    # ▼ NUEVO: filtrar solo partidos pendientes de este grupo
    partidos_pendientes_grupo = [
        (eq1, eq2, ciudad)
        for eq1, eq2, ciudad in PARTIDOS_GRUPO
        if normalizar_clave(eq1) in nombres_grupo
        and normalizar_clave(eq2) in nombres_grupo
    ]

    equipos = []
    for eq in equipos_raw:
        nombre_eq = eq["equipo"]
        sel       = buscar_seleccion(nombre_eq, selecciones)

        if sel is None:
            no_encontrados.append(nombre_eq)
            sel = {
                "nombre":               nombre_eq,
                "puntos_fifa":          FIFA_FALLBACK,
                "forma_oficial":        0.35,
                "win_rate_neutro":      0.35,
                "goles_favor_oficial":  1.0,
                "goles_contra_oficial": 1.2,
                "win_rate_local":       0.35,
                "win_rate_visita":      0.30,
            }

        fuerza_base     = max(0.01, calcular_fuerza(sel))
        ajuste_sede     = calcular_ajuste_sede(nombre_eq)
        fuerza_ajustada = max(0.01, fuerza_base * ajuste_sede)

        equipos.append({
            "raw":         eq,
            "sel":         sel,
            "nombre":      nombre_eq,
            "fuerza_base": fuerza_base,
            "ajuste_sede": round(ajuste_sede, 4),
            "fuerza":      fuerza_ajustada,
        })

    # ▼ NUEVO: usar Monte Carlo con tabla real
    probs = monte_carlo_con_tabla(equipos, partidos_pendientes_grupo)

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
            "prob_lider":      round(probs[i][0] * 100, 2),
            "prob_segundo":    round(probs[i][1] * 100, 2),
            "prob_tercero":    round(probs[i][2] * 100, 2),
            "prob_cuarto":     round(probs[i][3] * 100, 2),
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

    partidos_jugados  = 6 - len(partidos_pendientes_grupo)  # 6 total por grupo de 4
    partidos_restantes = len(partidos_pendientes_grupo)

    return {
        "grupo":              nombre_grupo,
        "equipos":            resultado_equipos,
        "favorito":           resultado_equipos[0]["equipo"],
        "suma_prob_lider":    round(sum(eq["prob_lider"] for eq in resultado_equipos), 2),
        "partidos_jugados":   partidos_jugados,
        "partidos_restantes": partidos_restantes,
        "no_encontrados":     no_encontrados,
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

        print(
            f"  Grupo {letra}  (favorito: {resultado['favorito']})  "
            f"[jugados: {resultado['partidos_jugados']}/6  "
            f"restantes: {resultado['partidos_restantes']}  "
            f"suma lider: {resultado['suma_prob_lider']}%]"
        )
        for eq in resultado["equipos"]:
            marca = "★" if eq["es_favorito"] else " "
            print(
                f"    {marca} {eq['equipo']:<26}"
                f"FIFA #{eq['ranking_fifa']:<4} "
                f"Pts:{eq['tabla']['puntos']:.0f}  "
                f"Fuerza:{eq['fuerza_modelo']:.4f} "
                f"AjusteSede:{eq['ajuste_sede']:+.4f}  "
                f"Lider:{eq['prob_lider']:>5.1f}%  "
                f"(2°:{eq['prob_segundo']:>4.1f}% / 3°:{eq['prob_tercero']:>4.1f}% / 4°:{eq['prob_cuarto']:>4.1f}%)"
            )
        if resultado["no_encontrados"]:
            print(f"    ⚠  Sin datos: {resultado['no_encontrados']}")
        print()

    salida = {
        "meta": {
            "fuente":  "Don Octavio Web",
            "mundial": "FIFA World Cup 2026",
            "version": "2.2",
            "metodo":  (
                "Fuerza compuesta + Ajuste Sede/Altitud + "
                "Monte Carlo 100k simulaciones con tabla real como base"
            ),
            "metrica_clave": (
                "prob_lider: % de veces que el equipo queda 1° del grupo. "
                "Los 4 equipos de cada grupo suman 100%."
            ),
            "pesos_modelo": PESOS,
            "novedades_v2_2": (
                "Monte Carlo parte de puntos/goles reales del grupos.json. "
                "Solo simula partidos que quedan en PARTIDOS_GRUPO. "
                "Para registrar un resultado: 1) comenta/elimina el partido "
                "de PARTIDOS_GRUPO, 2) actualiza grupos.json con stats reales."
            ),
        },
        "grupos": resultados,
    }

    with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Listo → {RUTA_SALIDA}")


if __name__ == "__main__":
    main()
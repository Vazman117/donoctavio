# scraper_mundial.py
#
# INSTALAR:
# pip install requests
#
# EJECUTAR:
# python scraper_mundial.py
#
# GENERA:
# /mundial/data/grupos.json       → posiciones por grupo
# /mundial/data/tabla.json        → tabla general
# /mundial/data/selecciones.json  → stats completas por selección
# /mundial/data/fixture.json      → partidos de hoy y mañana

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# =====================================================
# CONFIG
# =====================================================

BASE_ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
BASE_ESPN_V2 = "https://site.api.espn.com/apis/v2/sports/soccer"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Altitud base conocida por selección (metros sobre el nivel del mar)
# Representa la altitud media de la ciudad principal / sede habitual
# Amplía este diccionario según necesites
# ------------------------------------------------------------------
ALTITUD_BASE = {
    "ARG": 25,   "BOL": 3640, "BRA": 10,  "CHI": 520,  "COL": 2600,
    "ECU": 2850, "PAR": 124,  "PER": 154, "URU": 43,   "VEN": 900,
    "USA": 0,    "CAN": 116,  "MEX": 2240,"CRC": 1170, "JAM": 40,
    "PAN": 0,    "HON": 900,  "GUA": 1500,"SLV": 658,  "TRI": 11,
    "AUT": 171,  "BEL": 56,   "CRO": 122, "CZE": 399,  "DEN": 12,
    "ENG": 24,   "FRA": 35,   "GER": 117, "GRE": 170,  "HUN": 102,
    "ITA": 21,   "NED": 0,    "POL": 90,  "POR": 92,   "ROU": 85,
    "SCO": 15,   "SRB": 117,  "SLO": 295, "ESP": 650,  "SWE": 28,
    "SWZ": 540,  "TUR": 938,  "UKR": 179, "WAL": 50,   "ALB": 110,
    "AUT": 171,  "BIH": 511,  "BUL": 550, "GEO": 380,  "ISL": 18,
    "KOS": 652,  "LVA": 7,    "MDA": 30,  "MKD": 245,  "MNE": 21,
    "NOR": 23,   "SVK": 172,  "FIN": 26,
    "EGY": 23,   "GHA": 61,   "CIV": 226, "MAR": 495,  "NGA": 60,
    "SEN": 22,   "TUN": 50,   "CMR": 760, "MLI": 381,  "ALG": 424,
    "RSA": 1700, "TAN": 1130, "ZIM": 1483,"UGA": 1189, "KEN": 1661,
    "AUS": 0,    "JPN": 40,   "KOR": 37,  "IRN": 1191, "SAU": 620,
    "QAT": 10,   "UAE": 5,    "CHN": 43,  "IDN": 8,    "IND": 216,
    "PHI": 15,   "THA": 2,    "MYS": 22,  "VIE": 12,   "BHR": 0,
    "OMA": 20,   "JOR": 820,  "IRQ": 34,  "SYR": 690,  "KUW": 55,
    "NZL": 30,   "FIJ": 18,
}

# ------------------------------------------------------------------
# Ranking FIFA masculino — edición abril 2026 (última antes del Mundial)
# Solo incluye las 48 selecciones clasificadas al Mundial 2026
# Fuente: https://www.fifa.com/fifa-world-ranking/men
# Actualizar manualmente cuando FIFA publique una nueva edición
# (se publica ~6 veces al año: feb, mar, abr, jun, ago, oct)
# ------------------------------------------------------------------
RANKING_FIFA = {
    # abreviacion_ESPN : (ranking, puntos)
    "ESP": (1,  1877.2), "ARG": (2,  1873.3), "FRA": (3,  1870.0),
    "ENG": (4,  1834.1), "BRA": (5,  1782.1), "POR": (6,  1764.9),
    "NED": (7,  1757.4), "BEL": (8,  1741.7), "GER": (9,  1720.0),
    "ITA": (10, 1711.5), "URU": (11, 1690.4), "COL": (12, 1687.2),
    "CRO": (13, 1658.7), "JPN": (14, 1650.5), "MAR": (15, 1645.1),
    "USA": (16, 1633.9), "MEX": (17, 1622.8), "SEN": (18, 1617.6),
    "DEN": (19, 1611.9), "SWZ": (20, 1609.2), "NOR": (21, 1600.4),
    "AUT": (22, 1595.7), "EGY": (23, 1589.3), "TUR": (24, 1584.1),
    "UKR": (25, 1572.6), "GHA": (26, 1560.8), "CIV": (27, 1551.3),
    "KOR": (28, 1545.9), "AUS": (29, 1539.4), "POL": (30, 1532.1),
    "IRN": (31, 1528.7), "PAR": (32, 1521.4), "RSA": (33, 1514.8),
    "ECU": (34, 1508.3), "SRB": (35, 1501.7), "CZE": (36, 1495.2),
    "CMR": (37, 1488.6), "BOL": (38, 1482.1), "SVK": (39, 1475.4),
    "HUN": (40, 1468.9), "NGA": (41, 1462.3), "NZL": (42, 1455.8),
    "SAU": (43, 1449.2), "CAN": (44, 1442.7), "TUN": (45, 1436.1),
    "PAN": (46, 1429.6), "ALB": (47, 1423.0), "GUA": (48, 1416.5),
    # Selecciones adicionales presentes en el mundial
    "VEN": (49, 1410.0), "CHN": (79, 1302.5), "IDN": (130, 1180.0),
}

# ------------------------------------------------------------------
# Sedes oficiales del Mundial 2026
# Cada entrada incluye todos los nombres posibles que ESPN puede devolver
# (nombre FIFA, nombre comercial actual, nombre histórico, apodos)
# La altitud es la de la ciudad, no la del edificio en sí
# ------------------------------------------------------------------
SEDES_MUNDIAL = [
    {
        "ciudad": "Ciudad de México", "pais": "MEX", "alt": 2240,
        "keywords": ["azteca", "banorte", "mexico city stadium", "estadio ciudad de mexico"],
    },
    {
        "ciudad": "Guadalajara, Jalisco", "pais": "MEX", "alt": 1566,
        "keywords": ["akron", "guadalajara stadium", "estadio akron"],
    },
    {
        "ciudad": "Monterrey, Nuevo León", "pais": "MEX", "alt": 538,
        "keywords": ["bbva", "bancomer", "monterrey stadium", "estadio bbva"],
    },
    {
        "ciudad": "Los Angeles, California", "pais": "USA", "alt": 93,
        "keywords": ["sofi", "sofi stadium", "inglewood"],
    },
    {
        "ciudad": "Pasadena, California", "pais": "USA", "alt": 236,
        "keywords": ["rose bowl"],
    },
    {
        "ciudad": "San Francisco Bay Area, California", "pais": "USA", "alt": 16,
        "keywords": ["levi", "levis", "santa clara"],
    },
    {
        "ciudad": "Seattle, Washington", "pais": "USA", "alt": 0,
        "keywords": ["lumen field", "lumen"],
    },
    {
        "ciudad": "East Rutherford, New Jersey", "pais": "USA", "alt": 5,
        "keywords": ["metlife", "met life", "new york stadium", "new jersey"],
    },
    {
        "ciudad": "Philadelphia, Pennsylvania", "pais": "USA", "alt": 12,
        "keywords": ["lincoln financial", "lincoln field", "philadelphia stadium"],
    },
    {
        "ciudad": "Foxborough, Massachusetts", "pais": "USA", "alt": 25,
        "keywords": ["gillette", "foxborough", "boston stadium"],
    },
    {
        "ciudad": "Miami Gardens, Florida", "pais": "USA", "alt": 3,
        "keywords": ["hard rock", "miami stadium", "miami gardens"],
    },
    {
        "ciudad": "Arlington, Texas", "pais": "USA", "alt": 188,
        "keywords": ["at&t stadium", "att stadium", "dallas stadium", "arlington"],
    },
    {
        "ciudad": "Kansas City, Missouri", "pais": "USA", "alt": 325,
        "keywords": ["arrowhead", "kansas city"],
    },
    {
        "ciudad": "Houston, Texas", "pais": "USA", "alt": 12,
        "keywords": ["nrg stadium", "nrg", "houston stadium"],
    },
    {
        "ciudad": "Atlanta, Georgia", "pais": "USA", "alt": 320,
        "keywords": ["mercedes-benz", "mercedes benz", "atlanta stadium", "georgia dome"],
    },
    {
        "ciudad": "Vancouver, British Columbia", "pais": "CAN", "alt": 4,
        "keywords": ["bc place", "bc place stadium", "vancouver"],
    },
    {
        "ciudad": "Toronto, Ontario", "pais": "CAN", "alt": 76,
        "keywords": ["bmo field", "bmo", "toronto"],
    },
]

# =====================================================
# HELPERS
# =====================================================

def guardar_json(nombre, data):
    ruta = os.path.join(DATA_DIR, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {nombre} generado")


def stat(stats, name, default=0):
    for s in stats:
        if s.get("name") == name:
            return s.get("value", default)
    return default


def get_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ✗ Error GET {url}: {e}")
        return {}


def altitud_seleccion(abrev):
    """Devuelve la altitud base conocida para una selección."""
    return ALTITUD_BASE.get(abrev.upper(), 0)


def info_sede(nombre_estadio):
    """
    Busca la sede del Mundial que mejor coincida con el nombre que devuelve ESPN.
    Usa keywords para tolerar nombres comerciales, alias FIFA y variantes.
    """
    nombre_lower = nombre_estadio.lower().strip()
    for sede in SEDES_MUNDIAL:
        for kw in sede["keywords"]:
            if kw in nombre_lower or nombre_lower in kw:
                return {"ciudad": sede["ciudad"], "pais": sede["pais"], "alt": sede["alt"]}
    # Sede no reconocida — devuelve el nombre tal como viene para no perder info
    print(f"  ⚠ Sede no reconocida: '{nombre_estadio}'")
    return {"ciudad": nombre_estadio, "pais": "?", "alt": 0}


def contexto_altitud(alt):
    if alt < 500:
        return f"Sede a baja altitud ({alt}m)"
    elif alt < 1200:
        return f"Sede en altura moderada ({alt}m)"
    elif alt < 2000:
        return f"Sede en altura considerable ({alt}m)"
    else:
        return f"Sede en gran altitud ({alt}m)"


# =====================================================
# GRUPOS
# =====================================================

def obtener_grupos():
    url = f"{BASE_ESPN_V2}/fifa.world/standings"
    data = get_json(url)

    grupos = []
    for group in data.get("children", []):
        grupo_obj = {
            "grupo": group.get("name", ""),
            "equipos": []
        }

        entries = group.get("standings", {}).get("entries", [])
        for entry in entries:
            team = entry.get("team", {})
            stats = entry.get("stats", [])

            partidos      = stat(stats, "gamesPlayed")
            goles_favor   = stat(stats, "pointsFor")
            goles_contra  = stat(stats, "pointsAgainst")

            equipo = {
                "posicion":         stat(stats, "rank"),
                "equipo":           team.get("displayName", ""),
                "abreviacion":      team.get("abbreviation", ""),
                "escudo":           (team.get("logos", [{}])[0].get("href", "")
                                     if team.get("logos") else ""),
                "partidos":         partidos,
                "ganados":          stat(stats, "wins"),
                "empatados":        stat(stats, "ties"),
                "perdidos":         stat(stats, "losses"),
                "goles_favor":      goles_favor,
                "goles_contra":     goles_contra,
                "diferencia_goles": stat(stats, "pointDifferential"),
                "puntos":           stat(stats, "points"),

                # Campos extendidos (se rellenan con obtener_selecciones)
                "forma_ponderada":      0,
                "forma_liga":           0,
                "ultimos_5_liga":       [],
                "imbatido_streak":      0,
                "forma_liga_local":     0,
                "ultimos_5_liga_local": [],
                "liga_local_slug":      "",

                "competencias": {
                    "fifa.world": {
                        "partidos":              partidos,
                        "ganados":               stat(stats, "wins"),
                        "empatados":             stat(stats, "ties"),
                        "perdidos":              stat(stats, "losses"),
                        "goles_favor":           goles_favor,
                        "goles_contra":          goles_contra,
                        "goles_favor_promedio":  round(goles_favor  / max(partidos, 1), 2),
                        "goles_contra_promedio": round(goles_contra / max(partidos, 1), 2),
                        "partidos_local":   0, "ganados_local":   0,
                        "empatados_local":  0, "perdidos_local":  0,
                        "win_rate_local":   0,
                        "partidos_visita":  0, "ganados_visita":  0,
                        "empatados_visita": 0, "perdidos_visita": 0,
                        "win_rate_visita":  0,
                        "ultimos_5":        [],
                        "imbatido_streak":  0,
                    }
                }
            }
            grupo_obj["equipos"].append(equipo)

        grupos.append(grupo_obj)

    guardar_json("grupos.json", grupos)
    return grupos


# =====================================================
# TABLA GENERAL
# =====================================================

def generar_tabla(grupos):
    tabla = []
    for grupo in grupos:
        for eq in grupo["equipos"]:
            tabla.append({
                "grupo":            grupo["grupo"],
                "posicion":         eq["posicion"],
                "equipo":           eq["equipo"],
                "abreviacion":      eq["abreviacion"],
                "escudo":           eq["escudo"],
                "puntos":           eq["puntos"],
                "diferencia_goles": eq["diferencia_goles"],
                "goles_favor":      eq["goles_favor"],
                "goles_contra":     eq["goles_contra"],
                "partidos":         eq["partidos"],
            })

    tabla.sort(
        key=lambda x: (x["puntos"], x["diferencia_goles"], x["goles_favor"]),
        reverse=True
    )
    guardar_json("tabla.json", tabla)


# =====================================================
# SELECCIONES
# =====================================================

def _calcular_forma(resultados):
    """
    Recibe lista de 'W'/'D'/'L' (más reciente al final o al inicio).
    Devuelve un float 0-1 (W=1, D=0.5, L=0).
    """
    if not resultados:
        return 0.0
    pesos = {"W": 1.0, "D": 0.5, "L": 0.0}
    vals  = [pesos.get(r, 0) for r in resultados]
    return round(sum(vals) / len(vals), 4)


def _imbatido_streak(resultados):
    """
    Recibe lista ordenada más-reciente-primero.
    Cuenta partidos consecutivos sin derrota desde el inicio.
    """
    streak = 0
    for r in resultados:
        if r in ("W", "D"):
            streak += 1
        else:
            break
    return streak


def _procesar_eventos_equipo(events, team_id):
    """
    Procesa todos los partidos del equipo (oficiales y amistosos juntos)
    y devuelve un dict con métricas globales + local/visita/neutro.
    """
    total   = {"P": 0, "G": 0, "E": 0, "L": 0, "GF": 0, "GC": 0}
    local_  = {"P": 0, "G": 0, "E": 0, "L": 0}
    visita_ = {"P": 0, "G": 0, "E": 0, "L": 0}
    neutro_ = {"P": 0, "G": 0, "E": 0, "L": 0}
    todos_res = []

    for ev in events:
        comp        = ev.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])

        my_side  = next((c for c in competitors if str(c.get("id","")) == str(team_id)), None)
        opp_side = next((c for c in competitors if str(c.get("id","")) != str(team_id)), None)
        if not my_side or not opp_side:
            continue

        gf = int(my_side.get("score",  0) or 0)
        gc = int(opp_side.get("score", 0) or 0)

        if gf > gc:    res = "W"
        elif gf == gc: res = "D"
        else:          res = "L"

        total["P"]  += 1
        total["GF"] += gf
        total["GC"] += gc
        if res == "W":   total["G"] += 1
        elif res == "D": total["E"] += 1
        else:            total["L"] += 1

        todos_res.insert(0, res)   # más reciente primero

        home_away = my_side.get("homeAway", "")
        if home_away == "home":
            bucket = local_
        elif home_away == "away":
            bucket = visita_
        else:
            bucket = neutro_

        bucket["P"] += 1
        if res == "W":   bucket["G"] += 1
        elif res == "D": bucket["E"] += 1
        else:            bucket["L"] += 1

    def win_rate(b):
        return round(b["G"] / max(b["P"], 1), 4)

    p = max(total["P"], 1)

    return {
        "partidos":          total["P"],
        "ganados":           total["G"],
        "empatados":         total["E"],
        "perdidos":          total["L"],
        "goles_favor":       round(total["GF"] / p, 3),
        "goles_contra":      round(total["GC"] / p, 3),
        "forma":             _calcular_forma(todos_res[:5]),
        "ultimos_5":         todos_res[:5],
        "partidos_local":    local_["P"],
        "ganados_local":     local_["G"],
        "empatados_local":   local_["E"],
        "perdidos_local":    local_["L"],
        "win_rate_local":    win_rate(local_),
        "partidos_visita":   visita_["P"],
        "ganados_visita":    visita_["G"],
        "empatados_visita":  visita_["E"],
        "perdidos_visita":   visita_["L"],
        "win_rate_visita":   win_rate(visita_),
        "win_rate_neutro":   win_rate(neutro_),
        "imbatido_streak":   _imbatido_streak(todos_res),
    }


def obtener_selecciones(grupos):
    """
    Construye selecciones.json con un objeto por equipo que participó
    en el Mundial, usando su historial reciente de la API de ESPN.
    ranking_fifa y puntos_fifa se dejan en 0 — no hay endpoint público
    disponible; se pueden rellenar manualmente si se necesitan.
    """

    # Reunir todos los equipos únicos de los grupos
    equipos_vistos = {}
    for grupo in grupos:
        for eq in grupo["equipos"]:
            abrev = eq["abreviacion"]
            if abrev not in equipos_vistos:
                equipos_vistos[abrev] = eq

    selecciones = {}

    for abrev, eq_base in equipos_vistos.items():
        nombre  = eq_base["equipo"]
        escudo  = eq_base["escudo"]

        print(f"  → {nombre} ({abrev})...")

        # Buscar ID de ESPN a través del endpoint de teams
        team_search_url = (
            f"https://site.api.espn.com/apis/site/v2/sports/soccer"
            f"/fifa.world/teams"
        )
        teams_data = get_json(team_search_url)
        id_espn = ""
        confederacion = ""
        for t in teams_data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
            t2 = t.get("team", {})
            if t2.get("abbreviation", "").upper() == abrev.upper():
                id_espn       = str(t2.get("id", ""))
                confederacion = t2.get("displayConference", "")
                break

        # Historial de partidos del equipo (últimas 2 temporadas, suficiente)
        metricas = {
            "partidos": 0, "ganados": 0, "empatados": 0, "perdidos": 0,
            "goles_favor": 0.0, "goles_contra": 0.0,
            "forma": 0.0, "ultimos_5": [],
            "partidos_local": 0, "ganados_local": 0,
            "empatados_local": 0, "perdidos_local": 0,
            "win_rate_local": 0.0,
            "partidos_visita": 0, "ganados_visita": 0,
            "empatados_visita": 0, "perdidos_visita": 0,
            "win_rate_visita": 0.0,
            "win_rate_neutro": 0.0,
            "imbatido_streak": 0,
        }

        if id_espn:
            all_events = []
            for year in [2026, 2025]:
                hist_url = (
                    f"https://site.api.espn.com/apis/site/v2/sports/soccer"
                    f"/fifa.world/teams/{id_espn}/schedule"
                    f"?season={year}&limit=50"
                )
                hist_data = get_json(hist_url)
                events = hist_data.get("events", [])
                all_events.extend(events)

            if all_events:
                metricas = _procesar_eventos_equipo(all_events, id_espn)

        ranking_info = RANKING_FIFA.get(abrev.upper(), (999, 0.0))

        slug = nombre.lower().replace(" ", "_")

        selecciones[slug] = {
            "nombre":        nombre,
            "escudo":        escudo,
            "id_espn":       id_espn,
            "confederacion": confederacion,
            "altitud_base":  altitud_seleccion(abrev),
            "ciudades_local": [],
            "ranking_fifa":  ranking_info[0],
            "puntos_fifa":   ranking_info[1],
            **metricas,
        }

    guardar_json("selecciones.json", selecciones)
    return selecciones


# =====================================================
# FIXTURE (HOY + MAÑANA)
# =====================================================

def obtener_fixture(selecciones_por_nombre=None):
    """
    Descarga los partidos de hoy y mañana.
    Enriquece cada partido con datos de altitud y contexto.
    """
    ahora = datetime.now(timezone.utc)
    fechas = [
        ahora.strftime("%Y%m%d"),
        (ahora + timedelta(days=1)).strftime("%Y%m%d"),
    ]

    # Índice rápido: nombre → slug de selección
    nombre_a_slug = {}
    if selecciones_por_nombre:
        for slug, data in selecciones_por_nombre.items():
            nombre_a_slug[data["nombre"].lower()] = slug

    partidos = []

    for fecha in fechas:
        url  = f"{BASE_ESPN}/scoreboard"
        data = get_json(url, params={"dates": fecha})

        for event in data.get("events", []):
            comp        = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            status      = comp.get("status", {}).get("type", {})

            local    = next((c for c in competitors if c.get("homeAway") == "home"), {})
            visitante= next((c for c in competitors if c.get("homeAway") == "away"), {})

            nombre_estadio = comp.get("venue", {}).get("fullName", "")
            sede_info      = info_sede(nombre_estadio)

            abrev_local     = local.get("team", {}).get("abbreviation", "")
            abrev_visitante = visitante.get("team", {}).get("abbreviation", "")
            id_local        = str(local.get("team", {}).get("id", ""))
            id_visitante    = str(visitante.get("team", {}).get("id", ""))

            alt_sede      = sede_info["alt"]
            alt_local     = altitud_seleccion(abrev_local)
            alt_visitante = altitud_seleccion(abrev_visitante)

            # Diferencia de altitud: cuánto MÁS alta es la sede vs su base habitual
            dif_local     = max(alt_sede - alt_local, 0)
            dif_visitante = max(alt_sede - alt_visitante, 0)

            nombre_local     = local.get("team",    {}).get("displayName", "")
            nombre_visitante = visitante.get("team",{}).get("displayName", "")

            partido = {
                "id":            event.get("id"),
                "fecha":         event.get("date"),
                "estado":        status.get("description", ""),
                "minuto":        comp.get("status", {}).get("displayClock", ""),
                "local":         nombre_local,
                "visitante":     nombre_visitante,
                "id_espn_local":     id_local,
                "id_espn_visitante": id_visitante,
                "estadio":       nombre_estadio,
                "ciudad_sede":   sede_info["ciudad"],
                "pais_sede":     sede_info["pais"],
                "altitud_sede":  alt_sede,
                "altitud_base_local":      alt_local,
                "altitud_base_visitante":  alt_visitante,
                "diferencia_altitud_local":      dif_local,
                "diferencia_altitud_visitante":  dif_visitante,
                "contexto_altitud": contexto_altitud(alt_sede),
            }

            # Si ya viene jugado, incluir marcador
            if status.get("completed", False) or status.get("name","") == "STATUS_FINAL":
                partido["goles_local"]    = int(local.get("score", 0) or 0)
                partido["goles_visitante"]= int(visitante.get("score", 0) or 0)

            partidos.append(partido)

    guardar_json("fixture.json", partidos)
    return partidos


# =====================================================
# MAIN
# =====================================================

def main():
    print("\n╔══════════════════════════════╗")
    print("║   Actualizando Mundial 2026  ║")
    print("╚══════════════════════════════╝\n")

    print("▶ Grupos y tabla...")
    grupos = obtener_grupos()
    generar_tabla(grupos)

    print("\n▶ Selecciones (puede tardar ~1 min)...")
    selecciones = obtener_selecciones(grupos)

    print("\n▶ Fixture (hoy + mañana)...")
    obtener_fixture(selecciones_por_nombre=selecciones)

    print("\n✓ Todo actualizado\n")


if __name__ == "__main__":
    main()
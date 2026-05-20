import requests
import json
import time
import os
import argparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer": "https://www.espn.com.mx/",
    "Origin": "https://www.espn.com.mx"
}

PESOS_FORMA = [0.35, 0.25, 0.20, 0.12, 0.08]

# ─────────────────────────────────────────────
# PESOS POR COMPETENCIA (para forma combinada)
# ─────────────────────────────────────────────
PESO_COMPETENCIA = {
    # Ligas regulares — peso completo
    "mex.1":                  1.0,
    "mex.2":                  1.0,
    "eng.1":                  1.0,
    "esp.1":                  1.0,
    "ger.1":                  1.0,
    "fra.1":                  1.0,
    "ita.1":                  1.0,
    "ned.1":                  1.0,
    "bel.1":                  1.0,
    "bra.1":                  1.0,
    "usa.1":                  1.0,
    "sco.1":                  1.0,
    "gre.1":                  1.0,
    "rus.1":                  1.0,
    "arg.1":                  1.0,
    "col.1":                  1.0,
    "chi.1":                  1.0,
    "uru.1":                  1.0,
    "ven.1":                  1.0,
    "ecu.1":                  1.0,
    "per.1":                  1.0,
    "usa.nwsl":               1.0,
    "mex.women":              1.0,
    # Torneos internacionales — peso reducido
    "conmebol.libertadores":  0.90,
    "conmebol.sudamericana":  0.80,
    "concacaf.champions":     0.70,
    "concacaf.w.champions":   0.70,
    "uefa.champions":         0.60,
    "uefa.europa":            0.55,
    "uefa.europa.conf":       0.50,
    "eng.fa":                 0.40,
    "esp.copa":               0.40,
    "ger.cup":                0.40,
    "fra.cup":                0.40,
    "mex.copa":               0.40,
}


# ─────────────────────────────────────────────
# LIGAS REGULARES
# ─────────────────────────────────────────────
LIGAS_CONFIG = {
    "mex.1": {
        "nombre":                  "Liga MX",
        "carpeta":                 "LIGA-MX",
        "copas":                   ["mex.1", "concacaf.champions"],
        "es_torneo_copa":          False,
        "liga_principal":          "mex.1",
        "tiene_apertura_clausura": True,
        "season_type_id":          "8",
    },
    "mex.2": {
        "nombre":                  "Liga de Expansión MX",
        "carpeta":                 "LIGA-MX-EXPANSION",
        "copas":                   ["mex.2"],
        "es_torneo_copa":          False,
        "liga_principal":          "mex.2",
        "tiene_apertura_clausura": True,
        "season_type_id":          "8",
    },
    "eng.1": {
        "nombre":                  "Premier League",
        "carpeta":                 "PREMIER-LEAGUE",
        "copas":                   ["eng.1", "uefa.champions", "eng.fa"],
        "es_torneo_copa":          False,
        "liga_principal":          "eng.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "esp.1": {
        "nombre":                  "La Liga",
        "carpeta":                 "LALIGA",
        "copas":                   ["esp.1", "uefa.champions", "esp.copa"],
        "es_torneo_copa":          False,
        "liga_principal":          "esp.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "ger.1": {
        "nombre":                  "Bundesliga",
        "carpeta":                 "BUNDESLIGA",
        "copas":                   ["ger.1", "uefa.champions"],
        "es_torneo_copa":          False,
        "liga_principal":          "ger.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "fra.1": {
        "nombre":                  "Ligue 1",
        "carpeta":                 "LIGUE-1",
        "copas":                   ["fra.1", "uefa.champions"],
        "es_torneo_copa":          False,
        "liga_principal":          "fra.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "ned.1": {
        "nombre":                  "Eredivisie",
        "carpeta":                 "EREDIVISIE",
        "copas":                   ["ned.1", "uefa.europa"],
        "es_torneo_copa":          False,
        "liga_principal":          "ned.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "bel.1": {
        "nombre":                  "Belgian Pro League",
        "carpeta":                 "BELGIAN-PRO-LEAGUE",
        "copas":                   ["bel.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "bel.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "bra.1": {
        "nombre":                  "Brasileirao Serie A",
        "carpeta":                 "BRASILEIRAO-SERIE-A",
        "copas":                   ["bra.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "bra.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "usa.1": {
        "nombre":                  "MLS",
        "carpeta":                 "MLS",
        "copas":                   ["usa.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "usa.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "sco.1": {
        "nombre":                  "Scottish Premiership",
        "carpeta":                 "SCOTTISH-PREMIERSHIP",
        "copas":                   ["sco.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "sco.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "gre.1": {
        "nombre":                  "Super League Grecia",
        "carpeta":                 "SUPERLIGA-GRECIA",
        "copas":                   ["gre.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "gre.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "rus.1": {
        "nombre":                  "Liga Premier Rusia",
        "carpeta":                 "LIGAPREMIER-RUSIA",
        "copas":                   ["rus.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "rus.1",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "uefa.europa": {
        "nombre":                  "UEFA Europa League",
        "carpeta":                 "EUROPA-LEAGUE",
        # El scraper busca partidos SOLO de este torneo.
        # La forma de liga local se agrega como campo extra (forma_liga_local).
        "copas":                   ["uefa.europa"],
        "es_torneo_copa":          True,
        "liga_principal":          "uefa.europa",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        # Slugs de ligas locales de los equipos participantes
        # El scraper las consulta para obtener forma_liga_local
        "ligas_locales":           ["eng.1", "esp.1", "ger.1", "fra.1", "ita.1",
                                    "ned.1", "por.1", "bel.1", "sco.1", "gre.1"],
    },
    "conmebol.libertadores": {
        "nombre":                  "CONMEBOL Libertadores",
        "carpeta":                 "LIBERTADORES",
        "copas":                   ["conmebol.libertadores"],
        "es_torneo_copa":          True,
        "liga_principal":          "conmebol.libertadores",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        "ligas_locales":           ["bra.1", "arg.1", "col.1", "chi.1",
                                    "uru.1", "ven.1", "ecu.1", "per.1", "mex.1"],
    },
    "conmebol.sudamericana": {
        "nombre":                  "CONMEBOL Sudamericana",
        "carpeta":                 "SUDAMERICANA",
        "copas":                   ["conmebol.sudamericana"],
        "es_torneo_copa":          True,
        "liga_principal":          "conmebol.sudamericana",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        "ligas_locales":           ["bra.1", "arg.1", "col.1", "chi.1",
                                    "uru.1", "ven.1", "ecu.1", "per.1"],
    },
    "concacaf.w.champions": {
        "nombre":                  "Concacaf W Champions Cup",
        "carpeta":                 "CONCACAF-W-CHAMPIONS",
        "copas":                   ["concacaf.w.champions"],
        "es_torneo_copa":          True,
        "liga_principal":          "concacaf.w.champions",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        "ligas_locales":           ["usa.nwsl", "mex.women"],
    },
}


# ─────────────────────────────────────────────
# DIAGNÓSTICO
# ─────────────────────────────────────────────

def diagnosticar(liga_slug):
    standings_url = f"https://site.api.espn.com/apis/v2/sports/soccer/{liga_slug}/standings"
    teams_url     = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/teams"
    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/scoreboard"

    print("🔎 DIAGNÓSTICO DE ENDPOINTS\n")
    urls = {
        "standings":  standings_url,
        "teams":      teams_url,
        "scoreboard": scoreboard_url,
    }
    resultados = {}
    for nombre, url in urls.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            size = len(r.text)
            ok = r.status_code == 200 and size > 100
            print(f"  {'✅' if ok else '❌'} {nombre}: HTTP {r.status_code} | {size} chars")
            if ok:
                resultados[nombre] = r.json()
            else:
                print(f"     Respuesta: {r.text[:120]}")
                resultados[nombre] = None
        except Exception as e:
            print(f"  ❌ {nombre}: ERROR - {e}")
            resultados[nombre] = None
    print()
    return resultados


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_stat(stats, name):
    for s in stats:
        if s.get("name") == name:
            return s.get("value", 0)
    return 0


def normalizar(nombre):
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


def calcular_forma_ponderada(partidos):
    """
    Forma ponderada por recencia Y por peso de competencia.
    Toma los 5 más recientes de la lista (ya debe venir ordenada desc por fecha).
    """
    ultimos = partidos[:5]
    while len(ultimos) < 5:
        ultimos.append(None)
    score = 0.0
    for i, p in enumerate(ultimos):
        if p is None:
            continue
        pts       = 1.0 if p["resultado"] == "W" else (0.5 if p["resultado"] == "D" else 0.0)
        peso_pos  = PESOS_FORMA[i]
        peso_comp = PESO_COMPETENCIA.get(p["liga"], 0.5)
        score    += pts * peso_pos * peso_comp
    return round(score, 4)


def calcular_imbatido_streak(resultados):
    streak = 0
    for r in resultados:
        if r in ("W", "D"):
            streak += 1
        else:
            break
    return streak


# ─────────────────────────────────────────────
# PARSEAR STANDINGS
# ─────────────────────────────────────────────

def parsear_standings(data):
    """Intenta distintas estructuras que ESPN puede devolver."""
    tabla        = []
    equipos_dict = {}

    entries = None
    try:
        entries = data["children"][0]["standings"]["entries"]
        print("  Estructura: children[0].standings.entries ✅")
    except (KeyError, IndexError):
        pass

    if not entries:
        try:
            entries = data["standings"]["entries"]
            print("  Estructura: standings.entries ✅")
        except KeyError:
            pass

    if not entries:
        try:
            entries = data["entries"]
            print("  Estructura: entries ✅")
        except KeyError:
            pass

    if not entries:
        print("  ❌ No se encontraron entries. Keys:", list(data.keys()))
        return tabla, equipos_dict

    for entry in entries:
        team    = entry["team"]
        stats   = entry["stats"]
        team_id = team["id"]

        ganados     = int(get_stat(stats, "wins"))
        empatados   = int(get_stat(stats, "ties"))
        perdidos    = int(get_stat(stats, "losses"))
        partidos    = int(get_stat(stats, "gamesPlayed"))
        puntos      = int(get_stat(stats, "points"))
        gf          = int(get_stat(stats, "pointsFor"))
        gc          = int(get_stat(stats, "pointsAgainst"))
        posicion    = int(get_stat(stats, "rank"))
        rank_change = int(get_stat(stats, "rankChange"))
        logo_url    = team.get("logos", [{}])[0].get("href", "")

        tabla.append({
            "posicion":         posicion,
            "equipo":           team["displayName"],
            "id":               team_id,
            "partidos":         partidos,
            "ganados":          ganados,
            "empatados":        empatados,
            "perdidos":         perdidos,
            "goles_favor":      gf,
            "goles_contra":     gc,
            "diferencia_goles": gf - gc,
            "puntos":           puntos,
        })

        equipos_dict[team_id] = {
            "nombre":               team["displayName"],
            "abreviacion":          team.get("abbreviation", ""),
            "escudo":               logo_url,
            # Posición refleja la tabla del torneo/liga scrapeado
            "posicion":             posicion,
            "posicion_anterior":    posicion - rank_change,
            "tendencia_posicion":   rank_change,
            "partidos":             partidos,
            "ganados":              ganados,
            "empatados":            empatados,
            "perdidos":             perdidos,
            "puntos":               puntos,
            "goles_favor":          gf,
            "goles_contra":         gc,
            "goles_diff":           gf - gc,
            "goles_favor_promedio":  round(gf / partidos, 3) if partidos else 0,
            "goles_contra_promedio": round(gc / partidos, 3) if partidos else 0,
            # Se llena en el paso de partidos
            "competencias":         {},
            "forma_ponderada":      0.0,
            "forma_liga":           0.0,
            "ultimos_5_liga":       [],
            "imbatido_streak":      0,
            # Solo para torneos copa — se llena después
            "forma_liga_local":     None,
            "ultimos_5_liga_local": None,
            "liga_local_slug":      None,
        }

    tabla.sort(key=lambda x: x["posicion"])
    return tabla, equipos_dict


# ─────────────────────────────────────────────
# FALLBACK: EQUIPOS DESDE MÚLTIPLES FUENTES
# Para torneos copa donde standings no existe
# o viene dividido por grupos (children[])
# ─────────────────────────────────────────────

def _extraer_equipo_info(team):
    """Extrae los campos básicos de un objeto team de ESPN."""
    logos = team.get("logos", [])
    escudo = logos[0].get("href", "") if logos else team.get("logo", "")
    return {
        "nombre":      team.get("displayName", ""),
        "abreviacion": team.get("abbreviation", ""),
        "escudo":      escudo,
    }


def obtener_equipos_desde_standings_grupos(data):
    """
    Libertadores/Sudamericana tienen standings divididos por grupos:
    data['children'] = [ {group_A}, {group_B}, ... ]
    Itera todos los grupos y extrae los equipos de cada uno.
    """
    equipos = {}
    children = data.get("children", [])
    if not children:
        return equipos

    print(f"  → Standings con {len(children)} grupo(s) detectados")
    for grupo in children:
        entries = (
            grupo.get("standings", {}).get("entries", [])
            or grupo.get("entries", [])
        )
        for entry in entries:
            team    = entry.get("team", {})
            stats   = entry.get("stats", [])
            team_id = team.get("id")
            if not team_id or team_id in equipos:
                continue

            ganados   = int(get_stat(stats, "wins"))
            empatados = int(get_stat(stats, "ties"))
            perdidos  = int(get_stat(stats, "losses"))
            partidos  = int(get_stat(stats, "gamesPlayed"))
            puntos    = int(get_stat(stats, "points"))
            gf        = int(get_stat(stats, "pointsFor"))
            gc        = int(get_stat(stats, "pointsAgainst"))
            # En grupos no hay rank global, usamos posición dentro del grupo
            posicion  = int(get_stat(stats, "rank")) or 9
            logos     = team.get("logos", [])
            escudo    = logos[0].get("href", "") if logos else ""

            equipos[team_id] = {
                "nombre":               team.get("displayName", ""),
                "abreviacion":          team.get("abbreviation", ""),
                "escudo":               escudo,
                "posicion":             posicion,
                "posicion_anterior":    posicion,
                "tendencia_posicion":   0,
                "partidos":             partidos,
                "ganados":              ganados,
                "empatados":            empatados,
                "perdidos":             perdidos,
                "puntos":               puntos,
                "goles_favor":          gf,
                "goles_contra":         gc,
                "goles_diff":           gf - gc,
                "goles_favor_promedio":  round(gf / partidos, 3) if partidos else 0,
                "goles_contra_promedio": round(gc / partidos, 3) if partidos else 0,
                "competencias":         {},
                "forma_ponderada":      0.0,
                "forma_liga":           0.0,
                "ultimos_5_liga":       [],
                "imbatido_streak":      0,
                "forma_liga_local":     None,
                "ultimos_5_liga_local": None,
                "liga_local_slug":      None,
            }

    print(f"  → {len(equipos)} equipos extraídos de grupos")
    return equipos


def obtener_equipos_desde_teams(liga_slug):
    """
    Intenta el endpoint /teams para obtener todos los participantes.
    Devuelve dict {team_id: info_basica}.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/teams"
    equipos = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200 or len(r.text) < 100:
            return equipos
        data = r.json()
        for sport in data.get("sports", []):
            for league in sport.get("leagues", []):
                for t in league.get("teams", []):
                    team    = t.get("team", {})
                    team_id = team.get("id")
                    if team_id and team_id not in equipos:
                        equipos[team_id] = _extraer_equipo_info(team)
        print(f"  → {len(equipos)} equipos desde /teams")
    except Exception as e:
        print(f"  ⚠️  Teams endpoint error: {e}")
    return equipos


def obtener_equipos_desde_scoreboard(liga_slug, semanas=8):
    """
    Itera el scoreboard por varias fechas para capturar TODOS los equipos
    que han jugado en el torneo, no solo los de la jornada actual.
    Devuelve dict {team_id: info_basica}.
    """
    from datetime import datetime, timedelta

    equipos  = {}
    hoy      = datetime.utcnow()

    # Genera fechas: desde 'semanas' semanas atrás hasta hoy, de 7 en 7 días
    fechas = []
    for i in range(semanas):
        fecha = hoy - timedelta(weeks=i)
        fechas.append(fecha.strftime("%Y%m%d"))

    for fecha_str in fechas:
        url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer"
               f"/{liga_slug}/scoreboard?dates={fecha_str}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                continue
            data = r.json()
            for evento in data.get("events", []):
                for comp in evento.get("competitions", []):
                    for competitor in comp.get("competitors", []):
                        team    = competitor.get("team", {})
                        team_id = team.get("id")
                        if team_id and team_id not in equipos:
                            equipos[team_id] = _extraer_equipo_info(team)
            time.sleep(0.2)
        except Exception:
            continue

    print(f"  → {len(equipos)} equipos desde scoreboard ({semanas} semanas)")
    return equipos


def obtener_equipos_copa_cascada(liga_slug, standings_data):
    """
    Estrategia en cascada para torneos copa:
    1. Standings por grupos (children[]) — el más completo si existe
    2. Endpoint /teams
    3. Scoreboard multi-fecha
    Devuelve dict {team_id: equipo_dict} listo para usar.
    """
    # ── Estrategia 1: standings con grupos ──────────────
    equipos = obtener_equipos_desde_standings_grupos(standings_data or {})
    if len(equipos) >= 4:
        print(f"  ✅ Equipos obtenidos desde standings por grupos: {len(equipos)}")
        return equipos

    # ── Estrategia 2: endpoint /teams ───────────────────
    print("  ⚠️  Grupos insuficientes — intentando /teams...")
    equipos_teams = obtener_equipos_desde_teams(liga_slug)
    if len(equipos_teams) >= 4:
        print(f"  ✅ Equipos obtenidos desde /teams: {len(equipos_teams)}")
        # Convertir info básica a estructura completa
        return {
            tid: construir_equipo_copa(tid, info)
            for tid, info in equipos_teams.items()
        }

    # ── Estrategia 3: scoreboard multi-fecha ────────────
    print("  ⚠️  /teams insuficiente — usando scoreboard multi-fecha...")
    equipos_sb = obtener_equipos_desde_scoreboard(liga_slug, semanas=10)
    if equipos_sb:
        print(f"  ✅ Equipos obtenidos desde scoreboard: {len(equipos_sb)}")
        return {
            tid: construir_equipo_copa(tid, info)
            for tid, info in equipos_sb.items()
        }

    print("  ❌ No se pudieron obtener equipos por ninguna vía.")
    return {}


def construir_equipo_copa(team_id, info):
    """
    Construye el dict base de un equipo para torneos copa
    cuando no hay standings (posición neutra).
    """
    return {
        "nombre":               info["nombre"],
        "abreviacion":          info["abreviacion"],
        "escudo":               info["escudo"],
        "posicion":             9,   # neutro — no hay tabla lineal
        "posicion_anterior":    9,
        "tendencia_posicion":   0,
        "partidos":             0,
        "ganados":              0,
        "empatados":            0,
        "perdidos":             0,
        "puntos":               0,
        "goles_favor":          0,
        "goles_contra":         0,
        "goles_diff":           0,
        "goles_favor_promedio":  0.0,
        "goles_contra_promedio": 0.0,
        "competencias":         {},
        "forma_ponderada":      0.0,
        "forma_liga":           0.0,
        "ultimos_5_liga":       [],
        "imbatido_streak":      0,
        "forma_liga_local":     None,
        "ultimos_5_liga_local": None,
        "liga_local_slug":      None,
    }


# ─────────────────────────────────────────────
# PARTIDOS POR EQUIPO
# ─────────────────────────────────────────────

def obtener_partidos_equipo(team_id, copas):
    """
    Descarga el schedule del equipo para cada competencia en `copas`.
    Devuelve lista de partidos ordenada por fecha desc, sin duplicados.
    """
    todos_partidos = []
    fechas_vistas  = set()

    for liga in copas:
        url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer"
               f"/{liga}/teams/{team_id}/schedule")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                continue
            data = r.json()
        except Exception:
            continue

        for evento in data.get("events", []):
            comp = evento.get("competitions", [{}])[0]
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                continue

            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            mi_equipo = next((c for c in competitors if str(c["id"]) == str(team_id)), None)
            rival     = next((c for c in competitors if str(c["id"]) != str(team_id)), None)
            if not mi_equipo or not rival:
                continue

            fecha = evento.get("date")
            if fecha in fechas_vistas:
                continue
            fechas_vistas.add(fecha)

            gane   = mi_equipo.get("winner", False)
            empate = not gane and not rival.get("winner", False)

            try:
                mis_goles   = int(float(mi_equipo.get("score", {}).get("displayValue", 0) or 0))
                goles_rival = int(float(rival.get("score",    {}).get("displayValue", 0) or 0))
            except Exception:
                mis_goles = goles_rival = 0

            todos_partidos.append({
                "fecha":        fecha,
                "liga":         liga,
                "es_local":     mi_equipo.get("homeAway") == "home",
                "resultado":    "W" if gane else ("D" if empate else "L"),
                "goles_favor":  mis_goles,
                "goles_contra": goles_rival,
            })

    todos_partidos.sort(key=lambda x: x["fecha"], reverse=True)
    return todos_partidos


# ─────────────────────────────────────────────
# STATS POR COMPETENCIA
# ─────────────────────────────────────────────

def calcular_stats_competencia(partidos):
    """Calcula todas las métricas para un subconjunto de partidos."""
    if not partidos:
        return {}

    locales = [p for p in partidos if p["es_local"]]
    visitas = [p for p in partidos if not p["es_local"]]

    def w(lst): return sum(1 for p in lst if p["resultado"] == "W")
    def d(lst): return sum(1 for p in lst if p["resultado"] == "D")
    def l(lst): return sum(1 for p in lst if p["resultado"] == "L")

    pl       = len(locales)
    pv       = len(visitas)
    total    = len(partidos)
    gf_total = sum(p["goles_favor"]  for p in partidos)
    gc_total = sum(p["goles_contra"] for p in partidos)
    resultados = [p["resultado"] for p in partidos]

    return {
        "partidos":               total,
        "ganados":                w(partidos),
        "empatados":              d(partidos),
        "perdidos":               l(partidos),
        "goles_favor":            gf_total,
        "goles_contra":           gc_total,
        "goles_favor_promedio":   round(gf_total / total, 3) if total else 0,
        "goles_contra_promedio":  round(gc_total / total, 3) if total else 0,
        "partidos_local":         pl,
        "ganados_local":          w(locales),
        "empatados_local":        d(locales),
        "perdidos_local":         l(locales),
        "win_rate_local":         round(w(locales) / pl, 3) if pl else 0,
        "partidos_visita":        pv,
        "ganados_visita":         w(visitas),
        "empatados_visita":       d(visitas),
        "perdidos_visita":        l(visitas),
        "win_rate_visita":        round(w(visitas) / pv, 3) if pv else 0,
        "ultimos_5":              resultados[:5],
        "imbatido_streak":        calcular_imbatido_streak(resultados),
    }


def calcular_stats(partidos, liga_principal):
    """
    Agrupa partidos por competencia y calcula stats para cada una.
    También calcula forma_ponderada combinada (todos los partidos).
    Devuelve (competencias_dict, forma_combinada).
    """
    if not partidos:
        return {}, 0.0

    por_competencia = {}
    for p in partidos:
        por_competencia.setdefault(p["liga"], []).append(p)

    competencias = {
        liga: calcular_stats_competencia(ps)
        for liga, ps in por_competencia.items()
    }

    forma_combinada = calcular_forma_ponderada(partidos)
    return competencias, forma_combinada


# ─────────────────────────────────────────────
# FORMA EN LIGA LOCAL (solo para torneos copa)
# ─────────────────────────────────────────────

def obtener_forma_liga_local(team_id, ligas_locales):
    """
    Para un equipo de torneo internacional, busca su forma reciente
    en la liga local consultando cada slug de liga_local hasta encontrar partidos.
    Devuelve (forma_ponderada, ultimos_5, liga_slug_encontrado).
    """
    for liga_slug in ligas_locales:
        try:
            partidos = obtener_partidos_equipo(team_id, [liga_slug])
            partidos_liga = [p for p in partidos if p["liga"] == liga_slug]
            if partidos_liga:
                forma  = calcular_forma_ponderada(partidos_liga)
                ul5    = [p["resultado"] for p in partidos_liga[:5]]
                return forma, ul5, liga_slug
        except Exception:
            continue
    return 0.0, [], None


# ─────────────────────────────────────────────
# GUARDADO
# ─────────────────────────────────────────────

def guardar_json(data, carpeta, filename):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, filename)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Guardado: {ruta}")


# ─────────────────────────────────────────────
# MAIN: SCRAPEAR LIGA O TORNEO
# ─────────────────────────────────────────────

def scrapear_liga(liga_slug):
    config = LIGAS_CONFIG.get(liga_slug)
    if not config:
        print(f"❌ Slug '{liga_slug}' no encontrado en LIGAS_CONFIG.")
        return

    es_copa       = config.get("es_torneo_copa", False)
    liga_principal = config["liga_principal"]
    copas          = config["copas"]
    ligas_locales  = config.get("ligas_locales", [])

    print(f"\n🚀 Scraper — {config['nombre']} ({liga_slug})")
    print(f"   Tipo: {'Torneo copa' if es_copa else 'Liga regular'}")
    print("=" * 50)

    datos = diagnosticar(liga_slug)

    # ── Obtener equipos ──────────────────────────────
    print("📊 Procesando equipos...")
    tabla        = []
    equipos_dict = {}

    if not es_copa:
        # Liga regular: standings lineal directo
        if datos.get("standings"):
            tabla, equipos_dict = parsear_standings(datos["standings"])
            print(f"  ✅ {len(equipos_dict)} equipos desde standings")
        else:
            print("  ❌ No hay standings para liga regular. Abortando.")
            return
    else:
        # Torneo copa: cascada de 3 estrategias
        print("  → Torneo copa: usando estrategia en cascada...")
        equipos_dict = obtener_equipos_copa_cascada(liga_slug, datos.get("standings"))

    if not equipos_dict:
        print("  ❌ No se encontraron equipos. Abortando.")
        return

    # ── Partidos por equipo ──────────────────────────
    print(f"\n📅 Obteniendo partidos ({', '.join(copas)})...")

    for team_id in list(equipos_dict.keys()):
        nombre = equipos_dict[team_id]["nombre"]
        print(f"  🔄 {nombre}...")

        try:
            # 1. Partidos en las competencias de este torneo/liga
            partidos = obtener_partidos_equipo(team_id, copas)
            competencias, forma_combinada = calcular_stats(partidos, liga_principal)

            eq = equipos_dict[team_id]
            eq["competencias"]    = competencias
            eq["forma_ponderada"] = forma_combinada

            # Acceso rápido a datos de la competencia principal
            stats_principal = competencias.get(liga_principal, {})
            eq["forma_liga"]      = calcular_forma_ponderada(
                [p for p in partidos if p["liga"] == liga_principal]
            )
            eq["ultimos_5_liga"]  = stats_principal.get("ultimos_5", [])
            eq["imbatido_streak"] = stats_principal.get("imbatido_streak", 0)

            # Actualizar totales desde stats de la competencia principal si standings
            # vino vacío (caso copa sin tabla)
            if es_copa and stats_principal:
                eq["partidos"]               = stats_principal.get("partidos", 0)
                eq["ganados"]                = stats_principal.get("ganados", 0)
                eq["empatados"]              = stats_principal.get("empatados", 0)
                eq["perdidos"]               = stats_principal.get("perdidos", 0)
                eq["goles_favor"]            = stats_principal.get("goles_favor", 0)
                eq["goles_contra"]           = stats_principal.get("goles_contra", 0)
                eq["goles_diff"]             = eq["goles_favor"] - eq["goles_contra"]
                eq["goles_favor_promedio"]   = stats_principal.get("goles_favor_promedio", 0.0)
                eq["goles_contra_promedio"]  = stats_principal.get("goles_contra_promedio", 0.0)

            # 2. Para torneos copa: forma en liga local (dato cruzado)
            if es_copa and ligas_locales:
                print(f"     → Buscando forma en liga local...")
                forma_local, ul5_local, liga_encontrada = obtener_forma_liga_local(
                    team_id, ligas_locales
                )
                eq["forma_liga_local"]     = forma_local
                eq["ultimos_5_liga_local"] = ul5_local
                eq["liga_local_slug"]      = liga_encontrada
                if liga_encontrada:
                    print(f"     → Liga local: {liga_encontrada} | Forma: {forma_local}")
                else:
                    print(f"     → Liga local no encontrada")

            time.sleep(0.3)

        except Exception as e:
            print(f"    ⚠️  Error procesando {nombre}: {e}")

    # ── Guardar tabla.json (solo si hay standings) ───
    if tabla:
        tabla_export = [{k: v for k, v in t.items() if k != "id"} for t in tabla]
        guardar_json(tabla_export, config["carpeta"], "tabla.json")

    # ── Guardar equipos.json ─────────────────────────
    equipos_final = {}
    for team_id, datos_equipo in equipos_dict.items():
        key = normalizar(datos_equipo["nombre"])
        equipos_final[key] = datos_equipo

    guardar_json(equipos_final, config["carpeta"], "equipos.json")

    # ── Resumen ──────────────────────────────────────
    print(f"\n📋 RESUMEN — {config['nombre']}")
    print(f"   Equipos scrapeados: {len(equipos_final)}")
    print(f"   Carpeta: {config['carpeta']}/")
    if tabla:
        print(f"\n🏆 Top 5:")
        for t in tabla[:5]:
            print(f"   {t['posicion']}. {t['equipo']} — {t['puntos']} pts")
    print()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scraper ESPN — Ligas y torneos, una carpeta por competencia"
    )
    parser.add_argument(
        "--liga",
        type=str,
        help=(
            "Slug de la liga o torneo. Ejemplos:\n"
            "  python scrapper.py --liga mex.1\n"
            "  python scrapper.py --liga conmebol.libertadores\n"
            "  python scrapper.py --liga all\n"
            "  python scrapper.py --liga ligas   (solo ligas regulares)\n"
            "  python scrapper.py --liga torneos (solo torneos copa)"
        )
    )
    args = parser.parse_args()

    if not args.liga:
        print("Uso:")
        print("  python scrapper.py --liga mex.1")
        print("  python scrapper.py --liga conmebol.libertadores")
        print("  python scrapper.py --liga all")
        print("  python scrapper.py --liga ligas")
        print("  python scrapper.py --liga torneos")
        print("\nLigas y torneos disponibles:")
        print("\n  LIGAS REGULARES:")
        for slug, cfg in LIGAS_CONFIG.items():
            if not cfg.get("es_torneo_copa"):
                print(f"    {slug:<30} {cfg['nombre']}")
        print("\n  TORNEOS:")
        for slug, cfg in LIGAS_CONFIG.items():
            if cfg.get("es_torneo_copa"):
                print(f"    {slug:<30} {cfg['nombre']}")

    elif args.liga == "all":
        for slug in LIGAS_CONFIG:
            scrapear_liga(slug)
            time.sleep(2)

    elif args.liga == "ligas":
        slugs = [s for s, c in LIGAS_CONFIG.items() if not c.get("es_torneo_copa")]
        for slug in slugs:
            scrapear_liga(slug)
            time.sleep(2)

    elif args.liga == "torneos":
        slugs = [s for s, c in LIGAS_CONFIG.items() if c.get("es_torneo_copa")]
        for slug in slugs:
            scrapear_liga(slug)
            time.sleep(2)

    else:
        scrapear_liga(args.liga)
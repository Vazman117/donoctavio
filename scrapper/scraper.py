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

# Peso por competencia para forma ponderada combinada
PESO_COMPETENCIA = {
    "mex.1":              1.0,
    "mex.2":              1.0,
    "eng.1":              1.0,
    "esp.1":              1.0,
    "ger.1":              1.0,
    "fra.1":              1.0,
    "ita.1":              1.0,
    "ned.1":              1.0,
    "bel.1":              1.0,
    "bra.1":              1.0,
    "usa.1":              1.0,
    "sco.1":              1.0,
    "gre.1":              1.0,
    "rus.1":              1.0,
    "concacaf.champions": 0.6,
    "uefa.champions":     0.6,
    "uefa.europa":        0.5,
    "eng.fa":             0.4,
    "esp.copa":           0.4,
}

# =============================
# CONFIG DE LIGAS
# =============================

LIGAS_CONFIG = {
    "mex.1": {
        "nombre":                  "Liga MX",
        "carpeta":                 "LIGA-MX",
        "copas":                   ["mex.1", "concacaf.champions"],
        "tiene_apertura_clausura": True,
        "season_type_id":          "8",
    },
    "mex.2": {
        "nombre":                  "Liga de Expansión MX",
        "carpeta":                 "LIGA-MX-EXPANSION",
        "copas":                   ["mex.2"],
        "tiene_apertura_clausura": True,
        "season_type_id":          "8",
    },
    "eng.1": {
        "nombre":                  "Premier League",
        "carpeta":                 "PREMIER-LEAGUE",
        "copas":                   ["eng.1", "uefa.champions", "eng.fa"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "esp.1": {
        "nombre":                  "La Liga",
        "carpeta":                 "LALIGA",
        "copas":                   ["esp.1", "uefa.champions", "esp.copa"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "ger.1": {
        "nombre":                  "Bundesliga",
        "carpeta":                 "BUNDESLIGA",
        "copas":                   ["ger.1", "uefa.champions"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "fra.1": {
        "nombre":                  "Ligue 1",
        "carpeta":                 "LIGUE-1",
        "copas":                   ["fra.1", "uefa.champions"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "ned.1": {
        "nombre":                  "Eredivisie",
        "carpeta":                 "EREDIVISIE",
        "copas":                   ["ned.1", "uefa.europa"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "bel.1": {
        "nombre":                  "Belgian Pro League",
        "carpeta":                 "BELGIAN-PRO-LEAGUE",
        "copas":                   ["bel.1"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "bra.1": {
        "nombre":                  "Brasileirao Serie A",
        "carpeta":                 "BRASILEIRAO-SERIE-A",
        "copas":                   ["bra.1"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "usa.1": {
        "nombre":                  "MLS",
        "carpeta":                 "MLS",
        "copas":                   ["usa.1"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "sco.1": {
        "nombre":                  "Scottish Premiership",
        "carpeta":                 "SCOTTISH-PREMIERSHIP",
        "copas":                   ["sco.1"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "gre.1": {
        "nombre":                  "Super League Grecia",
        "carpeta":                 "SUPERLIGA-GRECIA",
        "copas":                   ["gre.1"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
    "rus.1": {
        "nombre":                  "Liga Premier Rusia",
        "carpeta":                 "LIGAPREMIER-RUSIA",
        "copas":                   ["rus.1"],
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
    },
}


# =============================
# DIAGNOSTICO
# =============================

def diagnosticar(liga_slug):
    standings_url = f"https://site.api.espn.com/apis/v2/sports/soccer/{liga_slug}/standings"
    teams_url     = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/teams"
    schedule_url  = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/teams/219/schedule"

    print("🔎 DIAGNOSTICO DE ENDPOINTS\n")
    urls = {
        "standings": standings_url,
        "teams":     teams_url,
        "schedule":  schedule_url,
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


# =============================
# HELPERS
# =============================

def get_stat(stats, name):
    for s in stats:
        if s.get("name") == name:
            return s.get("value", 0)
    return 0


def calcular_forma_ponderada(partidos):
    """Forma ponderada por recencia Y por peso de competencia"""
    ultimos = partidos[:5]
    while len(ultimos) < 5:
        ultimos.append(None)
    score = 0
    for i, p in enumerate(ultimos):
        if p is None:
            continue
        pts = 1.0 if p["resultado"] == "W" else (0.5 if p["resultado"] == "D" else 0.0)
        peso_pos  = PESOS_FORMA[i]
        peso_comp = PESO_COMPETENCIA.get(p["liga"], 0.5)
        score += pts * peso_pos * peso_comp
    return round(score, 4)


def calcular_imbatido_streak(resultados):
    streak = 0
    for r in resultados:
        if r in ("W", "D"):
            streak += 1
        else:
            break
    return streak


# =============================
# PARSEAR STANDINGS
# =============================

def parsear_standings(data):
    """Intenta distintas estructuras que ESPN puede devolver"""
    tabla = []
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
        print("  ❌ No se encontraron entries. Keys disponibles:", list(data.keys()))
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

        logo_url = team.get("logos", [{}])[0].get("href", "")

        fila = {
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
            "puntos":           puntos
        }
        tabla.append(fila)

        equipos_dict[team_id] = {
            "nombre":                  team["displayName"],
            "abreviacion":             team.get("abbreviation", ""),
            "escudo":                  logo_url,
            "posicion":                posicion,
            "posicion_anterior":       posicion - rank_change,
            "tendencia_posicion":      rank_change,
            "partidos":                partidos,
            "ganados":                 ganados,
            "empatados":               empatados,
            "perdidos":                perdidos,
            "puntos":                  puntos,
            "goles_favor":             gf,
            "goles_contra":            gc,
            "goles_diff":              gf - gc,
            "goles_favor_promedio":    round(gf / partidos, 3) if partidos else 0,
            "goles_contra_promedio":   round(gc / partidos, 3) if partidos else 0,
            "competencias":            {},   # 👈 se llena después por competencia
        }

    tabla.sort(key=lambda x: x["posicion"])
    return tabla, equipos_dict


# =============================
# PARTIDOS Y STATS
# =============================

def obtener_partidos_equipo(team_id, copas):
    todos_partidos = []
    fechas_vistas  = set()

    for liga in copas:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/teams/{team_id}/schedule"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                continue
            data = r.json()
        except:
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
                goles_rival = int(float(rival.get("score", {}).get("displayValue", 0) or 0))
            except:
                mis_goles = goles_rival = 0

            todos_partidos.append({
                "fecha":        fecha,
                "liga":         liga,   # 👈 guardamos de qué competencia es
                "es_local":     mi_equipo.get("homeAway") == "home",
                "resultado":    "W" if gane else ("D" if empate else "L"),
                "goles_favor":  mis_goles,
                "goles_contra": goles_rival,
            })

    todos_partidos.sort(key=lambda x: x["fecha"], reverse=True)
    return todos_partidos


def calcular_stats_competencia(partidos):
    """Stats para una lista de partidos (de una sola competencia)"""
    if not partidos:
        return {}

    locales = [p for p in partidos if p["es_local"]]
    visitas = [p for p in partidos if not p["es_local"]]

    def w(lst): return sum(1 for p in lst if p["resultado"] == "W")
    def d(lst): return sum(1 for p in lst if p["resultado"] == "D")
    def l(lst): return sum(1 for p in lst if p["resultado"] == "L")

    pl = len(locales)
    pv = len(visitas)
    resultados = [p["resultado"] for p in partidos]

    gf_total = sum(p["goles_favor"]  for p in partidos)
    gc_total = sum(p["goles_contra"] for p in partidos)
    total    = len(partidos)

    return {
        "partidos":              total,
        "ganados":               w(partidos),
        "empatados":             d(partidos),
        "perdidos":              l(partidos),
        "goles_favor":           gf_total,
        "goles_contra":          gc_total,
        "goles_favor_promedio":  round(gf_total / total, 3) if total else 0,
        "goles_contra_promedio": round(gc_total / total, 3) if total else 0,

        "partidos_local":        pl,
        "ganados_local":         w(locales),
        "empatados_local":       d(locales),
        "perdidos_local":        l(locales),
        "win_rate_local":        round(w(locales) / pl, 3) if pl else 0,

        "partidos_visita":       pv,
        "ganados_visita":        w(visitas),
        "empatados_visita":      d(visitas),
        "perdidos_visita":       l(visitas),
        "win_rate_visita":       round(w(visitas) / pv, 3) if pv else 0,

        "ultimos_5":             resultados[:5],
        "imbatido_streak":       calcular_imbatido_streak(resultados),
    }


def calcular_stats(partidos, liga_principal):
    """
    Devuelve:
      - stats por competencia (dict)
      - forma_ponderada combinada (usando pesos por competencia)
    """
    if not partidos:
        return {}, 0.0

    # Agrupar por competencia
    por_competencia = {}
    for p in partidos:
        por_competencia.setdefault(p["liga"], []).append(p)

    competencias = {}
    for liga, ps in por_competencia.items():
        competencias[liga] = calcular_stats_competencia(ps)

    # Forma ponderada combinada (todos los partidos juntos, con peso por competencia)
    forma_combinada = calcular_forma_ponderada(partidos)

    return competencias, forma_combinada


# =============================
# GUARDADO
# =============================

def guardar_json(data, carpeta, filename):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, filename)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Guardado: {ruta}")


def normalizar(nombre):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


# =============================
# MAIN POR LIGA
# =============================

def scrapear_liga(liga_slug):
    config = LIGAS_CONFIG.get(liga_slug)
    if not config:
        print(f"❌ Liga '{liga_slug}' no encontrada en LIGAS_CONFIG.")
        return

    print(f"\n🚀 Scraper — {config['nombre']} ({liga_slug})\n" + "="*45)

    # Diagnóstico
    datos = diagnosticar(liga_slug)

    # Standings
    print("📊 Procesando standings...")
    if not datos.get("standings"):
        print("  ❌ Standings no disponible. Abortando.")
        print(f"\n  👉 Verifica: https://site.api.espn.com/apis/v2/sports/soccer/{liga_slug}/standings")
        return

    tabla, equipos_dict = parsear_standings(datos["standings"])
    print(f"  ✅ {len(equipos_dict)} equipos en tabla")

    # IDs de equipos
    print("\n🔍 Obteniendo IDs de equipos...")
    ids_equipos = {}
    if datos.get("teams"):
        for sport in datos["teams"].get("sports", []):
            for league in sport.get("leagues", []):
                for t in league.get("teams", []):
                    team = t["team"]
                    ids_equipos[team["id"]] = team["displayName"]
    print(f"  ✅ {len(ids_equipos)} IDs")

    # Partidos por equipo
    copas = config["copas"]
    print(f"\n📅 Obteniendo partidos ({', '.join(copas)})...")
    ids_a_procesar = list(equipos_dict.keys()) if equipos_dict else list(ids_equipos.keys())

    for team_id in ids_a_procesar:
        nombre = equipos_dict.get(team_id, {}).get("nombre") or ids_equipos.get(team_id, team_id)
        print(f"  🔄 {nombre}...")
        try:
            partidos = obtener_partidos_equipo(team_id, copas)
            competencias, forma_combinada = calcular_stats(partidos, liga_slug)

            if team_id in equipos_dict:
                equipos_dict[team_id]["competencias"]     = competencias
                equipos_dict[team_id]["forma_combinada"]  = forma_combinada
                # Forma y streak de la liga principal (para acceso rápido del modelo)
                stats_liga = competencias.get(liga_slug, {})
                equipos_dict[team_id]["forma_liga"]       = calcular_forma_ponderada(
                    [p for p in partidos if p["liga"] == liga_slug]
                ) if stats_liga else 0.0
                equipos_dict[team_id]["ultimos_5_liga"]   = stats_liga.get("ultimos_5", [])
                equipos_dict[team_id]["imbatido_streak"]  = stats_liga.get("imbatido_streak", 0)

            time.sleep(0.3)
        except Exception as e:
            print(f"    ⚠️  {e}")

    # Guardar tabla.json
    tabla_export = [{k: v for k, v in t.items() if k != "id"} for t in tabla]
    guardar_json(tabla_export, config["carpeta"], "tabla.json")

    # Guardar equipos.json
    equipos_final = {}
    for team_id, datos_equipo in equipos_dict.items():
        key = normalizar(datos_equipo["nombre"])
        equipos_final[key] = datos_equipo

    guardar_json(equipos_final, config["carpeta"], "equipos.json")

    print(f"\n📋 RESUMEN — {config['nombre']}")
    print(f"  Equipos: {len(equipos_final)}")
    print(f"\n🏆 Top 5:")
    for t in tabla_export[:5]:
        print(f"  {t['posicion']}. {t['equipo']} — {t['puntos']} pts")


# =============================
# ENTRY POINT
# =============================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper ESPN — Universal por liga")
    parser.add_argument(
        "--liga",
        type=str,
        help="Slug de la liga (ej: eng.1, mex.1). Usa 'all' para todas."
    )
    args = parser.parse_args()

    if not args.liga:
        print("Uso:")
        print("  python scrapper.py --liga mex.1")
        print("  python scrapper.py --liga eng.1")
        print("  python scrapper.py --liga all")
        print("\nLigas disponibles:")
        for slug, cfg in LIGAS_CONFIG.items():
            print(f"  {slug:<20} {cfg['nombre']}")

    elif args.liga == "all":
        for slug in LIGAS_CONFIG:
            scrapear_liga(slug)
            time.sleep(2)
    else:
        scrapear_liga(args.liga)
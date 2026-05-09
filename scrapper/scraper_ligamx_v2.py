import requests
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer": "https://www.espn.com.mx/",
    "Origin": "https://www.espn.com.mx"
}

# URLs confirmadas por el usuario
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings"
TEAMS_URL     = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/teams"
SCHEDULE_URL  = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/teams/{team_id}/schedule"
LIGAS_SCHEDULE = ["mex.1", "concacaf.champions"]

CLAUSURA_TYPE_ID = "8"
PESOS_FORMA = [0.35, 0.25, 0.20, 0.12, 0.08]


# =============================
# DIAGNOSTICO
# =============================

def diagnosticar():
    print("🔎 DIAGNOSTICO DE ENDPOINTS\n")
    urls = {
        "standings": STANDINGS_URL,
        "teams":     TEAMS_URL,
        "schedule":  SCHEDULE_URL.format(team_id=219),
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


def calcular_forma_ponderada(resultados):
    ultimos = resultados[:5]
    while len(ultimos) < 5:
        ultimos.append(None)
    score = 0
    for i, res in enumerate(ultimos):
        if res is None:
            continue
        pts = 1.0 if res == "W" else (0.5 if res == "D" else 0.0)
        score += pts * PESOS_FORMA[i]
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

    # Estructura A: children[0].standings.entries (doc 12)
    entries = None
    try:
        entries = data["children"][0]["standings"]["entries"]
        print("  Estructura: children[0].standings.entries ✅")
    except (KeyError, IndexError):
        pass

    # Estructura B: standings.entries directa
    if not entries:
        try:
            entries = data["standings"]["entries"]
            print("  Estructura: standings.entries ✅")
        except KeyError:
            pass

    # Estructura C: entries directa
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

        ganados   = int(get_stat(stats, "wins"))
        empatados = int(get_stat(stats, "ties"))
        perdidos  = int(get_stat(stats, "losses"))
        partidos  = int(get_stat(stats, "gamesPlayed"))
        puntos    = int(get_stat(stats, "points"))
        gf        = int(get_stat(stats, "pointsFor"))
        gc        = int(get_stat(stats, "pointsAgainst"))
        posicion  = int(get_stat(stats, "rank"))
        rank_change = int(get_stat(stats, "rankChange"))

        logo_url = team.get("logos", [{}])[0].get("href", "")

        fila = {
            "posicion": posicion,
            "equipo": team["displayName"],
            "id": team_id,
            "partidos": partidos,
            "ganados": ganados,
            "empatados": empatados,
            "perdidos": perdidos,
            "goles_favor": gf,
            "goles_contra": gc,
            "diferencia_goles": gf - gc,
            "puntos": puntos
        }
        tabla.append(fila)

        equipos_dict[team_id] = {
            "nombre": team["displayName"],
            "abreviacion": team.get("abbreviation", ""),
            "escudo": logo_url,
            "posicion": posicion,
            "posicion_anterior": posicion - rank_change,
            "tendencia_posicion": rank_change,
            "partidos": partidos,
            "ganados": ganados,
            "empatados": empatados,
            "perdidos": perdidos,
            "puntos": puntos,
            "goles_favor": gf,
            "goles_contra": gc,
            "goles_diff": gf - gc,
            "goles_favor_promedio": round(gf / partidos, 3) if partidos else 0,
            "goles_contra_promedio": round(gc / partidos, 3) if partidos else 0,
        }

    tabla.sort(key=lambda x: x["posicion"])
    return tabla, equipos_dict


# =============================
# PARTIDOS Y STATS
# =============================

def obtener_partidos_equipo(team_id):
    todos_partidos = []
    fechas_vistas = set()

    for liga in LIGAS_SCHEDULE:
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
                "es_local":     mi_equipo.get("homeAway") == "home",
                "resultado":    "W" if gane else ("D" if empate else "L"),
                "goles_favor":  mis_goles,
                "goles_contra": goles_rival,
            })

    todos_partidos.sort(key=lambda x: x["fecha"], reverse=True)
    return todos_partidos

def calcular_stats(partidos):
    if not partidos:
        return {}

    locales = [p for p in partidos if p["es_local"]]
    visitas = [p for p in partidos if not p["es_local"]]

    def w(lst): return sum(1 for p in lst if p["resultado"] == "W")
    def d(lst): return sum(1 for p in lst if p["resultado"] == "D")
    def l(lst): return sum(1 for p in lst if p["resultado"] == "L")

    pl, pv = len(locales), len(visitas)
    resultados = [p["resultado"] for p in partidos]

    return {
        "partidos_local":   pl,
        "ganados_local":    w(locales),
        "empatados_local":  d(locales),
        "perdidos_local":   l(locales),
        "win_rate_local":   round(w(locales) / pl, 3) if pl else 0,

        "partidos_visita":  pv,
        "ganados_visita":   w(visitas),
        "empatados_visita": d(visitas),
        "perdidos_visita":  l(visitas),
        "win_rate_visita":  round(w(visitas) / pv, 3) if pv else 0,

        "forma_ponderada":  calcular_forma_ponderada(resultados),
        "ultimos_5":        resultados[:5],
        "imbatido_streak":  calcular_imbatido_streak(resultados),
    }


# =============================
# MAIN
# =============================

def main():
    print("\n🚀 Scraper Liga MX Clausura 2026\n" + "="*40)

    # Diagnostico
    datos = diagnosticar()

    # Standings
    print("📊 Procesando standings...")
    if datos.get("standings"):
        tabla, equipos_dict = parsear_standings(datos["standings"])
    else:
        print("  ❌ Standings no disponible. Abortando.")
        print("\n  👉 Verifica que esta URL abre JSON en tu navegador:")
        print(f"     {STANDINGS_URL}")
        return

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
    print("\n📅 Obteniendo partidos (puede tardar ~30s)...")
    ids_a_procesar = list(equipos_dict.keys()) if equipos_dict else list(ids_equipos.keys())

    for team_id in ids_a_procesar:
        nombre = equipos_dict.get(team_id, {}).get("nombre") or ids_equipos.get(team_id, team_id)
        print(f"  🔄 {nombre}...")
        try:
            partidos = obtener_partidos_equipo(team_id)
            stats    = calcular_stats(partidos)
            if team_id in equipos_dict:
                equipos_dict[team_id].update(stats)
            time.sleep(0.3)
        except Exception as e:
            print(f"    ⚠️  {e}")

    # Guardar tabla.json
    tabla_export = [{k: v for k, v in t.items() if k != "id"} for t in tabla]
    with open("tabla.json", "w", encoding="utf-8") as f:
        json.dump(tabla_export, f, indent=2, ensure_ascii=False)
    print("\n✅ tabla.json guardado")

    # Guardar equipos.json
    def normalizar(nombre):
        reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
        n = nombre.lower().replace(" ", "")
        for a, b in reemplazos.items():
            n = n.replace(a, b)
        return n

    equipos_final = {}
    for team_id, datos_equipo in equipos_dict.items():
        key = normalizar(datos_equipo["nombre"])
        equipos_final[key] = datos_equipo

    with open("equipos.json", "w", encoding="utf-8") as f:
        json.dump(equipos_final, f, indent=2, ensure_ascii=False)
    print("✅ equipos.json guardado")

    print(f"\n📋 RESUMEN FINAL")
    print(f"  Equipos: {len(equipos_final)}")
    print(f"\n🏆 Top 5:")
    for t in tabla_export[:5]:
        print(f"  {t['posicion']}. {t['equipo']} — {t['puntos']} pts")


if __name__ == "__main__":
    main()

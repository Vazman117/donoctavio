"""
=============================================================
  MODELO DE PROBABILIDADES POR GRUPO — MUNDIAL 2026
  Don Octavio Web
=============================================================

MÉTRICA PRINCIPAL:
    prob_lider  →  % de veces que cada equipo queda 1° del grupo
                   Los 4 equipos de cada grupo suman exactamente 100%.
                   Indica quién es el favorito a liderar e,
                   indirectamente, quién tiene más chances de pasar.

ESTRUCTURA ESPERADA:
    mundial/
    └── data/
        ├── grupos.json
        ├── selecciones.json
        └── modelo_grupos.py  <- este archivo

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
#  PESOS DEL MODELO
#  Basados en análisis estadístico de Mundiales 1994-2022.
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
#  UTILIDADES
# =============================================================

def clamp(valor, minimo=0.0, maximo=1.0):
    return max(minimo, min(maximo, valor))


def normalizar_clave(nombre):
    """'South Korea' -> 'south_korea',  'Côte d\\'Ivoire' -> 'cote_divoire'"""
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


# =============================================================
#  GENERADOR DE NÚMEROS NORMALES (Box-Muller)
#  Reemplaza numpy.random.normal — sin dependencias externas
# =============================================================

def normal_sample(mu=0.0, sigma=1.0):
    """Genera un valor de distribución normal via Box-Muller."""
    while True:
        u1 = random.random()
        u2 = random.random()
        if u1 > 0.0:
            break
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


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
#  MONTE CARLO — Python puro
#
#  Simula n_sim veces el grupo con ruido gaussiano sobre las
#  fuerzas y cuenta en qué posición queda cada equipo.
#  Devuelve matriz probs[equipo][posicion] donde cada columna
#  suma exactamente 1.0 (100%).
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
#  BUSCAR SELECCIÓN EN EL DICT
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

        equipos.append({
            "raw":    eq,
            "sel":    sel,
            "nombre": nombre_eq,
            "fuerza": max(0.01, calcular_fuerza(sel)),
        })

    fuerzas = [e["fuerza"] for e in equipos]
    probs   = monte_carlo(fuerzas)

    # ── Construir resultado ──────────────────────────────────
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
            "fuerza_modelo":   round(fuerzas[i], 4),

            # ── MÉTRICAS PRINCIPALES ──────────────────────────
            # prob_lider: probabilidad de quedar 1° del grupo.
            # Los 4 equipos del grupo suman exactamente 100%.
            # Es el indicador principal de favorito y, de forma
            # indirecta, de chances de pasar a octavos.
            "prob_lider":   round(probs[i][0] * 100, 2),

            # Posiciones secundarias (también suman 100% por columna)
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

    # Ordenar por prob_lider descendente
    resultado_equipos.sort(key=lambda x: x["prob_lider"], reverse=True)

    # Marcar al favorito del grupo
    resultado_equipos[0]["es_favorito"] = True
    for eq in resultado_equipos[1:]:
        eq["es_favorito"] = False

    # Verificación: los 4 prob_lider deben sumar ~100%
    suma = sum(eq["prob_lider"] for eq in resultado_equipos)

    return {
        "grupo":          nombre_grupo,
        "equipos":        resultado_equipos,
        "favorito":       resultado_equipos[0]["equipo"],
        "suma_prob_lider": round(suma, 2),   # debe ser ≈ 100.0
        "no_encontrados": no_encontrados,
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
                f"    {marca} {eq['equipo']:<22}"
                f"FIFA #{eq['ranking_fifa']:<4} "
                f"Lider: {eq['prob_lider']:>5.1f}%  "
                f"(2°:{eq['prob_segundo']:>5.1f}% / 3°:{eq['prob_tercero']:>5.1f}% / 4°:{eq['prob_cuarto']:>5.1f}%)"
            )
        if resultado["no_encontrados"]:
            print(f"    ⚠  Sin datos: {resultado['no_encontrados']}")
        print()

    salida = {
        "meta": {
            "fuente":        "Don Octavio Web",
            "mundial":       "FIFA World Cup 2026",
            "metodo":        "Fuerza compuesta + Monte Carlo 100k simulaciones",
            "metrica_clave": (
                "prob_lider: % de veces que el equipo queda 1° del grupo. "
                "Los 4 equipos de cada grupo suman 100%."
            ),
            "pesos_modelo":  PESOS,
        },
        "grupos": resultados,
    }

    with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Listo → {RUTA_SALIDA}")


if __name__ == "__main__":
    main()
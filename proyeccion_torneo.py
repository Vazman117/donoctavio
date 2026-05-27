import json
import math
import os

# Importa el motor central — no duplicamos nada
from proyeccion import (
    adaptar_equipo,
    predecir_probabilidades,
    calcular_promedio_liga,
    cargar_equipos,
    cargar_h2h,
    obtener_equipo,
    guardar_resultado,
    PERFILES_TORNEO,
    DB_CONFIG,
)


# =============================
# CONFIG DE TORNEOS DE GRUPOS
# =============================

FORMATOS_GRUPO = {
    "conmebol.libertadores": {
        "nombre":               "CONMEBOL Libertadores",
        "total_jornadas":       6,
        "equipos_por_grupo":    4,
        "clasifican":           2,
        "repechaje":            1,
        "perfil":               "libertadores",
        "liga_key":             "conmebol.libertadores",
        "peso_h2h_grupo":       0.25,
        # Promedio histórico de goles/partido en el torneo.
        # Se usa en lugar del promedio calculado desde los pocos partidos
        # de grupos (4-5 partidos dan promedio muy bajo → lambdas bajos → empate inflado).
        "promedio_goles_torneo": 2.30,
    },
    "conmebol.sudamericana": {
        "nombre":               "CONMEBOL Sudamericana",
        "total_jornadas":       6,
        "equipos_por_grupo":    4,
        "clasifican":           1,
        "repechaje":            1,
        "perfil":               "sudamericana",
        "liga_key":             "conmebol.sudamericana",
        "peso_h2h_grupo":       0.25,
        "promedio_goles_torneo": 2.20,
    },
    "uefa.champions": {
        "nombre":               "UEFA Champions League",
        "total_jornadas":       6,
        "equipos_por_grupo":    4,
        "clasifican":           2,
        "repechaje":            1,
        "perfil":               "champions_league",
        "liga_key":             "uefa.champions",
        "peso_h2h_grupo":       0.22,
        "promedio_goles_torneo": 2.80,
    },
    "uefa.europa": {
        "nombre":               "UEFA Europa League",
        "total_jornadas":       6,
        "equipos_por_grupo":    4,
        "clasifican":           2,
        "repechaje":            1,
        "perfil":               "europa_league",
        "liga_key":             "uefa.europa",
        "peso_h2h_grupo":       0.22,
        "promedio_goles_torneo": 2.60,
    },
}


# =============================
# HELPERS
# =============================

def limitar(v, a, b):
    return max(a, min(v, b))

def nivel_impacto(d):
    if d >= 0.25:   return "alto"
    elif d >= 0.12: return "medio"
    else:           return "bajo"

def normalizar_nombre(nombre):
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


# =============================
# H2H DE FASE DE GRUPOS
# =============================

def buscar_h2h_grupo(nombre_local, nombre_visitante, h2h_data):
    """
    Busca el partido que ya jugaron estos dos equipos en la fase de grupos.
    El h2h.json del torneo tiene todos los cruces ya disputados.

    Devuelve:
        h2h_score       → ventaja del local (0.0 a 1.0, 0.5 = neutro)
        partido         → el partido encontrado (dict) o None
        ventaja_goles   → diferencia de goles a favor del local en el H2H
        descripcion     → texto descriptivo del resultado anterior
    """
    nl = normalizar_nombre(nombre_local)
    nv = normalizar_nombre(nombre_visitante)

    cruce = None
    for key, val in h2h_data.items():
        partidos = val.get("partidos", [])
        if not partidos:
            continue
        # Verificar si este cruce involucra a ambos equipos
        ea = normalizar_nombre(val.get("equipo_a", ""))
        eb = normalizar_nombre(val.get("equipo_b", ""))
        if (ea == nl and eb == nv) or (ea == nv and eb == nl):
            cruce = val
            break

    if not cruce or not cruce.get("partidos"):
        return 0.5, None, 0, "Sin enfrentamiento previo en este torneo."

    # Solo tomamos el primer (y único) partido disponible
    partido = cruce["partidos"][0]
    gl      = partido["goles_local"]
    gv      = partido["goles_visitante"]
    local_en_partido = normalizar_nombre(partido["local"]) == nl

    # ── Score H2H para el local de HOY ──────────────────────────────────────
    if gl == gv:
        # Empate en el H2H → neutro
        h2h_score     = 0.5
        ventaja_goles = 0
        quien_gano    = "empate"
    elif gl > gv:
        # Ganó el local del partido anterior
        if local_en_partido:
            # El local de hoy también fue local y ganó → ventaja
            h2h_score     = 0.72
            ventaja_goles = gl - gv
            quien_gano    = "local_hoy"
        else:
            # El local de hoy fue visitante y perdió → desventaja
            h2h_score     = 0.28
            ventaja_goles = -(gl - gv)
            quien_gano    = "visitante_hoy"
    else:
        # Ganó el visitante del partido anterior
        if local_en_partido:
            # El local de hoy fue local y perdió → desventaja
            h2h_score     = 0.28
            ventaja_goles = -(gv - gl)
            quien_gano    = "visitante_hoy"
        else:
            # El local de hoy fue visitante y ganó → ventaja
            h2h_score     = 0.72
            ventaja_goles = gv - gl
            quien_gano    = "local_hoy"

    # ── Descripción ─────────────────────────────────────────────────────────
    fecha = partido.get("fecha", "")[:10]
    if quien_gano == "empate":
        descripcion = (f"Se enfrentaron el {fecha}: {partido['local']} {gl}-{gv} "
                       f"{partido['visitante']}. Empate.")
    elif quien_gano == "local_hoy":
        descripcion = (f"Se enfrentaron el {fecha}: {partido['local']} {gl}-{gv} "
                       f"{partido['visitante']}. {nombre_local} ganó ese partido.")
    else:
        descripcion = (f"Se enfrentaron el {fecha}: {partido['local']} {gl}-{gv} "
                       f"{partido['visitante']}. {nombre_visitante} ganó ese partido.")

    return limitar(h2h_score, 0.0, 1.0), partido, ventaja_goles, descripcion


def calcular_bonus_h2h_grupo(ventaja_goles, urgencia_local, urgencia_visitante):
    """
    La ventaja en goles del H2H puede ser decisiva en caso de empate en puntos.
    Si un equipo necesita remontar la diferencia de goles, su urgencia sube.
    Devuelve ajuste adicional a aplicar sobre el bonus de urgencia.
    """
    if ventaja_goles == 0:
        return 0.0, 0.0

    # Si el local va perdiendo en el H2H Y tiene urgencia alta/media,
    # necesita no solo ganar sino hacerlo por margen → sube presión
    bonus_extra_local     = 0.0
    bonus_extra_visitante = 0.0

    if ventaja_goles < 0 and urgencia_local in ("alta", "media"):
        # Local necesita remontar goles — presión extra
        bonus_extra_local = min(0.05, abs(ventaja_goles) * 0.02)
    elif ventaja_goles > 0 and urgencia_visitante in ("alta", "media"):
        # Visitante necesita remontar goles — presión extra
        bonus_extra_visitante = min(0.05, abs(ventaja_goles) * 0.02)

    return bonus_extra_local, bonus_extra_visitante


# =============================
# ANÁLISIS DE TABLA DE GRUPO
# =============================

def analizar_tabla_grupo(tabla, jornada_actual, formato):
    """
    Determina para cada equipo su estado, puntos necesarios y urgencia.

    tabla: lista de dicts ordenada por posición, cada uno con:
        {equipo, puntos, partidos, ganados, empatados, perdidos,
         goles_favor, goles_contra, diferencia_goles}
    """
    total_jornadas   = formato["total_jornadas"]
    clasifican       = formato["clasifican"]
    con_repechaje    = formato.get("repechaje", 0)
    jornadas_rest    = total_jornadas - jornada_actual
    pts_por_ganar    = jornadas_rest * 3

    # Peso del contexto según jornada
    # Jornada 1 → 0.40 | Jornada 6 → 1.00
    peso_contexto = round(0.40 + (jornada_actual / total_jornadas) * 0.60, 2)

    resultado = []
    for i, eq in enumerate(tabla):
        pos    = i + 1
        pts    = eq["puntos"]
        nombre = eq["equipo"]

        # ── Clasificado matemáticamente ──────────────────────────────────────
        if pos <= clasifican:
            rival_bajo     = tabla[clasifican] if len(tabla) > clasifican else None
            pts_max_rival  = rival_bajo["puntos"] + pts_por_ganar if rival_bajo else 0
            clasificado_mat = pts > pts_max_rival
        else:
            clasificado_mat = False

        # ── Eliminado matemáticamente ────────────────────────────────────────
        if pos > clasifican:
            pts_max_propio = pts + pts_por_ganar
            rival_arriba   = tabla[clasifican - 1]
            eliminado_mat  = pts_max_propio < rival_arriba["puntos"]
        else:
            eliminado_mat = False

        # ── Puntos necesarios y estado ───────────────────────────────────────
        if clasificado_mat:
            pts_necesita  = 0
            estado        = "clasificado"
        elif eliminado_mat:
            pts_necesita  = 0
            estado        = "eliminado"
        elif pos <= clasifican:
            # EN ZONA: calcula cuánto necesita para que el primer rival
            # de abajo del corte NO lo pueda igualar aunque gane todo.
            # Ej: Medellín 7pts, Estudiantes 6pts, 1 jornada:
            #   si Medellín pierde → 7pts, Estudiantes puede llegar a 9pts → lo supera
            #   Medellín necesita 1 pto para asegurar (7+1=8 > 9 no, pero 7 < 9)
            #   Correcto: necesita ganar (3pts) para estar seguro
            rival_abajo = tabla[clasifican] if len(tabla) > clasifican else None
            if rival_abajo:
                pts_max_rival_abajo = rival_abajo["puntos"] + pts_por_ganar
                if pts > pts_max_rival_abajo:
                    # Ya no puede ser alcanzado → asegurado
                    pts_necesita = 0
                else:
                    # Necesita sumar suficiente para que rival no lo iguale
                    pts_necesita = max(1, pts_max_rival_abajo - pts + 1 - pts_por_ganar + 1)
                    pts_necesita = min(pts_necesita, 3)  # máximo 1 victoria
            else:
                pts_necesita = 0
            estado = "en_zona"
        else:
            # FUERA DE ZONA: necesita superar al equipo en el corte
            rival_arriba = tabla[clasifican - 1]
            pts_necesita = (rival_arriba["puntos"] - pts) + 1
            estado       = "fuera_zona"

        # ── Urgencia ─────────────────────────────────────────────────────────
        if clasificado_mat:
            urgencia = "nula_clasificado"
        elif eliminado_mat:
            urgencia = "nula_eliminado"
        elif estado == "en_zona":
            if pts_necesita == 0:
                # Nadie puede alcanzarle aunque gane todo → tranquilo
                urgencia = "nula"
            elif jornadas_rest <= 1:
                # Última(s) jornada(s): necesita puntos para asegurar
                urgencia = "media"   # en zona pero con amenaza real
            else:
                urgencia = "nula"    # quedan jornadas, puede recuperar
        elif pts_necesita <= 3 and jornadas_rest <= 1:
            urgencia = "alta"
        elif pts_necesita <= 3:
            urgencia = "media"
        else:
            urgencia = "alta"

        # ── Depende del partido paralelo ─────────────────────────────────────
        depende_paralelo = (
            not clasificado_mat and
            not eliminado_mat and
            jornadas_rest <= 1 and
            abs(pts - tabla[clasifican - 1]["puntos"]) <= 3
        )

        resultado.append({
            "equipo":           nombre,
            "posicion":         pos,
            "puntos":           pts,
            "estado":           estado,
            "pts_necesita":     pts_necesita,
            "urgencia":         urgencia,
            "clasificado_mat":  clasificado_mat,
            "eliminado_mat":    eliminado_mat,
            "depende_paralelo": depende_paralelo,
            "jornadas_rest":    jornadas_rest,
        })

    return resultado, peso_contexto


# =============================
# BONUS DE URGENCIA
# =============================

BONUS_URGENCIA = {
    "alta":             0.16,
    "media":            0.08,
    "nula":             0.00,
    "nula_clasificado": -0.05,
    "nula_eliminado":    0.05,
}

def get_bonus(urgencia):
    return BONUS_URGENCIA.get(urgencia, 0.0)


# =============================
# INTERPRETACIÓN DE URGENCIA
# =============================

def describir_urgencia(info, nombre_rival, es_local):
    urgencia  = info["urgencia"]
    pts_nec   = info["pts_necesita"]
    jorn_rest = info["jornadas_rest"]
    dep_par   = info["depende_paralelo"]

    sufijo = (f" Su clasificación también depende del resultado del partido paralelo."
              if dep_par else "")

    if urgencia == "nula_clasificado":
        return (f"{info['equipo']} ya tiene la clasificación matemáticamente asegurada. "
                f"Puede especular tácticamente y administrar esfuerzos.")
    elif urgencia == "nula_eliminado":
        return (f"{info['equipo']} está matemáticamente eliminado sin importar el resultado. "
                f"Jugará sin presión, lo que puede traducirse en un equipo más abierto.")
    elif urgencia == "alta":
        if jorn_rest <= 1:
            return (f"{info['equipo']} necesita ganar hoy sí o sí para mantenerse con vida. "
                    f"Necesita al menos {pts_nec} punto(s) más para alcanzar la zona de clasificación. "
                    f"Deberá atacar desde el inicio, generando espacios para {nombre_rival}." + sufijo)
        else:
            return (f"{info['equipo']} está en situación crítica: necesita sumar "
                    f"{pts_nec} puntos en las {jorn_rest} jornadas restantes." + sufijo)
    elif urgencia == "media":
        return (f"{info['equipo']} necesita {pts_nec} punto(s) para asegurar su clasificación. "
                f"Atacará con orden sin sacrificar la estructura defensiva." + sufijo)
    else:
        return (f"{info['equipo']} está en zona de clasificación y puede gestionar "
                f"el partido con relativa comodidad." + sufijo)


# =============================
# ANÁLISIS ESTRUCTURADO
# =============================

def generar_analisis_grupo(
    info_local, info_visitante,
    nombre_local, nombre_visitante,
    local, visitante,
    resultado_base, cfg, peso_contexto,
    h2h_score, partido_h2h, ventaja_goles_h2h, desc_h2h,
    partido_paralelo=None,
):
    factores = []

    # ── 1. CONTEXTO DE GRUPO ─────────────────────────────────────────────────
    interp_partes = [
        describir_urgencia(info_local,     nombre_visitante, es_local=True),
        describir_urgencia(info_visitante, nombre_local,     es_local=False),
    ]
    if partido_paralelo:
        interp_partes.append(
            f"Simultáneamente se juega {partido_paralelo['local']} vs "
            f"{partido_paralelo['visitante']}, cuyo resultado puede afectar "
            f"directamente la clasificación de ambos equipos en este partido."
        )

    factores.append({
        "factor":          "Contexto de grupo",
        "impacto":         "alto",
        "tipo":            "grupo",
        "peso_contexto":   peso_contexto,
        "local": {
            "nombre":           nombre_local,
            "posicion":         info_local["posicion"],
            "puntos":           info_local["puntos"],
            "estado":           info_local["estado"],
            "urgencia":         info_local["urgencia"],
            "pts_necesita":     info_local["pts_necesita"],
            "depende_paralelo": info_local["depende_paralelo"],
        },
        "visitante": {
            "nombre":           nombre_visitante,
            "posicion":         info_visitante["posicion"],
            "puntos":           info_visitante["puntos"],
            "estado":           info_visitante["estado"],
            "urgencia":         info_visitante["urgencia"],
            "pts_necesita":     info_visitante["pts_necesita"],
            "depende_paralelo": info_visitante["depende_paralelo"],
        },
        "partido_paralelo": partido_paralelo,
        "interpretacion":   " ".join(interp_partes),
    })

    # ── 2. H2H DEL TORNEO ────────────────────────────────────────────────────
    if partido_h2h:
        # Impacto del H2H según ventaja de goles
        imp_h2h = nivel_impacto(abs(h2h_score - 0.5) * 2)

        # Contexto de diferencia de goles para el desempate
        nota_goles = ""
        if abs(ventaja_goles_h2h) >= 1:
            if ventaja_goles_h2h > 0:
                nota_goles = (f" Además, {nombre_local} lleva ventaja de "
                              f"{ventaja_goles_h2h} gol(es) en el marcador acumulado, "
                              f"lo que podría ser decisivo en caso de empate en puntos.")
            else:
                nota_goles = (f" Además, {nombre_visitante} lleva ventaja de "
                              f"{abs(ventaja_goles_h2h)} gol(es) en el marcador acumulado, "
                              f"lo que podría ser decisivo en caso de empate en puntos.")

        factores.append({
            "factor":          "Historial en el torneo",
            "impacto":         imp_h2h,
            "tipo":            "h2h_grupo",
            "local":           {"nombre": nombre_local,     "h2h_score": round(h2h_score, 2)},
            "visitante":       {"nombre": nombre_visitante, "h2h_score": round(1 - h2h_score, 2)},
            "partido":         partido_h2h,
            "ventaja_goles":   ventaja_goles_h2h,
            "interpretacion":  desc_h2h + nota_goles,
        })
    else:
        factores.append({
            "factor":         "Historial en el torneo",
            "impacto":        "bajo",
            "tipo":           "h2h_grupo",
            "local":          {"nombre": nombre_local,     "h2h_score": 0.5},
            "visitante":      {"nombre": nombre_visitante, "h2h_score": 0.5},
            "partido":        None,
            "ventaja_goles":  0,
            "interpretacion": "Sin enfrentamiento previo en este torneo.",
        })

    # ── 3. FORMA RECIENTE ────────────────────────────────────────────────────
    fl    = local["forma_ponderada"]
    fv    = visitante["forma_ponderada"]
    ul5_l = local.get("ultimos_5", [])
    ul5_v = visitante.get("ultimos_5", [])
    wins_l  = ul5_l.count("W"); losses_l = ul5_l.count("L")
    wins_v  = ul5_v.count("W"); losses_v = ul5_v.count("L")
    draws_l = ul5_l.count("D"); draws_v  = ul5_v.count("D")

    if fl > fv:
        interp = (f"{nombre_local} llega con mejor momentum: índice {fl:.2f}/1.0 "
                  f"frente a {fv:.2f}/1.0 de {nombre_visitante}. "
                  f"Últimos 5: {wins_l}V/{draws_l}E/{losses_l}D vs {wins_v}V/{draws_v}E/{losses_v}D.")
    elif fv > fl:
        interp = (f"{nombre_visitante} llega con mejor momentum: índice {fv:.2f}/1.0 "
                  f"frente a {fl:.2f}/1.0 de {nombre_local}. "
                  f"Últimos 5: {wins_v}V/{draws_v}E/{losses_v}D vs {wins_l}V/{draws_l}E/{losses_l}D.")
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

    # ── 4. RENDIMIENTO SITUACIONAL ───────────────────────────────────────────
    wrl  = local["win_rate_local"]
    wrv  = visitante["win_rate_visita"]
    gl_l = local.get("ganados_local", 0);   el_l = local.get("empatados_local", 0)
    pl_l = local.get("perdidos_local", 0)
    gv_v = visitante.get("ganados_visita", 0); ev_v = visitante.get("empatados_visita", 0)
    pv_v = visitante.get("perdidos_visita", 0)

    if wrl >= 0.55 and wrv <= 0.30:
        interp = (f"Contraste marcado: {nombre_local} gana el {wrl*100:.0f}% en casa "
                  f"({gl_l}G/{el_l}E/{pl_l}P), {nombre_visitante} solo el {wrv*100:.0f}% "
                  f"de visita ({gv_v}G/{ev_v}E/{pv_v}P).")
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
        "local":     {"etiqueta": "Win rate local",  "valor": round(wrl * 100, 1),
                      "detalle": f"{gl_l}G/{el_l}E/{pl_l}P", "nombre": nombre_local},
        "visitante": {"etiqueta": "Win rate visita", "valor": round(wrv * 100, 1),
                      "detalle": f"{gv_v}G/{ev_v}E/{pv_v}P", "nombre": nombre_visitante},
        "interpretacion": interp,
    })

    # ── 5. POTENCIAL OFENSIVO Y DEFENSIVO ────────────────────────────────────
    gf_l = local["goles_favor_promedio"];   gc_l = local["goles_contra_promedio"]
    gf_v = visitante["goles_favor_promedio"]; gc_v = visitante["goles_contra_promedio"]
    vo   = gf_l - gf_v; vd = gc_v - gc_l

    if vo >= 0.4 and vd >= 0.3:
        interp = (f"Superioridad integral de {nombre_local}: {gf_l:.2f} goles/partido "
                  f"(vs {gf_v:.2f}) y solo {gc_l:.2f} recibidos (vs {gc_v:.2f}).")
    elif vo >= 0.4:
        interp = (f"{nombre_local} más ofensivo: {gf_l:.2f} vs {gf_v:.2f} goles/partido. "
                  f"Defensa: {gc_l:.2f} vs {gc_v:.2f}.")
    elif vo <= -0.4:
        interp = (f"{nombre_visitante} más ofensivo: {gf_v:.2f} vs {gf_l:.2f} goles/partido. "
                  f"Defensa: {gc_l:.2f} vs {gc_v:.2f}.")
    else:
        interp = (f"Producción similar: {nombre_local} {gf_l:.2f} — "
                  f"{nombre_visitante} {gf_v:.2f} goles/partido. "
                  f"Defensa: {gc_l:.2f} vs {gc_v:.2f}.")

    factores.append({
        "factor":    "Potencial ofensivo y defensivo",
        "impacto":   nivel_impacto(abs(vo)*0.5 + abs(vd)*0.5),
        "tipo":      "doble_barra",
        "local":     {"nombre": nombre_local,     "goles_favor": round(gf_l,2), "goles_contra": round(gc_l,2)},
        "visitante": {"nombre": nombre_visitante, "goles_favor": round(gf_v,2), "goles_contra": round(gc_v,2)},
        "interpretacion": interp,
    })

    # ── 6. URGENCIA TÁCTICA ──────────────────────────────────────────────────
    urg_l   = info_local["urgencia"]
    urg_v   = info_visitante["urgencia"]
    bonus_l = get_bonus(urg_l)
    bonus_v = get_bonus(urg_v)

    interp_l = describir_urgencia(info_local,     nombre_visitante, es_local=True)
    interp_v = describir_urgencia(info_visitante, nombre_local,     es_local=False)

    if urg_l in ("nula_clasificado","nula_eliminado","nula") and urg_v in ("alta","media"):
        interp = interp_v + " " + interp_l
    elif urg_v in ("nula_clasificado","nula_eliminado","nula") and urg_l in ("alta","media"):
        interp = interp_l + " " + interp_v
    else:
        interp = interp_l + " " + interp_v

    factores.append({
        "factor":  "Urgencia táctica",
        "impacto": "alto" if (urg_l == "alta" or urg_v == "alta") else "medio",
        "tipo":    "urgencia",
        "local": {
            "nombre":        nombre_local,
            "urgencia":      urg_l,
            "pts_necesita":  info_local["pts_necesita"],
            "bonus_aplicado": round(bonus_l, 3),
        },
        "visitante": {
            "nombre":        nombre_visitante,
            "urgencia":      urg_v,
            "pts_necesita":  info_visitante["pts_necesita"],
            "bonus_aplicado": round(bonus_v, 3),
        },
        "interpretacion": interp,
    })

    return factores


# =============================
# TABLA RESUMEN DEL GRUPO
# =============================

def generar_tabla_resumen(tabla_grupo, analisis_equipos, formato):
    clasifican    = formato["clasifican"]
    con_repechaje = formato.get("repechaje", 0)
    resumen       = []

    for i, (eq, info) in enumerate(zip(tabla_grupo, analisis_equipos)):
        pos = i + 1
        if pos <= clasifican:
            zona = "clasificacion"
        elif con_repechaje and pos == clasifican + 1:
            zona = "repechaje"
        else:
            zona = "eliminacion"

        resumen.append({
            "posicion":        pos,
            "equipo":          eq["equipo"],
            "escudo":          eq.get("escudo", ""),
            "puntos":          eq["puntos"],
            "partidos":        eq.get("partidos", 0),
            "ganados":         eq.get("ganados", 0),
            "empatados":       eq.get("empatados", 0),
            "perdidos":        eq.get("perdidos", 0),
            "goles_favor":     eq.get("goles_favor", 0),
            "goles_contra":    eq.get("goles_contra", 0),
            "diferencia":      eq.get("diferencia_goles", 0),
            "zona":            zona,
            "estado":          info["estado"],
            "urgencia":        info["urgencia"],
            "pts_necesita":    info["pts_necesita"],
            "clasificado_mat": info["clasificado_mat"],
            "eliminado_mat":   info["eliminado_mat"],
        })

    return resumen


# =============================
# MOTOR PRINCIPAL
# =============================

def generar_partido_grupo(
    id,
    nombre_grupo,
    tabla_grupo,
    local_nombre,
    visitante_nombre,
    jornada_actual,
    db,
    h2h_data,
    torneo_slug,
    partido_paralelo = None,
    archivo_salida   = "partidos_grupos.json",
):
    """
    Genera la proyección de un partido de fase de grupos
    considerando tabla del grupo, H2H del torneo y partido paralelo.

    tabla_grupo:  lista de equipos del grupo (del JSON de grupos)
    h2h_data:     dict del h2h.json del torneo
    torneo_slug:  clave en FORMATOS_GRUPO
    """
    formato = FORMATOS_GRUPO.get(torneo_slug)
    if not formato:
        raise ValueError(f"Torneo '{torneo_slug}' no en FORMATOS_GRUPO. "
                         f"Opciones: {list(FORMATOS_GRUPO.keys())}")

    cfg = PERFILES_TORNEO.get(formato["perfil"])
    if not cfg:
        raise ValueError(f"Perfil '{formato['perfil']}' no encontrado.")

    # ── Obtener y adaptar equipos ────────────────────────────────────────────
    local_raw     = obtener_equipo(local_nombre,     db)
    visitante_raw = obtener_equipo(visitante_nombre, db)

    if not local_raw:
        raise ValueError(f"Equipo local no encontrado: '{local_nombre}'")
    if not visitante_raw:
        raise ValueError(f"Equipo visitante no encontrado: '{visitante_nombre}'")

    # Asegurar que el campo "nombre" exista (grupos.json usa "equipo")
    if "nombre" not in local_raw:
        local_raw = dict(local_raw); local_raw["nombre"] = local_raw.get("equipo", local_nombre)
    if "nombre" not in visitante_raw:
        visitante_raw = dict(visitante_raw); visitante_raw["nombre"] = visitante_raw.get("equipo", visitante_nombre)

    liga_key  = formato["liga_key"]
    local     = adaptar_equipo(local_raw,     liga_key=liga_key)
    visitante = adaptar_equipo(visitante_raw, liga_key=liga_key)

    # ── Análisis de tabla ────────────────────────────────────────────────────
    analisis_equipos, peso_contexto = analizar_tabla_grupo(
        tabla_grupo, jornada_actual, formato
    )

    info_local = next(
        (e for e in analisis_equipos
         if normalizar_nombre(e["equipo"]) == normalizar_nombre(local_nombre)), None
    )
    info_visitante = next(
        (e for e in analisis_equipos
         if normalizar_nombre(e["equipo"]) == normalizar_nombre(visitante_nombre)), None
    )

    if not info_local or not info_visitante:
        raise ValueError(
            f"'{local_nombre}' o '{visitante_nombre}' no están en tabla_grupo. "
            f"Equipos disponibles: {[e['equipo'] for e in tabla_grupo]}"
        )

    # ── H2H del torneo ───────────────────────────────────────────────────────
    h2h_score, partido_h2h, ventaja_goles_h2h, desc_h2h = buscar_h2h_grupo(
        local_nombre, visitante_nombre, h2h_data
    )

    # Bonus extra por diferencia de goles en H2H (desempate)
    bonus_extra_l, bonus_extra_v = calcular_bonus_h2h_grupo(
        ventaja_goles_h2h,
        info_local["urgencia"],
        info_visitante["urgencia"],
    )

    # ── Predicción base ──────────────────────────────────────────────────────
    # Usar el promedio histórico del torneo, NO el calculado desde los pocos
    # partidos de grupos — con 4-5 partidos el promedio es artificialmente bajo
    # y hace que Poisson infle el empate (lambdas bajos → todo 0-0).
    promedio_liga = formato.get("promedio_goles_torneo") or calcular_promedio_liga(db)

    # Modificar temporalmente el perfil para incluir el H2H del grupo
    # con su peso específico (mayor que el H2H de liga normal)
    cfg_grupos = dict(cfg)
    cfg_grupos["usa_h2h"]   = True
    cfg_grupos["PESO_H2H"]  = formato["peso_h2h_grupo"]
    cfg_grupos["PESO_BASE"] = max(0.50, cfg["PESO_BASE"] - formato["peso_h2h_grupo"])

    # Construir h2h_data en el formato que espera predecir_probabilidades
    h2h_para_motor = {}
    if partido_h2h:
        h2h_para_motor = {
            "cruce_grupo": {
                "equipo_a":        local_nombre,
                "equipo_b":        visitante_nombre,
                "partidos_recientes": [partido_h2h],
                "clausura_2026":   [],
                "apertura_2025":   [],
            }
        }
        # Inyectar el score directamente para que el motor lo use
        # En lugar de recalcularlo, pasamos los pesos al perfil
        cfg_grupos["h2h_score_override"] = h2h_score

    resultado_base = predecir_probabilidades(
        local, visitante, h2h_para_motor,
        local_nombre, visitante_nombre,
        promedio_liga, cfg_grupos,
    )

    # ── Ajuste por urgencia + contexto de grupo ──────────────────────────────
    bonus_urg_l = get_bonus(info_local["urgencia"])
    bonus_urg_v = get_bonus(info_visitante["urgencia"])

    ajuste_l = (bonus_urg_l + bonus_extra_l) * peso_contexto
    ajuste_v = (bonus_urg_v + bonus_extra_v) * peso_contexto

    # Reducción de empate por urgencia:
    # Si alguien NECESITA ganar, un empate no le sirve → el empate baja.
    # Si ambos están clasificados/eliminados sin presión → el empate sube levemente.
    urg_l = info_local["urgencia"]
    urg_v = info_visitante["urgencia"]

    # ── Ajuste de empate por paridad de fuerzas ─────────────────────────────
    # El motor central puede subestimar el empate cuando las fuerzas son
    # muy parejas. Interpolamos hacia el empate esperado en partidos igualados.
    gap_fuerzas    = abs(resultado_base["local"] - resultado_base["visitante"])
    UMBRAL_PARIDAD = 0.15   # gap menor = partido parejo
    EMPATE_PAREJO  = 0.24   # empate esperado cuando fuerzas son iguales

    # factor_paridad: 0.0 = muy parejo | 1.0 = muy desigual
    factor_paridad = limitar(gap_fuerzas / UMBRAL_PARIDAD, 0.0, 1.0)

    # Si las fuerzas son parejas, subimos el empate hacia EMPATE_PAREJO.
    # Si son disparejas, el empate base del motor se mantiene.
    empate_base = resultado_base["empate"]
    ajuste_paridad = (1.0 - factor_paridad) * (EMPATE_PAREJO - empate_base)
    empate_ajustado = empate_base + ajuste_paridad

    # Reducción por urgencia — modulada por paridad:
    # Partido parejo + urgencia → reducción pequeña (empate sigue siendo real)
    # Partido desigual + urgencia → reducción normal
    if urg_l == "alta" or urg_v == "alta":
        reduccion_empate = 0.10 * peso_contexto * factor_paridad
    elif urg_l == "media" or urg_v == "media":
        reduccion_empate = 0.05 * peso_contexto * factor_paridad
    elif urg_l == "nula_clasificado" and urg_v == "nula_clasificado":
        reduccion_empate = -0.04   # ambos clasificados → empate sube
    elif urg_l == "nula_eliminado" and urg_v == "nula_eliminado":
        reduccion_empate = 0.0
    else:
        reduccion_empate = 0.0

    prob_local     = max(0.05, min(0.85, resultado_base["local"]     + ajuste_l))
    prob_empate    = max(0.05, empate_ajustado - reduccion_empate)
    prob_visitante = max(0.05, min(0.85, resultado_base["visitante"] + ajuste_v))

    # Renormalizar
    total          = prob_local + prob_empate + prob_visitante
    prob_local    /= total
    prob_empate   /= total
    prob_visitante /= total

    gap       = abs(prob_local - prob_visitante)
    confianza = "ajustado" if gap < 0.08 else "moderado" if gap < 0.18 else "favorable"

    # ── Predicción ───────────────────────────────────────────────────────────
    maxima = max(prob_local, prob_empate, prob_visitante)
    if   maxima == prob_local:     pred = local["nombre"]
    elif maxima == prob_empate:    pred = "Empate"
    else:                          pred = visitante["nombre"]

    # ── Tabla resumen y análisis ─────────────────────────────────────────────
    tabla_resumen = generar_tabla_resumen(tabla_grupo, analisis_equipos, formato)

    analisis = generar_analisis_grupo(
        info_local, info_visitante,
        local_nombre, visitante_nombre,
        local, visitante,
        resultado_base, cfg_grupos, peso_contexto,
        h2h_score, partido_h2h, ventaja_goles_h2h, desc_h2h,
        partido_paralelo=partido_paralelo,
    )

    output = {
        "id":                    id,
        "torneo":                formato["nombre"],
        "torneo_slug":           torneo_slug,
        "grupo":                 nombre_grupo,
        "jornada":               jornada_actual,
        "jornadas_total":        formato["total_jornadas"],
        "local":                 local["nombre"],
        "visitante":             visitante["nombre"],
        "logo_local":            local_raw.get("escudo"),
        "logo_visitante":        visitante_raw.get("escudo"),
        "prob_local":            prob_local,
        "prob_empate":           prob_empate,
        "prob_visitante":        prob_visitante,
        "fuerza_local":          resultado_base["fuerza_local"],
        "fuerza_visitante":      resultado_base["fuerza_visitante"],
        "diferencia":            resultado_base["diferencia"],
        "confianza":             confianza,
        "prediccion":            pred,
        "lambda_local":          resultado_base["lambda_local"],
        "lambda_visitante":      resultado_base["lambda_visitante"],
        "peso_contexto_grupo":   peso_contexto,
        "urgencia_local":        info_local["urgencia"],
        "urgencia_visitante":    info_visitante["urgencia"],
        "h2h_grupo": {
            "score_local":    round(h2h_score, 3),
            "ventaja_goles":  ventaja_goles_h2h,
            "partido":        partido_h2h,
            "descripcion":    desc_h2h,
        },
        "tabla_grupo":           tabla_resumen,
        "partido_paralelo":      partido_paralelo,
        "analisis":              analisis,
    }

    guardar_resultado(output, archivo_salida)
    return output


# =============================
# CARGAR DATOS
# =============================

def cargar_grupos(torneo_slug):
    """Carga scrapper/<CARPETA>/grupos.json"""
    cfg_db = next(
        (cfg for cfg in DB_CONFIG.values()
         if cfg.get("liga_key") == torneo_slug), None
    )
    if not cfg_db:
        raise ValueError(f"No se encontró DB_CONFIG para '{torneo_slug}'")
    ruta = os.path.join("scrapper", cfg_db["carpeta"], "grupos.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_equipos_desde_grupos(torneo_slug):
    """
    Construye el dict de equipos directamente desde grupos.json.
    grupos.json es la única fuente de verdad para torneos de fase de grupos —
    no se necesita equipos.json por separado.

    El dict resultante tiene la misma estructura que equipos.json:
    { "normalizado": {datos_equipo} }
    """
    grupos = cargar_grupos(torneo_slug)
    equipos = {}

    for grupo in grupos:
        for eq in grupo["equipos"]:
            # grupos.json usa "equipo" como nombre — normalizamos a "nombre"
            eq_norm = dict(eq)
            if "equipo" in eq_norm and "nombre" not in eq_norm:
                eq_norm["nombre"] = eq_norm["equipo"]

            key = normalizar_nombre(eq_norm["nombre"])
            equipos[key] = eq_norm

    return equipos


def encontrar_grupo(grupos, nombre_equipo):
    """Encuentra el grupo al que pertenece un equipo."""
    nn = normalizar_nombre(nombre_equipo)
    for grupo in grupos:
        for eq in grupo["equipos"]:
            if normalizar_nombre(eq["equipo"]) == nn:
                return grupo
    return None


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    # ── Cargar datos ─────────────────────────────────────────────────────────
    # grupos.json es la única fuente — no se necesita equipos.json por separado
    grupos_lib = cargar_grupos("conmebol.sudamericana")
    db_lib     = cargar_equipos_desde_grupos("conmebol.sudamericana")
    h2h_lib    = cargar_h2h("SUDAMERICANA")      # h2h.json del torneo

    # ── Casos a proyectar ─────────────────────────────────────────────────────
    # Formato: local, visitante, torneo_slug, jornada, partido_paralelo, salida
    # El grupo se detecta automáticamente desde grupos.json
    #
    # IMPORTANTE: jornada = partidos ya jugados ANTES del partido de hoy.
    # Si hoy se juega la jornada 6 y ya se jugaron 5 → jornada=5
    # La tabla refleja el estado ANTES del partido de hoy.
    # ─────────────────────────────────────────────────────────────────────────

    CASOS = [
        # ── Grupo E — Jornada 6 ──────────────────────────────────────────────
        {
            "id":              1,
            "local":           "Atletico-MG",
            "visitante":       "Academia Puerto Cabello",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Cienciano del Cusco", "visitante": "Juventud"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        {
            "id":              2,
            "local":           "Cienciano del Cusco",
            "visitante":       "Juventud",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Atletico-MG", "visitante": "Academia Puerto Cabello"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        # ── Grupo A — Jornada 6 ──────────────────────────────────────────────
        {
            "id":              3,
            "local":           "Club Olimpia",
            "visitante":       "Audax Italiano",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Vasco Da Gama", "visitante": "Barracas Central"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        {
            "id":              4,
            "local":           "Vasco Da Gama",
            "visitante":       "Barracas Central",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Club Olimpia", "visitante": "Audax Italiano"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        # ── Grupo G — Jornada 6 ──────────────────────────────────────────────
        {
            "id":              5,
            "local":           "Racing Club",
            "visitante":       "Independiente Petrolero",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Caracas FC", "visitante": "Botafogo"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        {
            "id":              6,
            "local":           "Caracas FC",
            "visitante":       "Botafogo",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Racing Club", "visitante": "Independiente Petrolero"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        {
            "id":              7,
            "local":           "River Plate",
            "visitante":       "Blooming",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "Red Bull Bragantino", "visitante": "Carabobo"},
            "salida":          "partidos_grupos_libertadores.json",
        },
        {
            "id":              8,
            "local":           "Red Bull Bragantino",
            "visitante":       "Carabobo",
            "torneo_slug":     "conmebol.sudamericana",
            "jornada":         5,
            "partido_paralelo": {"local": "River Plate", "visitante": "Blooming"},
            "salida":          "partidos_grupos_libertadores.json",
        },
    ]

    # ── Ejecución ─────────────────────────────────────────────────────────────
    print(f"\n🚀 Generando {len(CASOS)} proyecciones de fase de grupos...\n" + "="*60)

    for caso in CASOS:
        local_nombre     = caso["local"]
        visitante_nombre = caso["visitante"]
        torneo_slug      = caso["torneo_slug"]

        grupo = encontrar_grupo(grupos_lib, local_nombre)
        if not grupo:
            print(f"  ❌ Grupo no encontrado para '{local_nombre}'")
            continue

        try:
            p = generar_partido_grupo(
                id               = caso["id"],
                nombre_grupo     = grupo["grupo"],
                tabla_grupo      = grupo["equipos"],
                local_nombre     = local_nombre,
                visitante_nombre = visitante_nombre,
                jornada_actual   = caso["jornada"],
                db               = db_lib,
                h2h_data         = h2h_lib,
                torneo_slug      = torneo_slug,
                partido_paralelo = caso.get("partido_paralelo"),
                archivo_salida   = caso["salida"],
            )

            h2h_info = p["h2h_grupo"]
            print(f"  ⚽ [{p['grupo']}] "
                  f"{p['local']:<25} vs {p['visitante']:<25}")
            print(f"     {p['prob_local']:.1%} / {p['prob_empate']:.1%} / {p['prob_visitante']:.1%}"
                  f"  →  {p['prediccion']}  [{p['confianza']}]")
            print(f"     Urgencia: {p['urgencia_local']:<22} | {p['urgencia_visitante']}")
            print(f"     H2H torneo: {h2h_info['descripcion'][:60]}...")
            print(f"     Peso contexto: {p['peso_contexto_grupo']}")
            print()

        except Exception as e:
            print(f"  ❌ Error partido {caso['id']} "
                  f"({local_nombre} vs {visitante_nombre}): {e}")
            print()

    print("✅ Proyecciones de grupos completadas.")
"""
BACKTESTING — Evaluación de precisión del modelo de predicción
================================================================

Compara las predicciones que el modelo generó ANTES de cada jornada
(prob_local, prob_empate, prob_visitante, prediccion) contra lo que
realmente pasó (resultado, marcador), leyendo directamente de tu
archivo de historial.

Diseñado para ser tolerante a datos incompletos:
- Partidos sin "resultado" (no jugados aún) se excluyen automáticamente.
- Partidos con "resultado" pero sin "marcador" se incluyen en las
  métricas de 1X2 (accuracy, Brier), pero se excluyen de la métrica
  de marcador exacto.

Uso:
    python backtesting.py                      # usa historial.json en el mismo folder
    python backtesting.py ruta/al/historial.json
"""

import json
import sys


# =============================
# CARGA Y FILTRADO
# =============================

def cargar_historial(ruta="historial.json"):
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("El historial debe ser una lista de partidos.")
    return data


def es_partido_jugado(partido):
    """Un partido cuenta para el backtest solo si ya tiene resultado."""
    resultado = partido.get("resultado")
    return resultado is not None and resultado != ""


def tipo_resultado(partido):
    """
    Traduce el campo 'resultado' (nombre de equipo o 'Empate') a
    una de las 3 categorías: 'local', 'empate', 'visitante'.

    Devuelve None si el valor no se puede mapear con confianza
    (ej. nombre de equipo que no coincide ni con local ni visitante,
    lo cual señalaría un typo/inconsistencia en los datos).
    """
    resultado = partido.get("resultado", "")
    local     = partido.get("local", "")
    visitante = partido.get("visitante", "")

    if resultado == "Empate":
        return "empate"
    if resultado == local:
        return "local"
    if resultado == visitante:
        return "visitante"
    return None  # dato inconsistente, se reporta aparte


def tipo_prediccion(partido):
    """Misma traducción pero para el campo 'prediccion' del modelo."""
    pred      = partido.get("prediccion", "")
    local     = partido.get("local", "")
    visitante = partido.get("visitante", "")

    if pred == "Empate":
        return "empate"
    if pred == local:
        return "local"
    if pred == visitante:
        return "visitante"
    return None


# =============================
# MÉTRICAS POR PARTIDO
# =============================

def brier_score_partido(partido, tipo_real):
    """
    Brier score de un partido individual:
    suma de (prob_predicha - resultado_real)^2 para las 3 categorías.
    0 = predicción perfecta. ~0.67 = tan malo como tirar dados.
    """
    p_local  = partido.get("prob_local", 0.0)
    p_empate = partido.get("prob_empate", 0.0)
    p_vis    = partido.get("prob_visitante", 0.0)

    r_local  = 1.0 if tipo_real == "local"     else 0.0
    r_empate = 1.0 if tipo_real == "empate"    else 0.0
    r_vis    = 1.0 if tipo_real == "visitante" else 0.0

    return (p_local - r_local) ** 2 + (p_empate - r_empate) ** 2 + (p_vis - r_vis) ** 2


def benchmark_siempre_local(partido, tipo_real):
    """Línea base: '¿qué pasaría si siempre le atinara al local?'"""
    return tipo_real == "local"


def marcador_exacto_acierto(partido):
    """
    True/False/None:
    - None si no hay 'marcador' real o no hay 'marcadores_probables' (se excluye del cálculo)
    - True si el marcador real coincide con el top-1 de marcadores_probables
    - False si no coincide
    """
    marcador_real = partido.get("marcador")
    probables      = partido.get("marcadores_probables")
    if not marcador_real or not probables:
        return None
    return marcador_real == probables[0]


# =============================
# ACUMULADOR DE MÉTRICAS
# =============================

class Acumulador:
    """Junta las métricas de un grupo de partidos (general, por tipo, por torneo)."""

    def __init__(self, nombre):
        self.nombre = nombre
        self.total = 0
        self.aciertos = 0
        self.aciertos_benchmark = 0
        self.suma_brier = 0.0
        self.por_tipo_real = {"local": 0, "empate": 0, "visitante": 0}
        self.por_tipo_acierto = {"local": 0, "empate": 0, "visitante": 0}
        self.marcador_total = 0
        self.marcador_aciertos = 0
        self.inconsistentes = 0

    def procesar(self, partido):
        tipo_real = tipo_resultado(partido)
        if tipo_real is None:
            self.inconsistentes += 1
            return

        tipo_pred = tipo_prediccion(partido)

        self.total += 1
        self.por_tipo_real[tipo_real] += 1

        if tipo_pred == tipo_real:
            self.aciertos += 1
            self.por_tipo_acierto[tipo_real] += 1

        if benchmark_siempre_local(partido, tipo_real):
            self.aciertos_benchmark += 1

        self.suma_brier += brier_score_partido(partido, tipo_real)

        acierto_marcador = marcador_exacto_acierto(partido)
        if acierto_marcador is not None:
            self.marcador_total += 1
            if acierto_marcador:
                self.marcador_aciertos += 1

    # ── Métricas derivadas ──────────────────────────────────────────────

    @property
    def accuracy(self):
        return self.aciertos / self.total if self.total else None

    @property
    def accuracy_benchmark(self):
        return self.aciertos_benchmark / self.total if self.total else None

    @property
    def brier_promedio(self):
        return self.suma_brier / self.total if self.total else None

    @property
    def accuracy_marcador(self):
        return self.marcador_aciertos / self.marcador_total if self.marcador_total else None

    def recall_por_tipo(self, tipo):
        """De los partidos donde el resultado real fue 'tipo', ¿en cuántos acertó el modelo?"""
        total_tipo = self.por_tipo_real[tipo]
        if total_tipo == 0:
            return None
        return self.por_tipo_acierto[tipo] / total_tipo


# =============================
# REPORTE
# =============================

def fmt_pct(valor):
    return f"{valor*100:.1f}%" if valor is not None else "  N/D"


def imprimir_bloque(acum: Acumulador):
    print(f"\n── {acum.nombre} ──────────────────────────────────────")
    print(f"  Partidos evaluados:        {acum.total}")
    if acum.inconsistentes:
        print(f"  ⚠️  Partidos con 'resultado' inconsistente (ignorados): {acum.inconsistentes}")

    if acum.total == 0:
        print("  (sin datos suficientes)")
        return

    print(f"  Accuracy del modelo:       {fmt_pct(acum.accuracy)}")
    print(f"  Accuracy 'siempre local':  {fmt_pct(acum.accuracy_benchmark)}   (línea base)")
    diff = None
    if acum.accuracy is not None and acum.accuracy_benchmark is not None:
        diff = (acum.accuracy - acum.accuracy_benchmark) * 100
    if diff is not None:
        signo = "+" if diff >= 0 else ""
        print(f"  Ventaja vs benchmark:      {signo}{diff:.1f} puntos porcentuales")

    print(f"  Brier score promedio:      {acum.brier_promedio:.4f}   (0 = perfecto, ~0.67 = azar)")

    print(f"\n  Desglose por tipo de resultado real:")
    for tipo in ("local", "empate", "visitante"):
        n = acum.por_tipo_real[tipo]
        rec = acum.recall_por_tipo(tipo)
        print(f"    {tipo:<10} → {n:>3} partidos reales | acierto del modelo: {fmt_pct(rec)}")

    if acum.marcador_total > 0:
        print(f"\n  Marcador exacto (top-1 vs real): {fmt_pct(acum.accuracy_marcador)}"
              f"  ({acum.marcador_aciertos}/{acum.marcador_total} partidos con marcador disponible)")
    else:
        print(f"\n  Marcador exacto: sin datos de 'marcador' disponibles en este grupo.")


def generar_reporte(historial):
    jugados = [p for p in historial if es_partido_jugado(p)]
    no_jugados = len(historial) - len(jugados)

    print("=" * 60)
    print("  REPORTE DE BACKTESTING — Don Octavio")
    print("=" * 60)
    print(f"\nTotal de partidos en historial: {len(historial)}")
    print(f"Partidos ya jugados (con resultado): {len(jugados)}")
    print(f"Partidos pendientes (excluidos):     {no_jugados}")

    if not jugados:
        print("\nNo hay partidos jugados todavía para evaluar.")
        return

    # ── Bloque general ────────────────────────────────────────────────────
    general = Acumulador("GENERAL (todos los partidos jugados)")
    for p in jugados:
        general.procesar(p)
    imprimir_bloque(general)

    # ── Bloque por torneo/perfil ────────────────────────────────────────────
    torneos = {}
    for p in jugados:
        clave = p.get("torneo", "Sin torneo")
        torneos.setdefault(clave, []).append(p)

    print("\n\n" + "=" * 60)
    print("  DESGLOSE POR TORNEO")
    print("=" * 60)
    for nombre_torneo, partidos_torneo in sorted(torneos.items(), key=lambda x: -len(x[1])):
        acum = Acumulador(nombre_torneo)
        for p in partidos_torneo:
            acum.procesar(p)
        imprimir_bloque(acum)

    print("\n" + "=" * 60)
    print("  Fin del reporte.")
    print("=" * 60)


# =============================
# MAIN
# =============================

if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "historial.json"
    try:
        historial = cargar_historial(ruta)
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo '{ruta}'.")
        print("   Uso: python backtesting.py ruta/al/historial.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ El archivo '{ruta}' no es JSON válido: {e}")
        sys.exit(1)

    generar_reporte(historial)
"""
debug_fifa_ranking.py

Script de DIAGNÓSTICO (no toca tus JSON del mundial).
Solo sirve para ver qué nos está devolviendo fifa.com realmente,
para poder ajustar obtener_ranking_fifa() con datos reales.

EJECUTAR:
    python debug_fifa_ranking.py

Pega aquí la salida completa de la consola.
"""

import re
import json
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}

URLS_PAGINA = [
    "https://www.fifa.com/en/fifa-world-ranking/men",
    "https://www.fifa.com/fifa-world-ranking/men",
]


def buscar_listas_con_rank(obj, path=""):
    """Busca recursivamente listas de dicts que tengan alguna clave con 'rank'."""
    encontrados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            nuevo_path = f"{path}.{k}" if path else k
            if isinstance(v, list) and v and isinstance(v[0], dict):
                claves = list(v[0].keys())
                if any("rank" in c.lower() for c in claves):
                    encontrados.append((nuevo_path, len(v), claves, v[0]))
            encontrados += buscar_listas_con_rank(v, nuevo_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:2]):
            encontrados += buscar_listas_con_rank(item, f"{path}[{i}]")
    return encontrados


for url in URLS_PAGINA:
    print("=" * 70)
    print("GET", url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        print("URL final tras redirecciones:", r.url)
        print("status code:", r.status_code)
        print("content-type:", r.headers.get("content-type"))
        print("largo del HTML:", len(r.text))

        # Guardar HTML completo para inspección manual si hace falta
        fname = "debug_fifa_" + url.split("/")[-1] + ".html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(r.text)
        print("HTML guardado en:", fname)

        # ¿Hay algún bloque de datos embebido tipo Next.js / Nuxt / etc.?
        for patron, nombre in [
            (r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', "__NEXT_DATA__"),
            (r'<script id="__NUXT_DATA__"[^>]*>(.*?)</script>', "__NUXT_DATA__"),
            (r'window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>', "window.__NUXT__"),
            (r'<script type="application/json"[^>]*>(.*?)</script>', "application/json script"),
        ]:
            m = re.search(patron, r.text, re.S)
            print(f"  ¿Contiene {nombre}?:", "SÍ" if m else "no")
            if m:
                try:
                    data = json.loads(m.group(1))
                except Exception as e:
                    print("    (no se pudo parsear como JSON):", e)
                    continue

                hallazgos = buscar_listas_con_rank(data)
                if hallazgos:
                    for path_h, n, claves, ejemplo in hallazgos[:5]:
                        print(f"    → Lista encontrada en: {path_h}  ({n} elementos)")
                        print(f"      claves del primer item: {claves}")
                        print(f"      ejemplo: {json.dumps(ejemplo, ensure_ascii=False)[:400]}")
                else:
                    print("    (no se encontraron listas con 'rank' dentro)")

    except Exception as e:
        print("ERROR:", e)
    print()

print("=" * 70)
print("Listo. Pega toda esta salida en el chat.")
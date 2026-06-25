/**
 * historial.js
 * 1. Lee /partidos/index.json para obtener la lista de archivos
 * 2. Carga cada JSON automáticamente
 * 3. Rellena el resumen del home
 *
 * Para agregar partidos nuevos: solo añade el nombre del archivo
 * en /partidos/index.json — no hay que tocar este script nunca.
 */

const CARPETA   = 'partidos/';
const MAX_MINI  = 3; // cuántos partidos mostrar en el home

// ── Utilidades ───────────────────────────────────────────

function fmt(n) {
  return (n * 100).toFixed(1) + '%';
}

function obtenerFavorito(p) {
  if (p.prediccion) return p.prediccion;
  const max = Math.max(p.prob_local, p.prob_empate, p.prob_visitante);
  if (max === p.prob_local)     return p.local;
  if (max === p.prob_visitante) return p.visitante;
  return 'Empate';
}

function obtenerPctFavorito(p, favorito) {
  if (favorito === p.local)     return fmt(p.prob_local);
  if (favorito === p.visitante) return fmt(p.prob_visitante);
  return fmt(p.prob_empate);
}

// ── Carga de datos ───────────────────────────────────────

async function cargarJSON(ruta) {
  const r = await fetch(ruta);
  if (!r.ok) throw new Error(`No se pudo cargar ${ruta}`);
  return r.json();
}

async function cargarTodosLosPartidos() {
  // 1. Lee el índice de archivos
  let archivos = [];
  try {
    archivos = await cargarJSON(CARPETA + 'index.json');
  } catch (e) {
    console.warn('historial.js: no se encontró partidos/index.json', e);
    return [];
  }

  // 2. Carga cada archivo en paralelo, ignora los que fallen
  const resultados = await Promise.allSettled(
    archivos.map(nombre => cargarJSON(CARPETA + nombre))
  );

  const partidos = [];
  for (const res of resultados) {
    if (res.status === 'fulfilled') {
      const data = res.value;
      // Soporta: array directo o { partidos: [...] }
      if (Array.isArray(data))               partidos.push(...data);
      else if (Array.isArray(data.partidos)) partidos.push(...data.partidos);
    }
  }
  return partidos;
}

// ── Render ───────────────────────────────────────────────

function calcularEficiencia(partidos) {
  const conResultado = partidos.filter(p => p.resultado);
  if (conResultado.length === 0) return '—';

  let aciertos = 0;
  for (const p of conResultado) {
    if (p.prediccion === p.resultado) aciertos++;
  }

  return ((aciertos / conResultado.length) * 100).toFixed(1) + '%';
}

function esParidad(p, umbral = 0.15) {
  const probs = [p.prob_local, p.prob_empate, p.prob_visitante];
  probs.sort((a, b) => b - a);

  const diferencia = probs[0] - probs[1];

  return diferencia < umbral;
}

function calcularEfectividadParidad(partidos) {
  const conResultado = partidos.filter(p => p.resultado);

  let totalParidad = 0;
  let aciertosParidad = 0;

  for (const p of conResultado) {
    if (esParidad(p)) {
      totalParidad++;

      if (p.prediccion === p.resultado) {
        aciertosParidad++;
      }
    }
  }

  if (totalParidad === 0) return '—';

  return ((aciertosParidad / totalParidad) * 100).toFixed(1) + '%';
}

function renderMetricas(partidos) {
  const el = document.getElementById('metricas');
  if (!el) return;

  const conResultado = partidos.filter(p => p.resultado);
  const total = conResultado.length;

  let aciertos = 0, ajustados = 0;
  for (const p of conResultado) {
    const fav  = obtenerFavorito(p);
    if (fav === p.resultado) {
      aciertos++;
    } else {
      const probs = [p.prob_local, p.prob_empate, p.prob_visitante];
      probs.sort((a, b) => b - a);
      if (probs[0] - probs[1] < 0.14) ajustados++;
    }
  }

  const eficiencia = total ? ((aciertos / total) * 100).toFixed(1) + '%' : '—';
  const cobertura  = total ? (((aciertos + ajustados) / total) * 100).toFixed(1) + '%' : '—';

  el.innerHTML = `
    <div class="metrica-card">
      <div class="metrica-val">${partidos.length}</div>
      <div class="metrica-lbl">Proyecciones</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-val metrica-val--ok">${eficiencia}</div>
      <div class="metrica-lbl">Eficiencia</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-val metrica-val--pct">${cobertura}</div>
      <div class="metrica-lbl">Cobertura</div>
    </div>
  `;
}

function renderMiniTabla(partidos) {
  const el = document.getElementById('miniTabla');
  if (!el) return;

  const ultimos = partidos.slice(0, MAX_MINI);

  if (ultimos.length === 0) {
    el.innerHTML = `
      <p style="font-size:.78rem;color:var(--muted);text-align:center;padding:.5rem 0;">
        Sin partidos en el historial aún.
      </p>`;
    return;
  }

  el.innerHTML = ultimos.map(p => {
    const favorito = obtenerFavorito(p);
    const pct      = obtenerPctFavorito(p, favorito);
    return `
      <div class="mini-fila">
        <div class="mini-logos">
          <img src="${p.logo_local}"     alt="${p.local}"     onerror="this.style.display='none'">
          <img src="${p.logo_visitante}" alt="${p.visitante}" onerror="this.style.display='none'">
        </div>
        <span class="mini-nombre">${p.local} <em>vs</em> ${p.visitante}</span>
        <span class="mini-pred">${favorito} · ${pct}</span>
      </div>`;
  }).join('');
}

// ── Init ─────────────────────────────────────────────────

async function init() {
  const partidos = await cargarTodosLosPartidos();
  renderMetricas(partidos);
  renderMiniTabla(partidos);
}

init();

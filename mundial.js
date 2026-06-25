document.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash; // "#hoy", "#tabla", etc.
  if (hash) {
    const tabName = hash.replace('#', ''); // "hoy"
    const tabBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    if (tabBtn) tabBtn.click(); // simula el clic en el tab correspondiente
  }
});

const contenido = document.getElementById("contenidoMundial");
const tabs = document.querySelectorAll(".tab-btn");

tabs.forEach(btn => {
  btn.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    cambiarVista(btn.dataset.tab);
  });
});

const hashInicial = window.location.hash.replace('#', '');
const tabInicial  = document.querySelector(`.tab-btn[data-tab="${hashInicial}"]`);

if (tabInicial) {
  tabInicial.click();
} else {
  cambiarVista("grupos");
}

async function cambiarVista(vista) {
  const sec = document.getElementById("contenidoMundial");
  if (vista === "grupos") {
    sec.classList.remove("vista-scroll");
    cargarGrupos();
  }
  if (vista === "tabla") {
    sec.classList.add("vista-scroll");
    cargarTabla();
  }
  if (vista === "hoy") {
    sec.classList.add("vista-scroll");
    cargarHoy();
  }
  if (vista === "historial") {
    sec.classList.add("vista-scroll");
    cargarHistorial();
  }
}


/* ─── HOY ───────────────────────────────────────────────── */

let partidosHoy = [];
let vistaActualHoy = "lista"; // "lista" | "detalle"

/* ── Helpers defensivos ──────────────────────────────── */
function setStyle(id, prop, val) {
  const el = document.getElementById(id);
  if (el) el.style[prop] = val;
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function setHTML(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = val;
}
function addClass(id, cls) {
  const el = document.getElementById(id);
  if (el) el.classList.add(cls);
}
function removeClass(id, cls) {
  const el = document.getElementById(id);
  if (el) el.classList.remove(cls);
}

async function cargarHoy() {
  const res = await fetch("mundial/data/hoy.json");
  partidosHoy = await res.json();
  vistaActualHoy = "lista";
  renderHoyLista();
}

/* ── Render lista de partidos ────────────────────────── */
function renderHoyLista() {
  const header = `
    <div class="tabla-header">
      <span>Partido</span>
      <span>Local</span>
      <span>Empate</span>
      <span>Visitante</span>
      <span>Favorito</span>
    </div>
  `;

  const filas = partidosHoy.map((p, i) => {
    const pL = (p.prob_local     * 100).toFixed(1);
    const pE = (p.prob_empate    * 100).toFixed(1);
    const pV = (p.prob_visitante * 100).toFixed(1);

    return `
      <div class="fila" onclick="mostrarDetalleHoy(${i})">
        <div class="fila-equipo">
          <div class="logos-pair">
            <img src="${p.logo_local}"     alt="${p.local}"     onerror="this.style.visibility='hidden'">
            <img src="${p.logo_visitante}" alt="${p.visitante}" onerror="this.style.visibility='hidden'">
          </div>
          <span class="fila-nombre">${p.local} <em>vs</em> ${p.visitante}</span>
        </div>
        <span class="fila-pct win">${pL}%</span>
        <span class="fila-pct draw">${pE}%</span>
        <span class="fila-pct loss">${pV}%</span>
        <div class="fila-pred">
          <span class="fila-pred-text">${p.prediccion}</span>
          <svg class="fila-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </div>
      </div>
    `;
  }).join("");

  contenido.innerHTML = `
    <div id="vista-hoy-lista">
      ${header}
      ${filas}
    </div>
  `;
}

/* ── Helpers de factores ─────────────────────────────── */

function badgeImpacto(impacto) {
  const cls = impacto === 'alto'  ? 'impacto-alto'
            : impacto === 'medio' ? 'impacto-medio'
            : 'impacto-bajo';
  const txt = impacto === 'alto'  ? 'Impacto alto'
            : impacto === 'medio' ? 'Impacto medio'
            : 'Impacto bajo';
  return `<span class="factor-badge ${cls}">${txt}</span>`;
}

function renderBolitas(ultimos5) {
  return (ultimos5 || []).map(r => {
    const cls = r === 'W' ? 'bolita-w' : r === 'D' ? 'bolita-d' : 'bolita-l';
    return `<span class="bolita ${cls}">${r}</span>`;
  }).join('');
}

function renderBarra(valor, clase) {
  const pct = Math.round(valor * 100);
  return `
    <div class="factor-barra-track">
      <div class="factor-barra-fill ${clase}" style="width:0%" data-w="${pct}%"></div>
    </div>
    <span class="factor-barra-pct">${pct}%</span>
  `;
}

/* ── Render por tipo de factor ───────────────────────── */

function renderFactorForma(f) {
  return `
    <div class="factor-row">
      <span class="factor-equipo-label">${f.local.nombre}</span>
      <div class="factor-bolitas">${renderBolitas(f.local.ultimos_5)}</div>
      <span class="factor-valor">${f.local.valor}</span>
    </div>
    <div class="factor-row">
      <span class="factor-equipo-label">${f.visitante.nombre}</span>
      <div class="factor-bolitas">${renderBolitas(f.visitante.ultimos_5)}</div>
      <span class="factor-valor">${f.visitante.valor}</span>
    </div>
  `;
}

function renderFactorBarras(f) {
  const vl = f.local.valor;
  const vv = f.visitante.valor;
  const claseL = vl >= vv ? 'barra-win' : 'barra-loss';
  const claseV = vv > vl  ? 'barra-win' : 'barra-loss';
  return `
    <div class="factor-row">
      <span class="factor-equipo-label">${f.local.nombre}</span>
      ${renderBarra(vl, claseL)}
    </div>
    ${f.local.detalle ? `<div class="factor-detalle">${f.local.detalle}</div>` : ''}
    <div class="factor-row" style="margin-top:.5rem">
      <span class="factor-equipo-label">${f.visitante.nombre}</span>
      ${renderBarra(vv, claseV)}
    </div>
    ${f.visitante.detalle ? `<div class="factor-detalle">${f.visitante.detalle}</div>` : ''}
  `;
}

function renderFactorDobleBarra(f) {
  const maxGF = Math.max(f.local.goles_favor, f.visitante.goles_favor, 3);
  const maxGC = Math.max(f.local.goles_contra, f.visitante.goles_contra, 3);
  const pGFL  = Math.round((f.local.goles_favor     / maxGF) * 100);
  const pGFV  = Math.round((f.visitante.goles_favor  / maxGF) * 100);
  const pGCL  = Math.round((f.local.goles_contra     / maxGC) * 100);
  const pGCV  = Math.round((f.visitante.goles_contra / maxGC) * 100);
  const claseGFL = f.local.goles_favor    >= f.visitante.goles_favor    ? 'barra-win' : 'barra-loss';
  const claseGFV = f.visitante.goles_favor >= f.local.goles_favor       ? 'barra-win' : 'barra-loss';
  const claseGCL = f.local.goles_contra   <= f.visitante.goles_contra   ? 'barra-win' : 'barra-loss';
  const claseGCV = f.visitante.goles_contra <= f.local.goles_contra     ? 'barra-win' : 'barra-loss';

  return `
    <div class="factor-subgrupo-label">Goles a favor / partido</div>
    <div class="factor-row">
      <span class="factor-equipo-label">${f.local.nombre}</span>
      <div class="factor-barra-track"><div class="factor-barra-fill ${claseGFL}" style="width:0%" data-w="${pGFL}%"></div></div>
      <span class="factor-barra-pct">${f.local.goles_favor}</span>
    </div>
    <div class="factor-row">
      <span class="factor-equipo-label">${f.visitante.nombre}</span>
      <div class="factor-barra-track"><div class="factor-barra-fill ${claseGFV}" style="width:0%" data-w="${pGFV}%"></div></div>
      <span class="factor-barra-pct">${f.visitante.goles_favor}</span>
    </div>
    <div class="factor-subgrupo-label" style="margin-top:.75rem">Goles en contra / partido</div>
    <div class="factor-row">
      <span class="factor-equipo-label">${f.local.nombre}</span>
      <div class="factor-barra-track"><div class="factor-barra-fill ${claseGCL}" style="width:0%" data-w="${pGCL}%"></div></div>
      <span class="factor-barra-pct">${f.local.goles_contra}</span>
    </div>
    <div class="factor-row">
      <span class="factor-equipo-label">${f.visitante.nombre}</span>
      <div class="factor-barra-track"><div class="factor-barra-fill ${claseGCV}" style="width:0%" data-w="${pGCV}%"></div></div>
      <span class="factor-barra-pct">${f.visitante.goles_contra}</span>
    </div>
  `;
}

function renderFactorH2H(f) {
  const total = f.total || 1;
  const pL = Math.round((f.local.victorias    / total) * 100);
  const pV = Math.round((f.visitante.victorias / total) * 100);
  const pE = 100 - pL - pV;

  return `
    <div class="h2h-conteo">
      <div class="h2h-bloque">
        <span class="h2h-num">${f.local.victorias}</span>
        <span class="h2h-lbl">${f.local.nombre}</span>
      </div>
      <div class="h2h-bloque h2h-bloque--center">
        <span class="h2h-num h2h-num--emp">${total - f.local.victorias - f.visitante.victorias}</span>
        <span class="h2h-lbl">Empates</span>
      </div>
      <div class="h2h-bloque">
        <span class="h2h-num">${f.visitante.victorias}</span>
        <span class="h2h-lbl">${f.visitante.nombre}</span>
      </div>
    </div>
    <div class="h2h-barra-total">
      <div class="h2h-seg h2h-seg--local" style="width:${pL}%"></div>
      <div class="h2h-seg h2h-seg--emp"   style="width:${pE}%"></div>
      <div class="h2h-seg h2h-seg--visit" style="width:${pV}%"></div>
    </div>
  `;
}

function renderFactorVuelta(f) {
  return `
    <div class="vuelta-info">
      <div class="vuelta-equipo ${f.equipo_vuelta === f.local.nombre ? 'vuelta-destacado' : ''}">
        <span class="vuelta-pos">${f.local.posicion}°</span>
        <span class="vuelta-nombre">${f.local.nombre}</span>
        ${f.equipo_vuelta === f.local.nombre ? '<span class="vuelta-badge">Vuelta en casa</span>' : ''}
      </div>
      <div class="vuelta-equipo ${f.equipo_vuelta === f.visitante.nombre ? 'vuelta-destacado' : ''}">
        <span class="vuelta-pos">${f.visitante.posicion}°</span>
        <span class="vuelta-nombre">${f.visitante.nombre}</span>
        ${f.equipo_vuelta === f.visitante.nombre ? '<span class="vuelta-badge">Vuelta en casa</span>' : ''}
      </div>
    </div>
  `;
}

function renderFactorMarcadores(f) {
  const marcadores = f.marcadores || [];
  if (!marcadores.length) return '';

  const id = 'mcar-' + Math.random().toString(36).slice(2, 9);

  const slides = marcadores.map((m, i) => `
    <div class="marcador-slide" style="display:${i === 0 ? 'flex' : 'none'}" data-index="${i}">
      <span class="marcador-num">${m}</span>
    </div>
  `).join('');

  const dots = marcadores.map((_, i) => `
    <span class="marcador-dot ${i === 0 ? 'activo' : ''}" data-dot-for="${id}" data-index="${i}"></span>
  `).join('');

  return `
    <div class="marcador-carousel" id="${id}" data-total="${marcadores.length}" data-actual="0">
      <button class="marcador-arrow" onclick="moverCarruselMarcador('${id}', -1)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <div class="marcador-slides">${slides}</div>
      <button class="marcador-arrow" onclick="moverCarruselMarcador('${id}', 1)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    </div>
    <div class="marcador-dots">${dots}</div>
  `;
}

function moverCarruselMarcador(id, delta) {
  const cont = document.getElementById(id);
  if (!cont) return;

  const total = parseInt(cont.dataset.total, 10);
  let actual  = parseInt(cont.dataset.actual, 10);
  actual = (actual + delta + total) % total;
  cont.dataset.actual = actual;

  cont.querySelectorAll('.marcador-slide').forEach(slide => {
    slide.style.display = parseInt(slide.dataset.index, 10) === actual ? 'flex' : 'none';
  });

  document.querySelectorAll(`.marcador-dot[data-dot-for="${id}"]`).forEach(dot => {
    dot.classList.toggle('activo', parseInt(dot.dataset.index, 10) === actual);
  });
}

function renderFactor(f) {
  let visual = '';
  if      (f.tipo === 'forma')       visual = renderFactorForma(f);
  else if (f.tipo === 'barras')      visual = renderFactorBarras(f);
  else if (f.tipo === 'doble_barra') visual = renderFactorDobleBarra(f);
  else if (f.tipo === 'h2h')         visual = renderFactorH2H(f);
  else if (f.tipo === 'vuelta')      visual = renderFactorVuelta(f);
  else if (f.tipo === 'marcadores')  visual = renderFactorMarcadores(f);

  return `
    <div class="det-card det-card-factor">
      <div class="factor-header">
        <span class="factor-titulo">${f.factor}</span>
        ${badgeImpacto(f.impacto)}
      </div>
      <div class="factor-visual">${visual}</div>
      <div class="factor-interpretacion">${f.interpretacion}</div>
    </div>
  `;
}

/* ── Render análisis completo ────────────────────────── */
function renderAnalisis(p) {
  if (p.analisis && Array.isArray(p.analisis)) {
    return p.analisis.map(renderFactor).join('');
  }

  if (p.razones && !Array.isArray(p.razones)) {
    function renderRazonesEquipo(razones) {
      if (!razones) return '';
      const pros    = (razones.pros    || []).map(t => `<div class="razon-item razon-pro">${t}</div>`).join('');
      const contras = (razones.contras || []).map(t => `<div class="razon-item razon-contra">${t}</div>`).join('');
      return pros + contras;
    }
    return `
      <div class="det-card">
        <div class="det-seccion-titulo">Análisis</div>
        <div class="det-analisis-wrap">
          <div class="det-analisis-equipo">
            <div class="det-analisis-escudo">
              <img src="${p.logo_local}" alt="${p.local}" onerror="this.style.visibility='hidden'">
              <span class="det-analisis-nombre">${p.local}</span>
            </div>
            <div class="det-analisis-razones">${renderRazonesEquipo(p.razones.local)}</div>
          </div>
          <div class="det-analisis-divider"></div>
          <div class="det-analisis-equipo det-analisis-equipo--visit">
            <div class="det-analisis-razones">${renderRazonesEquipo(p.razones.visitante)}</div>
            <div class="det-analisis-escudo">
              <img src="${p.logo_visitante}" alt="${p.visitante}" onerror="this.style.visibility='hidden'">
              <span class="det-analisis-nombre">${p.visitante}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  return `<div class="det-card"><div class="det-analisis-wrap">${
    (p.razones || []).map(r => {
      const esFavor = r.startsWith('✅');
      const texto   = r.replace(/^✅\s*|^⚠️\s*/u, '');
      return `<div class="razon-item ${esFavor ? 'razon-pro' : 'razon-contra'}">${texto}</div>`;
    }).join('')
  }</div></div>`;
}

/* ── Mostrar detalle de partido ──────────────────────── */
function mostrarDetalleHoy(i) {
  const p = partidosHoy[i];

  const pL = (p.prob_local     * 100).toFixed(1);
  const pE = (p.prob_empate    * 100).toFixed(1);
  const pV = (p.prob_visitante * 100).toFixed(1);

  const confianza =
    p.confianza === 'favorable'
      ? ['Proyección favorable', 'conf-alta']
      : p.confianza === 'moderado'
      ? ['Proyección moderado',  'conf-media']
      : ['Proyección ajustado',  'conf-baja'];

  const fase = p.fase
    ? p.fase.replace('liguilla_ida',    'Semifinal · Ida')
             .replace('liguilla_vuelta', 'Semifinal · Vuelta')
    : 'Fase de Grupos';

  contenido.innerHTML = `
    <div id="vista-hoy-detalle">

      <button class="btn-volver-hoy" onclick="volverListaHoy()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        Volver
      </button>

      <div class="det-fase-label">${fase}</div>

      <div class="det-card">
        <div class="det-match">
          <div class="det-equipo">
            <img src="${p.logo_local}" alt="${p.local}" onerror="this.style.visibility='hidden'">
            <span class="det-equipo-nombre">${p.local}</span>
          </div>
          <span class="det-vs">vs</span>
          <div class="det-equipo">
            <img src="${p.logo_visitante}" alt="${p.visitante}" onerror="this.style.visibility='hidden'">
            <span class="det-equipo-nombre">${p.visitante}</span>
          </div>
        </div>
        <div class="det-divider"></div>
        <div class="det-probs">
          <div class="det-seccion-titulo">Probabilidades</div>
          <div class="barra-row">
            <span class="barra-label">${p.local} (Local)</span>
            <div class="barra-track"><div class="barra-fill win" data-w="${pL}"></div></div>
            <span class="barra-pct win">${pL}%</span>
          </div>
          <div class="barra-row">
            <span class="barra-label">Empate</span>
            <div class="barra-track"><div class="barra-fill draw" data-w="${pE}"></div></div>
            <span class="barra-pct draw">${pE}%</span>
          </div>
          <div class="barra-row">
            <span class="barra-label">${p.visitante} (Visitante)</span>
            <div class="barra-track"><div class="barra-fill loss" data-w="${pV}"></div></div>
            <span class="barra-pct loss">${pV}%</span>
          </div>
        </div>
      </div>

      ${renderAnalisis(p)}

      <div class="det-card det-card-pred">
        <div class="det-seccion-titulo">Favorito</div>
        <div class="det-pred-valor">${p.prediccion}</div>
        <span class="det-confianza ${confianza[1]}">${confianza[0]}</span>
      </div>

    </div>
  `;

  window.scrollTo({ top: 0 });

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.querySelectorAll('.barra-fill').forEach(el => {
        el.style.width = el.dataset.w + '%';
      });
      document.querySelectorAll('.factor-barra-fill').forEach(el => {
        el.style.width = el.dataset.w;
      });
    });
  });
}

/* ── Volver a lista ──────────────────────────────────── */
function volverListaHoy() {
  renderHoyLista();
  window.scrollTo({ top: 0 });
}


/* ─── GRUPOS ────────────────────────────────────────────── */

async function cargarGrupos() {
  const [resG, resP] = await Promise.all([
    fetch("mundial/data/grupos.json"),
    fetch("mundial/data/probabilidades_grupos.json"),
  ]);

  const grupos    = await resG.json();
  const probsData = await resP.json();

  /* Lookup: nombre equipo -> { prob_lider, es_favorito } */
  const probMap = {};
  Object.values(probsData.grupos).forEach(g => {
    g.equipos.forEach(eq => {
      probMap[eq.equipo] = {
        prob:     eq.prob_lider,
        favorito: eq.es_favorito,
      };
    });
  });

  function maxProb(equipos) {
    return Math.max(...equipos.map(eq => probMap[eq.equipo]?.prob ?? 0));
  }

  function probClase(p) {
    if (p >= 45) return "prob-alta";
    if (p >= 22) return "prob-media";
    return "prob-baja";
  }

  function renderGrupo(grupo) {
    const equiposOrdenados = [...grupo.equipos].sort((a, b) => a.posicion - b.posicion);
    const maxP = maxProb(equiposOrdenados);
    return `
      <div class="grupo-card">
        <div class="grupo-header">${grupo.grupo}</div>
        <table class="grupo-tabla">
          <thead>
            <tr>
              <th class="th-equipo">Equipo</th>
              <th>Pts</th>
              <th>DG</th>
              <th title="Probabilidad de liderar el grupo" style="text-align:right;padding-right:6px">1°</th>
            </tr>
          </thead>
          <tbody>
            ${equiposOrdenados.map(eq => {
              const dato     = probMap[eq.equipo];
              const prob     = dato?.prob ?? null;
              const favorito = dato?.favorito ?? false;
              const barW     = prob !== null && maxP > 0 ? Math.round((prob / maxP) * 100) : 0;
              const cls      = prob !== null ? probClase(prob) : "prob-baja";
              const label    = prob !== null ? `${prob}%` : "—";
              return `
                <tr class="${favorito ? "fila-favorito" : ""}">
                  <td class="equipo-cell">
                    <img src="${eq.escudo}" alt="${eq.equipo}" class="escudo-equipo">
                    <span class="equipo-abr">${eq.abreviacion}</span>
                  </td>
                  <td>${eq.puntos}</td>
                  <td>${eq.diferencia_goles}</td>
                  <td class="prob-cell">
                    <div class="prob-inner">
                      <div class="prob-bar-bg">
                        <div class="prob-bar-fill ${cls}" style="width:${barW}%"></div>
                      </div>
                      <span class="prob-val ${cls}">${label}</span>
                    </div>
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  /* Dividir grupos: primeros 6 izquierda, últimos 6 derecha */
  const izquierda = grupos.slice(0, 6);   // A B C D E F
  const derecha   = grupos.slice(6, 12);  // G H I J K L

  /* Construir filas: 2 izq + [logo en fila 1] + 2 der, repetido 3 veces */
  let filas = "";
  for (let i = 0; i < 3; i++) {
    filas += renderGrupo(izquierda[i * 2]);
    filas += renderGrupo(izquierda[i * 2 + 1]);
    if (i === 0) {
      filas += `
        <div class="grupos-logo-center">
          <img src="assets/mundial-2026.png" alt="Logo Mundial 2026">
        </div>
      `;
    }
    filas += renderGrupo(derecha[i * 2]);
    filas += renderGrupo(derecha[i * 2 + 1]);
  }

  contenido.innerHTML = `<div class="grupos-grid">${filas}</div>`;
}


/* ─── TABLA GENERAL ─────────────────────────────────────── */

async function cargarTabla() {
  const res   = await fetch("mundial/data/tabla.json");
  const tabla = await res.json();

  function ordenar(a, b) {
    if (b.puntos !== a.puntos)                     return b.puntos - a.puntos;
    if (b.diferencia_goles !== a.diferencia_goles) return b.diferencia_goles - a.diferencia_goles;
    return b.goles_favor - a.goles_favor;
  }

  const primeros = tabla.filter(eq => eq.posicion === 1).sort(ordenar);
  const segundos = tabla.filter(eq => eq.posicion === 2).sort(ordenar);
  const terceros = tabla.filter(eq => eq.posicion === 3).sort(ordenar);
  const cuartos  = tabla.filter(eq => eq.posicion === 4).sort(ordenar);
  const mejoresTerceros = terceros.slice(0, 8).map(eq => eq.equipo);

  function clasificacion(eq) {
    if (eq.posicion === 1 || eq.posicion === 2)               return "estado-verde";
    if (eq.posicion === 3 && mejoresTerceros.includes(eq.equipo)) return "estado-amarillo";
    return "estado-rojo";
  }

  function renderTabla(filas, conSeparadores) {
    return filas.map((eq, i) => {
      let sep = "";
      if (conSeparadores) {
        if (i === primeros.length)                                         sep = "separador-top";
        if (i === primeros.length + segundos.length)                       sep = "separador-top";
        if (i === primeros.length + segundos.length + terceros.length)     sep = "separador-top";
      }
      return `
        <tr class="${sep}">
          <td><div class="estado-linea ${clasificacion(eq)}"></div></td>
          <td class="pos-global">${i + 1}</td>
          <td>
            <div class="equipo-info">
              <img src="${eq.escudo}" class="escudo-tabla">
              <span>${eq.equipo}</span>
            </div>
          </td>
          <td>${eq.puntos}</td>
          <td>${eq.diferencia_goles > 0 ? "+" : ""}${eq.diferencia_goles}</td>
          <td>${eq.goles_favor}</td>
          <td>${eq.goles_contra}</td>
          <td>${eq.grupo.replace("Group ", "")}</td>
          <td>${eq.posicion}</td>
        </tr>
      `;
    }).join("");
  }

  function renderVista(vista) {
    let filas;
    if (vista === "general") {
      filas = [...tabla].sort(ordenar);
    } else {
      filas = [...primeros, ...segundos, ...terceros, ...cuartos];
    }

    const conSep = vista === "grupos";
    document.getElementById("tabla-body").innerHTML = renderTabla(filas, conSep);

    document.querySelectorAll(".toggle-tabla").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.vista === vista);
    });
  }

  contenido.innerHTML = `
    <div class="tabla-toggle-wrap">
      <button class="toggle-tabla active" data-vista="grupos" onclick="window._tablaVista('grupos')">
        Por posición
       </button>
      <button class="toggle-tabla" data-vista="general" onclick="window._tablaVista('general')">
        General
      </button>
     </div>
  
    <div class="tabla-wrap">

      <table class="tabla-general">
        <thead>
          <tr>
            <th></th>
            <th>Pos</th>
            <th>Selección</th>
            <th>Pts</th>
            <th>DG</th>
            <th>GF</th>
            <th>GC</th>
            <th>Grupo</th>
            <th>Lugar</th>
          </tr>
        </thead>
        <tbody id="tabla-body"></tbody>
      </table>
    </div>
  `;

  window._tablaVista = renderVista;
  renderVista("grupos");
}

/* ─── HISTORIAL ─────────────────────────────────────────── */
/* Agrega esto al final de mundial.js                        */
/* Fuente de datos: partidos/mundial.json                    */

// 1. Conectar el tab "historial" en cambiarVista()
// Busca la función cambiarVista y añade este bloque:
//
//   if (vista === "historial") {
//     sec.classList.add("vista-scroll");
//     cargarHistorial();
//   }

// ── Helpers ──────────────────────────────────────────────

let _partidosHistorial = [];

function fmtH(n) {
  return (n * 100).toFixed(1) + '%';
}

function obtenerFavoritoH(p) {
  if (p.prediccion) return p.prediccion;
  const max = Math.max(p.prob_local, p.prob_empate, p.prob_visitante);
  if (max === p.prob_local)     return p.local;
  if (max === p.prob_visitante) return p.visitante;
  return 'Empate';
}

function obtenerPctFavoritoH(p, fav) {
  if (fav === p.local)     return fmtH(p.prob_local);
  if (fav === p.visitante) return fmtH(p.prob_visitante);
  return fmtH(p.prob_empate);
}

function clasificarResultadoH(p) {
  if (!p.resultado) return 'pending';
  const fav = obtenerFavoritoH(p);
  if (fav === p.resultado) return 'acierto';
  const probs = [p.prob_local, p.prob_empate, p.prob_visitante].sort((a, b) => b - a);
  return probs[0] - probs[1] < 0.14 ? 'parcial' : 'fallo';
}

function calcularParidadH(partidos) {
  return partidos.filter(p => {
    const probs = [p.prob_local, p.prob_empate, p.prob_visitante].sort((a, b) => b - a);
    return probs[0] - probs[1] < 0.15;
  }).length;
}

// ── Carga ─────────────────────────────────────────────────

async function cargarHistorial() {
  const sec = document.getElementById('contenidoMundial');

  // Skeleton / loading
  sec.innerHTML = `
    <div class="hist-loading">
      <div class="spinner"></div>
      <span>Cargando historial…</span>
    </div>
  `;

  let partidos = [];
  try {
    const res = await fetch('partidos/mundial.json');
    if (!res.ok) throw new Error('Sin datos');
    const data = await res.json();
    partidos = Array.isArray(data) ? data
             : Array.isArray(data.partidos) ? data.partidos
             : [];
  } catch (e) {
    sec.innerHTML = `
      <div class="hist-vacio">
        <p>No se pudo cargar el historial.</p>
      </div>`;
    return;
  }

  _partidosHistorial = partidos;

  if (!partidos.length) {
    sec.innerHTML = `
      <div class="hist-vacio">
        <p>No hay proyecciones en el historial aún.</p>
      </div>`;
    return;
  }

  // ── Métricas ──
  const conResultado = partidos.filter(p => p.resultado);
  let aciertos = 0, parciales = 0, fallos = 0;
  for (const p of conResultado) {
    const t = clasificarResultadoH(p);
    if (t === 'acierto')      aciertos++;
    else if (t === 'parcial') parciales++;
    else                      fallos++;
  }
  const total    = conResultado.length;
  const efPct    = total ? ((aciertos / total) * 100).toFixed(1) + '%' : '—';
  const paridad  = calcularParidadH(partidos);

  // ── Filas ──
  const filas = partidos.map((p, i) => {
    const fav  = obtenerFavoritoH(p);
    const tipo = clasificarResultadoH(p);
    const tuvo = !!p.resultado;

    const rowClass = tipo === 'acierto' ? 'hist-fila--acierto'
                   : tipo === 'parcial' ? 'hist-fila--parcial'
                   : tipo === 'fallo'   ? 'hist-fila--fallo'
                   : '';

    const resClass = tipo === 'acierto' ? 'res--ok'
                   : tipo === 'parcial' ? 'res--parcial'
                   : tipo === 'fallo'   ? 'res--fail'
                   : 'res--pending';

    return `
      <div class="fila hist-fila ${rowClass}" onclick="abrirModalHistorial(${i})" style="cursor:pointer;">
        <div class="fila-equipo">
          <div class="logos-pair">
            <img src="${p.logo_local}"     alt="${p.local}"     onerror="this.style.display='none'">
            <img src="${p.logo_visitante}" alt="${p.visitante}" onerror="this.style.display='none'">
          </div>
          <span class="fila-nombre">${p.local} <em>vs</em> ${p.visitante}</span>
        </div>
        <span class="fila-pct win">${fmtH(p.prob_local)}</span>
        <span class="fila-pct draw">${fmtH(p.prob_empate)}</span>
        <span class="fila-pct loss">${fmtH(p.prob_visitante)}</span>
        <span class="fila-resultado ${resClass}">
          ${tuvo ? p.resultado : '—'}
        </span>
      </div>
    `;
  }).join('');

  sec.innerHTML = `

    <!-- Resumen métricas -->
    <div class="hist-resumen">
      <div class="hist-dona-wrap" id="histDonaMundial">
        <div class="hist-dona-inner">
          <canvas id="donaChartMundial" aria-label="Distribución de proyecciones"></canvas>
          <div class="hist-dona-centro">
            <span class="hist-dona-num">${total}</span>
            <span class="hist-dona-sub">Proyecciones</span>
          </div>
        </div>
      </div>

      <div class="hist-resumen-derecha">
        <div class="hist-metricas">
          <div class="hist-metrica-card">
            <span class="hist-metrica-val hist-val-win">${aciertos}</span>
            <span class="hist-metrica-lbl">Aciertos</span>
          </div>
          <div class="hist-metrica-card">
            <span class="hist-metrica-val hist-val-parcial">${parciales}</span>
            <span class="hist-metrica-lbl">Ajustados</span>
          </div>
          <div class="hist-metrica-card">
            <span class="hist-metrica-val hist-val-loss">${fallos}</span>
            <span class="hist-metrica-lbl">Fallos</span>
          </div>
        </div>
        <p class="hist-nota-paridad">
          ${paridad} de ${partidos.length} partidos fueron de alta paridad
        </p>
        <div class="hist-dona-leyenda" id="donaLeyendaMundial"></div>
      </div>
    </div>

    <!-- Tabla de partidos -->
    <div class="tabla-header hist-tabla-header">
      <span>Partido</span>
      <span>Local</span>
      <span>Empate</span>
      <span>Visitante</span>
      <span>Resultado</span>
    </div>
    ${filas}

    <!-- Modal -->
    <div class="modal-overlay" id="modalHistorialOverlay" onclick="cerrarModalHistorial(event)">
      <div class="modal-card" id="modalHistorialCard">
        <button class="modal-close" onclick="cerrarModalHistorial()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        <div id="modalHistorialContenido"></div>
      </div>
    </div>
  `;

  // Cargar Chart.js y pintar dona
  if (window.Chart) {
    renderDonaHistorial(aciertos, parciales, fallos, total);
  } else {
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';
    s.onload = () => renderDonaHistorial(aciertos, parciales, fallos, total);
    document.head.appendChild(s);
  }

  // ESC cierra modal
  document.addEventListener('keydown', _histEsc);
}

function _histEsc(e) {
  if (e.key === 'Escape') cerrarModalHistorial();
}

// ── Dona ─────────────────────────────────────────────────

function renderDonaHistorial(aciertos, parciales, fallos, total) {
  const wrap = document.getElementById('histDonaMundial');
  if (!wrap) return;
  wrap.style.opacity = '1';

  document.getElementById('donaLeyendaMundial').innerHTML = `
    <span class="dona-item">
      <span class="dona-dot" style="background:#27ae60;"></span>
      <span class="dona-lbl">Aciertos</span>
      <span class="dona-val">${Math.round(aciertos / total * 100)}%</span>
    </span>
    <span class="dona-item">
      <span class="dona-dot" style="background:#f39c12;"></span>
      <span class="dona-lbl">Ajustados</span>
      <span class="dona-val">${Math.round(parciales / total * 100)}%</span>
    </span>
    <span class="dona-item">
      <span class="dona-dot" style="background:#e74c3c;"></span>
      <span class="dona-lbl">Fallos</span>
      <span class="dona-val">${Math.round(fallos / total * 100)}%</span>
    </span>
  `;

  if (window._donaChartMundial) window._donaChartMundial.destroy();
  window._donaChartMundial = new Chart(
    document.getElementById('donaChartMundial'), {
      type: 'doughnut',
      data: {
        labels: ['Aciertos', 'Ajustados', 'Fallos'],
        datasets: [{
          data: [aciertos, parciales, fallos],
          backgroundColor: ['#27ae60', '#f39c12', '#e74c3c'],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx =>
                ` ${ctx.label}: ${ctx.raw} (${Math.round(ctx.raw / total * 100)}%)`,
            },
          },
        },
      },
    }
  );
}

// ── Modal ─────────────────────────────────────────────────

function abrirModalHistorial(i) {
  const p    = _partidosHistorial[i];
  const fav  = obtenerFavoritoH(p);
  const tipo = clasificarResultadoH(p);
  const tuvo = !!p.resultado;
  const ok   = tuvo && fav === p.resultado;

  const veredictoClass =
    tipo === 'acierto' ? 'veredicto--ok'
  : tipo === 'parcial' ? 'veredicto--parcial'
  : tipo === 'fallo'   ? 'veredicto--fail'
  : 'veredicto--pending';

  const veredictoTexto =
    tipo === 'acierto' ? 'Acierto'
  : tipo === 'parcial' ? 'Acierto parcial'
  : tipo === 'fallo'   ? 'Fallo'
  : 'Sin resultado';

  const veredictoIcon = !tuvo ? '' : ok
    ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`
    : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

  document.getElementById('modalHistorialContenido').innerHTML = `
    <div class="modal-equipos">
      <div class="modal-equipo">
        <img src="${p.logo_local}" alt="${p.local}" onerror="this.style.display='none'">
        <span>${p.local}</span>
      </div>
      <span class="modal-vs">vs</span>
      <div class="modal-equipo">
        <img src="${p.logo_visitante}" alt="${p.visitante}" onerror="this.style.display='none'">
        <span>${p.visitante}</span>
      </div>
    </div>

    <div class="modal-detalle">
      <div class="modal-fila">
        <span class="modal-lbl">Proyección</span>
        <span class="modal-val">${fav}</span>
      </div>
      <div class="modal-fila">
        <span class="modal-lbl">Confianza</span>
        <span class="modal-val">${p.confianza || '—'}</span>
      </div>
      <div class="modal-fila1">
        <span class="modal-lbl">Probabilidades</span>
        <span class="modal-val modal-probs">
          <span class="prob-chip win">${p.local} ${fmtH(p.prob_local)}</span>
          <span class="prob-chip draw">Empate ${fmtH(p.prob_empate)}</span>
          <span class="prob-chip loss">${p.visitante} ${fmtH(p.prob_visitante)}</span>
        </span>
      </div>
      <div class="modal-fila">
        <span class="modal-lbl">Resultado</span>
        <span class="modal-val">${tuvo ? p.resultado : '—'}</span>
      </div>
    </div>

    <div class="veredicto ${veredictoClass}">
      ${veredictoIcon}
      <span>${veredictoTexto}</span>
    </div>
  `;

  document.getElementById('modalHistorialOverlay').classList.add('modal--visible');
}

function cerrarModalHistorial(e) {
  if (e && e.target !== document.getElementById('modalHistorialOverlay')
       && !e.target.closest('.modal-close')) return;
  document.getElementById('modalHistorialOverlay')?.classList.remove('modal--visible');
}
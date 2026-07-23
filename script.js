let partidos = [];

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

/* ── Determina qué JSON y qué etiqueta usar según ?tipo= en la URL ── */
const CONFIG_TORNEOS = {
  temporada: { json: 'partidos.json',      label: 'Análisis Semanal' },
  progol:    { json: 'progol.json',        label: 'Progol' },
  media:     { json: 'pro-media.json',     label: 'Progol Media Semana' },
  revancha:  { json: 'pro-revancha.json',  label: 'Progol Revancha' }
};

const tipoActual = new URLSearchParams(window.location.search).get('tipo') || 'temporada';
const config      = CONFIG_TORNEOS[tipoActual] || CONFIG_TORNEOS.temporada;

const ARCHIVO_JSON = config.json;
const LABEL_LISTA  = config.label;

/* ── Carga de datos ──────────────────────────────────── */
setText('headerLabel', LABEL_LISTA);

fetch(ARCHIVO_JSON + '?v=' + Date.now())
  .then(r => r.json())
  .then(data => {
    partidos = data;
    setStyle('loading', 'display', 'none');
    renderLista();
  });

/* ── Render lista ────────────────────────────────────── */
function renderLista() {
  const contenedor = document.getElementById('contenedor');
  if (!contenedor) return;
  contenedor.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'tabla-header';
  header.innerHTML = `
    <span>Partido</span>
    <span>Local</span>
    <span>Empate</span>
    <span>Visitante</span>
    <span>Favorito</span>
  `;
  contenedor.appendChild(header);

  partidos.forEach((p, i) => {
    const fila = document.createElement('div');
    fila.className = 'fila';
    fila.onclick = () => mostrarDetalle(i);

    const pL = (p.prob_local     * 100).toFixed(1);
    const pE = (p.prob_empate    * 100).toFixed(1);
    const pV = (p.prob_visitante * 100).toFixed(1);

    fila.innerHTML = `
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
    `;
    contenedor.appendChild(fila);
  });
}

/* ── Helpers de factores ─────────────────────────────── */

function badgeImpacto(impacto) {
  const cls = impacto === 'alto' ? 'impacto-alto'
            : impacto === 'medio' ? 'impacto-medio'
            : 'impacto-bajo';
  const txt = impacto === 'alto' ? 'Impacto alto'
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
  const pGFL = Math.round((f.local.goles_favor    / maxGF) * 100);
  const pGFV = Math.round((f.visitante.goles_favor / maxGF) * 100);
  const pGCL = Math.round((f.local.goles_contra    / maxGC) * 100);
  const pGCV = Math.round((f.visitante.goles_contra / maxGC) * 100);
  const claseGFL = f.local.goles_favor    >= f.visitante.goles_favor    ? 'barra-win' : 'barra-loss';
  const claseGFV = f.visitante.goles_favor >= f.local.goles_favor       ? 'barra-win' : 'barra-loss';
  const claseGCL = f.local.goles_contra   <= f.visitante.goles_contra   ? 'barra-win' : 'barra-loss';
  const claseGCV = f.visitante.goles_contra <= f.local.goles_contra      ? 'barra-win' : 'barra-loss';

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

/* ── Carrusel de marcadores probables ────────────────── */
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

/* ── Mostrar detalle ─────────────────────────────────── */
function mostrarDetalle(i) {
  const p = partidos[i];

  const pL = (p.prob_local     * 100).toFixed(1);
  const pE = (p.prob_empate    * 100).toFixed(1);
  const pV = (p.prob_visitante * 100).toFixed(1);

  const confianza =
    p.confianza === 'favorable'
      ? ['Proyección favorable', 'conf-alta']
      : p.confianza === 'moderado'
      ? ['Proyección moderado',  'conf-media']
      : ['Proyección ajustado',  'conf-baja'];

  setHTML('detalleContenido', `
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
  `);

  addClass('vista-lista',   'hidden');
  removeClass('vista-detalle', 'hidden');

  setStyle('btnBack',   'display', 'flex');
  setStyle('btnInicio', 'display', 'none');
  setStyle('badgeWrap', 'display', 'none');

  const fase = p.fase
    ? p.fase.replace('liguilla_ida',    'Semifinal · Ida')
            .replace('liguilla_vuelta', 'Semifinal · Vuelta')
    : 'Jornada Regular';
  setText('headerLabel', fase);
  setText('headerTitle', p.local + ' · ' + p.visitante);

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
function mostrarLista() {
  addClass('vista-detalle', 'hidden');
  removeClass('vista-lista', 'hidden');

  setStyle('btnBack',   'display', 'none');
  setStyle('btnInicio', 'display', 'flex');
  setStyle('badgeWrap', 'display', '');

  setText('headerLabel', LABEL_LISTA);
  setText('headerTitle', 'Proyecciones');

  window.scrollTo({ top: 0 });
}
let partidos = [];

/* ── Carga de datos ──────────────────────────────────── */
fetch('partidos.json?v=' + Date.now())
  .then(r => r.json())
  .then(data => {
    partidos = data;
    document.getElementById('loading').style.display = 'none';
    renderLista();
  })

/* ── Render lista ────────────────────────────────────── */
function renderLista() {
  const contenedor = document.getElementById('contenedor');
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

function renderFactor(f) {
  let visual = '';
  if      (f.tipo === 'forma')       visual = renderFactorForma(f);
  else if (f.tipo === 'barras')      visual = renderFactorBarras(f);
  else if (f.tipo === 'doble_barra') visual = renderFactorDobleBarra(f);
  else if (f.tipo === 'h2h')         visual = renderFactorH2H(f);
  else if (f.tipo === 'vuelta')      visual = renderFactorVuelta(f);

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
  /* Formato nuevo: analisis es lista de factores */
  if (p.analisis && Array.isArray(p.analisis)) {
    return p.analisis.map(renderFactor).join('');
  }

  /* Formato legacy: razones objeto {local, visitante} */
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

  /* Formato legacy array */
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
      ? ['Pronóstico favorable', 'conf-alta']
      : p.confianza === 'moderado'
      ? ['Pronóstico moderado',  'conf-media']
      : ['Pronóstico ajustado',  'conf-baja'];

  document.getElementById('detalleContenido').innerHTML = `

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

  `;

  document.getElementById('vista-lista').classList.add('hidden');
  document.getElementById('vista-detalle').classList.remove('hidden');
  document.getElementById('btnBack').style.display = 'flex';
  document.getElementById('headerLabel').textContent = p.fase
    ? p.fase.replace('liguilla_ida',    'Cuartos de Final · Ida')
            .replace('liguilla_vuelta', 'Cuartos de Final · Vuelta')
    : 'Jornada Regular';
  document.getElementById('headerTitle').textContent = p.local + ' · ' + p.visitante;
  document.getElementById('badgeWrap').style.display = 'none';
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
  document.getElementById('vista-detalle').classList.add('hidden');
  document.getElementById('vista-lista').classList.remove('hidden');
  document.getElementById('btnBack').style.display = 'none';
  document.getElementById('headerLabel').textContent = 'Cuartos de Final · Ida';
  document.getElementById('headerTitle').textContent = 'Pronósticos';
  document.getElementById('badgeWrap').style.display = '';
  window.scrollTo({ top: 0 });
}
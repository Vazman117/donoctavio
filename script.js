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

  /* Encabezado de columnas */
  const header = document.createElement('div');
  header.className = 'tabla-header';
  header.innerHTML = `
    <span>Partido</span>
    <span>Local</span>
    <span>Empate</span>
    <span>Visitante</span>
    <span>Predicción</span>
  `;
  contenedor.appendChild(header);

  /* Filas */
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

/* ── Mostrar detalle ─────────────────────────────────── */
function mostrarDetalle(i) {
  const p = partidos[i];

  const pL = (p.prob_local     * 100).toFixed(1);
  const pE = (p.prob_empate    * 100).toFixed(1);
  const pV = (p.prob_visitante * 100).toFixed(1);

  const confianza = p.diferencia > 0.4
    ? ['Alta',  'conf-alta']
    : p.diferencia > 0.2
    ? ['Media', 'conf-media']
    : ['Baja',  'conf-baja'];

  document.getElementById('detalleContenido').innerHTML = `
    <div class="detalle-match">
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

    <div class="det-seccion">
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

    <div class="det-seccion">
      <div class="det-seccion-titulo">Resultado predicho</div>
      <div class="det-resultado">
        <div>
          <div class="det-pred-valor">${p.prediccion}</div>
          <span class="det-confianza ${confianza[1]}">Confianza ${confianza[0]}</span>
        </div>
        <div class="det-meta">
          <span class="det-meta-label">Diferencia</span>
          <span class="det-meta-val">${p.diferencia.toFixed(3)}</span>
        </div>
      </div>
    </div>
  `;

  /* Transición de vistas */
  document.getElementById('vista-lista').classList.add('hidden');
  document.getElementById('vista-detalle').classList.remove('hidden');
  document.getElementById('btnBack').style.display = 'flex';
  document.getElementById('headerLabel').textContent = 'Jornada 16';
  document.getElementById('headerTitle').textContent = p.local + ' · ' + p.visitante;
  document.getElementById('badgeWrap').style.display = 'none';
  window.scrollTo({ top: 0 });

  /* Animar barras */
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.querySelectorAll('.barra-fill').forEach(el => {
        el.style.width = el.dataset.w + '%';
      });
    });
  });
}

/* ── Volver a lista ──────────────────────────────────── */
function mostrarLista() {
  document.getElementById('vista-detalle').classList.add('hidden');
  document.getElementById('vista-lista').classList.remove('hidden');
  document.getElementById('btnBack').style.display = 'none';
  document.getElementById('headerLabel').textContent = 'Jornada 16';
  document.getElementById('headerTitle').textContent = 'Predicciones';
  document.getElementById('badgeWrap').style.display = '';
  window.scrollTo({ top: 0 });
}
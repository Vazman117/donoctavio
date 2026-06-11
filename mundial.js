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
    if (b.puntos !== a.puntos)                    return b.puntos - a.puntos;
    if (b.diferencia_goles !== a.diferencia_goles) return b.diferencia_goles - a.diferencia_goles;
    return b.goles_favor - a.goles_favor;
  }

  const primeros = tabla.filter(eq => eq.posicion === 1).sort(ordenar);
  const segundos = tabla.filter(eq => eq.posicion === 2).sort(ordenar);
  const terceros = tabla.filter(eq => eq.posicion === 3).sort(ordenar);
  const cuartos  = tabla.filter(eq => eq.posicion === 4).sort(ordenar);

  const mejoresTerceros = terceros.slice(0, 8).map(eq => eq.equipo);
  const tablaFinal = [...primeros, ...segundos, ...terceros, ...cuartos];

  contenido.innerHTML = `
    <div class="tabla-wrap">
      <table class="tabla-general">
        <thead>
          <tr>
            <th></th>
            <th>Pos</th>
            <th>Equipo</th>
            <th>Pts</th>
            <th>DG</th>
            <th>GF</th>
            <th>GC</th>
            <th>Grupo</th>
          </tr>
        </thead>
        <tbody>
          ${tablaFinal.map((eq, i) => {
            let estadoClase = "estado-rojo";
            if (eq.posicion === 1 || eq.posicion === 2) {
              estadoClase = "estado-verde";
            } else if (eq.posicion === 3 && mejoresTerceros.includes(eq.equipo)) {
              estadoClase = "estado-amarillo";
            }

            let sep = "";
            if (i === primeros.length)                                     sep = "separador-top";
            if (i === primeros.length + segundos.length)                   sep = "separador-top";
            if (i === primeros.length + segundos.length + terceros.length) sep = "separador-top";

            return `
              <tr class="${sep}">
                <td><div class="estado-linea ${estadoClase}"></div></td>
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
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}
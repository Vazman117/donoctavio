const contenido = document.getElementById("contenidoMundial");
const tabs = document.querySelectorAll(".tab-btn");

tabs.forEach(btn => {
  btn.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    cambiarVista(btn.dataset.tab);
  });
});

cambiarVista("grupos");

async function cambiarVista(vista) {
  const sec = document.getElementById("contenidoMundial");
  // Grupos: sin scroll. Tabla y Hoy: con scroll.
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

async function cargarHoy() {
  const res      = await fetch("mundial/data/hoy.json");
  const partidos = await res.json();

  contenido.innerHTML = `
    <div class="vista-header"><h2>Partidos de Hoy</h2></div>
    <div class="partidos-grid">
      ${partidos.map(p => `
        <div class="partido-card">
          <div class="equipos">
            <span>${p.local}</span>
            <span class="vs">vs</span>
            <span>${p.visitante}</span>
          </div>
          <div class="probabilidades">
            <div><small>${p.local}</small><strong>${p.probLocal}%</strong></div>
            <div><small>Empate</small><strong>${p.empate}%</strong></div>
            <div><small>${p.visitante}</small><strong>${p.probVisitante}%</strong></div>
          </div>
        </div>
      `).join("")}
    </div>
  `;
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
        prob:      eq.prob_lider,
        favorito:  eq.es_favorito,
      };
    });
  });

  /* Valor máximo de prob_lider dentro de cada grupo para escalar barras */
  function maxProb(equipos) {
    return Math.max(...equipos.map(eq => probMap[eq.equipo]?.prob ?? 0));
  }

  function probClase(p) {
    if (p >= 45) return "prob-alta";
    if (p >= 22) return "prob-media";
    return "prob-baja";
  }

  contenido.innerHTML = `
    <div class="grupos-grid">
      ${grupos.map(grupo => {

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
                  const barW     = prob !== null && maxP > 0
                    ? Math.round((prob / maxP) * 100)
                    : 0;
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
      }).join("")}
    </div>
  `;
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
            <th>Grupo</th>
            <th>Pts</th>
            <th>DG</th>
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
            if (i === primeros.length)                                   sep = "separador-top";
            if (i === primeros.length + segundos.length)                 sep = "separador-top";
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
                <td>${eq.grupo.replace("Group ", "")}</td>
                <td>${eq.puntos}</td>
                <td>${eq.diferencia_goles > 0 ? "+" : ""}${eq.diferencia_goles}</td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}
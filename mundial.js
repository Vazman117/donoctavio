const contenido = document.getElementById("contenidoMundial");

const tabs = document.querySelectorAll(".tab-btn");

tabs.forEach(btn => {

  btn.addEventListener("click", () => {

    tabs.forEach(tab => tab.classList.remove("active"));

    btn.classList.add("active");

    const vista = btn.dataset.tab;

    cambiarVista(vista);

  });

});


// VISTA INICIAL
cambiarVista("grupos");


// CONTROLADOR
async function cambiarVista(vista){

  if(vista === "hoy"){
    cargarHoy();
  }

  if(vista === "grupos"){
    cargarGrupos();
  }

  if(vista === "tabla"){
    cargarTabla();
  }

}


// =====================
// HOY
// =====================

async function cargarHoy(){

  const res = await fetch("mundial/data/hoy.json");

  const partidos = await res.json();

  contenido.innerHTML = `

    <div class="vista-header">
      <h2>Partidos de Hoy</h2>
    </div>

    <div class="partidos-grid">

      ${partidos.map(partido => `

        <div class="partido-card">

          <div class="equipos">

            <span>${partido.local}</span>

            <span class="vs">vs</span>

            <span>${partido.visitante}</span>

          </div>

          <div class="probabilidades">

            <div>
              <small>${partido.local}</small>
              <strong>${partido.probLocal}%</strong>
            </div>

            <div>
              <small>Empate</small>
              <strong>${partido.empate}%</strong>
            </div>

            <div>
              <small>${partido.visitante}</small>
              <strong>${partido.probVisitante}%</strong>
            </div>

          </div>

        </div>

      `).join("")}

    </div>

  `;

}


// =====================
// GRUPOS
// =====================

async function cargarGrupos(){

  const res = await fetch("mundial/data/grupos.json");

  const grupos = await res.json();

  contenido.innerHTML = `

    <div class="grupos-grid">

      ${grupos.map(grupo => {

        // ORDENAR POR POSICION
        const equiposOrdenados = grupo.equipos.sort(
          (a,b) => a.posicion - b.posicion
        );

        return `

          <div class="grupo-card">

            <h3>${grupo.grupo}</h3>

            <table class="grupo-tabla">

              <thead>
                <tr>
                  <th>#</th>
                  <th>Equipo</th>
                  <th>Pts</th>
                  <th>DG</th>
                </tr>
              </thead>

              <tbody>

                ${equiposOrdenados.map(eq => `

                  <tr>

                    <td>${eq.posicion}</td>

                    <td class="equipo-cell">

                      <img 
                        src="${eq.escudo}" 
                        alt="${eq.equipo}"
                        class="escudo-equipo"
                      >

                      <span>${eq.abreviacion}</span>

                    </td>

                    <td>${eq.puntos}</td>

                    <td>${eq.diferencia_goles}</td>

                  </tr>

                `).join("")}

              </tbody>

            </table>

          </div>

        `;

      }).join("")}

    </div>

  `;

}


// =====================
// TABLA GENERAL
// =====================

async function cargarTabla(){

  const res = await fetch("mundial/data/tabla.json");

  const tabla = await res.json();

  // FUNCION ORDEN
  function ordenar(a,b){

    if(b.puntos !== a.puntos){
      return b.puntos - a.puntos;
    }

    if(b.diferencia_goles !== a.diferencia_goles){
      return b.diferencia_goles - a.diferencia_goles;
    }

    return b.goles_favor - a.goles_favor;
  }

  // SEPARAR
  const primeros = tabla
    .filter(eq => eq.posicion === 1)
    .sort(ordenar);

  const segundos = tabla
    .filter(eq => eq.posicion === 2)
    .sort(ordenar);

  const terceros = tabla
    .filter(eq => eq.posicion === 3)
    .sort(ordenar);

  const cuartos = tabla
    .filter(eq => eq.posicion === 4)
    .sort(ordenar);

  // MEJORES TERCEROS
  const mejoresTerceros = terceros
    .slice(0,8)
    .map(eq => eq.equipo);

  // TABLA GLOBAL
  const tablaFinal = [
    ...primeros,
    ...segundos,
    ...terceros,
    ...cuartos
  ];

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

          ${tablaFinal.map((eq,index) => {

            let estadoClase = "";

            // CLASIFICADOS
            if(eq.posicion === 1 || eq.posicion === 2){
              estadoClase = "estado-verde";
            }

            // TERCEROS
            else if(eq.posicion === 3){

              if(mejoresTerceros.includes(eq.equipo)){
                estadoClase = "estado-amarillo";
              }else{
                estadoClase = "estado-rojo";
              }

            }

            // CUARTOS
            else{
              estadoClase = "estado-rojo";
            }

            // SEPARADORES
            let separador = "";

            if(index === primeros.length){
              separador = "separador-top";
            }

            if(index === primeros.length + segundos.length){
              separador = "separador-top";
            }

            if(
              index ===
              primeros.length +
              segundos.length +
              terceros.length
            ){
              separador = "separador-top";
            }

            return `

              <tr class="${separador}">

                <td>
                  <div class="estado-linea ${estadoClase}"></div>
                </td>

                <td class="pos-global">
                  ${index + 1}
                </td>

                <td>

                  <div class="equipo-info">

                    <img
                      src="${eq.escudo}"
                      class="escudo-tabla"
                    >

                    <span>
                      ${eq.equipo}
                    </span>

                  </div>

                </td>

                <td>${eq.grupo.replace("Group ","")}</td>

                <td>${eq.puntos}</td>

                <td>
                  ${eq.diferencia_goles > 0 ? "+" : ""}
                  ${eq.diferencia_goles}
                </td>

              </tr>

            `;

          }).join("")}

        </tbody>

      </table>

    </div>

  `;

}
/* ------------------------------------------------------------------
   Ficha municipal de avance TIC — Antioquia
   Datos inyectados por render.py en DATOS, GEO e IMG.
   Este archivo no contiene ninguna cifra: solo presentación.

   Modelo de filtros
   -----------------
   Los tres filtros territoriales se encadenan de lo general a lo
   particular: Subregión -> EAT -> Municipio. El ámbito del informe es
   siempre el más específico que esté seleccionado. Cada vista habilita
   solo los filtros que usa y bloquea los demás.
   ------------------------------------------------------------------ */
(function () {
  "use strict";

  var MUN = DATOS.municipios,
      SUB = DATOS.subregiones,
      EAT = DATOS.eats,
      DEP = DATOS.departamento,
      EST = DATOS.etiquetas_estado,
      EATD = DATOS.eat_display;

  var NOMBRES = {};
  MUN.forEach(function (m) { NOMBRES[m.cod] = m.nombre; });

  var COLOR = { teal: "var(--teal)", blue: "var(--blue)", amb: "var(--amb)" };
  var ICONOS = {
    conect: '<path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5.2 12.2a10 10 0 0 1 13.6 0"/><path d="M8.6 15.8a5 5 0 0 1 6.8 0"/><circle cx="12" cy="19.2" r="1.1"/>',
    infra: '<rect x="3" y="4" width="18" height="6.2" rx="2"/><rect x="3" y="13.8" width="18" height="6.2" rx="2"/><path d="M7 7.1h.01M7 16.9h.01"/>',
    gob: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/>',
    mapa: '<path d="M12 21.5s7-6.4 7-11.2A7 7 0 1 0 5 10.3c0 4.8 7 11.2 7 11.2z"/><circle cx="12" cy="10.1" r="2.5"/>',
    salud: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
    cam: '<rect x="3" y="7" width="13" height="10" rx="2"/><path d="M16 11l5-3v8l-5-3"/>',
    fibra: '<path d="M4 18c6 0 6-12 12-12"/><circle cx="4" cy="18" r="1.6"/><circle cx="16" cy="6" r="1.6"/>',
    tabla: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>',
    gente: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.4 6-5.4s6 2.1 6 5.4"/><path d="M16 11.5a3 3 0 1 0 0-6"/>'
  };

  // Tres agrupaciones de componentes definidas por la Dirección.
  var COMPONENTES = [
    { id: "ecosistemas", nombre: "Ecosistemas digitales", icono: "gob" },
    { id: "infraestructura", nombre: "Infraestructura", icono: "infra" },
    { id: "apropiacion", nombre: "Uso y apropiación", icono: "gente" }
  ];

  /* ---------------- formato ---------------- */
  function num(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return Math.round(v).toLocaleString("es-CO");
  }
  function pct(v, dec) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v * 100).toFixed(dec === undefined ? 0 : dec).replace(".", ",") + "%";
  }
  function si(v) { return v ? "Sí" : "No"; }
  function estado(v) { return EST[v] || "Sin dato"; }
  function eatNombre(e) { return EATD[e] || e; }
  function ico(k) {
    return '<svg class="ic" width="15" height="15" viewBox="0 0 24 24">' +
           (ICONOS[k] || "") + "</svg>";
  }
  function barra(f, tono) {
    return '<span class="balbg"><span class="bal' + (tono ? " " + tono : "") +
           '" style="width:' + Math.round((f || 0) * 56) + 'px"></span></span>';
  }
  function tile(valor, etiqueta, color, apagado) {
    return '<div class="tw"><div class="card"><div class="v' +
      (apagado ? " sd" : "") + '" style="color:' + color + '">' + valor +
      '</div><div class="l">' + etiqueta + "</div></div></div>";
  }
  function tiles(lista) { return '<div class="tiles">' + lista.join("") + "</div>"; }
  function seccion(titulo, icono, color, fondo, interior) {
    return '<div class="sec"><div class="sech" style="background:' + fondo +
      ";color:" + color + ";border-left:4px solid " + color + '">' +
      ico(icono) + titulo + "</div>" + interior + "</div>";
  }
  function celdas(vals) {
    return vals.map(function (v, i) {
      return "<td" + (i ? ' class="n"' : "") + ">" + v + "</td>";
    }).join("");
  }
  function tabla(encabezados, filas, pie) {
    var th = encabezados.map(function (h) {
      return "<th" + (h.n ? ' class="n"' : "") + ">" + h.t + "</th>";
    }).join("");
    return '<div class="tbl"><table><thead><tr>' + th + "</tr></thead><tbody>" +
      filas.join("") + (pie || "") + "</tbody></table></div>";
  }
  function nota(texto) { return '<div class="nota">' + texto + "</div>"; }

  // Participación: cada fila sobre el total del ámbito.
  function tablaReparto(titulo, filas, tono, conAvance, etiquetaTotal) {
    if (!filas || !filas.length) return "";
    var total = 0, conectadas = 0, sinDato = 0;
    var cuerpo = filas.map(function (f) {
      total += f.total;
      if (conAvance) { conectadas += f.conectadas; sinDato += f.sin_dato; }
      var base = [f.nombre, num(f.total), barra(f.part, tono) + pct(f.part)];
      if (conAvance) base = base.concat([num(f.conectadas), num(f.sin_dato)]);
      return "<tr>" + celdas(base) + "</tr>";
    }).join("");
    var enc = [{ t: titulo }, { t: "Total", n: true }, { t: "Participación", n: true }];
    if (conAvance) enc = enc.concat([{ t: "Con tecnología", n: true }, { t: "Sin dato", n: true }]);
    var pieVals = [etiquetaTotal || "Total", num(total), "100%"];
    if (conAvance) pieVals = pieVals.concat([num(conectadas), num(sinDato)]);
    return tabla(enc, [cuerpo], '<tr class="tot">' + celdas(pieVals) + "</tr>");
  }

  /* ---------------- mapa ---------------- */
  function mapaGrupo(codigos, principal) {
    var dentro = {};
    (codigos || []).forEach(function (c) { dentro[c] = true; });
    var celdasSvg = Object.keys(GEO.paths).map(function (c) {
      var cls = (c === principal) ? " sel" : (dentro[c] ? " grp" : "");
      return '<path class="mp' + cls + '" d="' + GEO.paths[c] + '"><title>' +
        (NOMBRES[c] || c) + "</title></path>";
    }).join("");
    return '<svg viewBox="0 0 ' + GEO.W + " " + GEO.H +
      '" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mapa de Antioquia">' +
      celdasSvg + '<path class="mout" d="' + GEO.outline + '"/></svg>';
  }

  /* ---------------- ámbito ---------------- */
  function valor(id) { return document.getElementById(id).value; }

  // En la vista Zona el municipio no participa: el ámbito es siempre el EAT,
  // la subregión o el departamento.
  function ambito(ignorarMunicipio) {
    var cod = ignorarMunicipio ? "" : valor("fmun"),
        fe = valor("feat"), fs = valor("fsub");
    if (cod) {
      var m = MUN.filter(function (x) { return x.cod === cod; })[0];
      if (m) return { tipo: "mun", nombre: m.nombre, datos: m, miembros: [m],
                      detalle: "Código DANE " + m.cod + " &nbsp;·&nbsp; Subregión " +
                               m.subregion + " &nbsp;·&nbsp; " + eatNombre(m.eat) };
    }
    if (fe) {
      var mm = MUN.filter(function (x) { return eatNombre(x.eat) === fe; });
      var clave = mm.length ? mm[0].eat : null;
      return { tipo: "eat", nombre: fe, datos: EAT[clave], miembros: mm,
               detalle: "Esquema asociativo territorial &nbsp;·&nbsp; " +
                        mm.length + " municipios" };
    }
    if (fs) {
      var ms = MUN.filter(function (x) { return x.subregion === fs; });
      return { tipo: "sub", nombre: fs, datos: SUB[fs], miembros: ms,
               detalle: "Subregión de Antioquia &nbsp;·&nbsp; " + ms.length +
                        " municipios" };
    }
    return { tipo: "dep", nombre: "Antioquia", datos: DEP, miembros: MUN,
             detalle: "Departamento &nbsp;·&nbsp; 125 municipios" };
  }

  /* ---------------- bloques reutilizables ---------------- */
  function bloqueEducacion(o, esMunicipio) {
    var e = o.educacion;
    return tiles([
      tile(num(e.total), "Sedes educativas", COLOR.teal),
      tile(num(e.conectadas), "Con tecnología", COLOR.teal),
      tile(pct(e.avance), "Avance", COLOR.teal),
      tile(num(e.sin_dato), "Sin dato de conexión", COLOR.teal)
    ]) +
      tablaReparto("Zona de la sede", e.zonas, "", true, "Total de sedes educativas") +
      nota("La sábana solo distingue zona rural y urbana en el programa de la " +
           "Gobernación. Las sedes de MinTIC y las que no tienen programa " +
           "asociado quedan <b>sin clasificar</b>: no es que no tengan zona, es " +
           "que la fuente no la registra.") +
      tablaReparto("Programa", e.programas, "", true, "Total de sedes educativas") +
      tablaReparto("Tecnología de conexión", e.tecnologias, "", false,
                   "Total de sedes educativas") +
      (esMunicipio ? "" :
        tablaReparto("Subprograma", e.subprogramas, "", true,
                     "Total de sedes educativas"));
  }

  function bloqueDatacenter(o) {
    var i = o.infraestructura;
    var sinDiag = i.diagnosticados === 0, sinInv = i.con_inventario === 0;
    return tiles([
      tile(num(i.datacenter_gobernacion), "DataCenter Gobernación", COLOR.blue),
      tile(num(i.datacenter_propio), "DataCenter propio", COLOR.blue),
      tile(num(i.diagnosticados), "Con diagnóstico aplicado", COLOR.blue),
      tile(num(i.zonas_wifi), "Puntos de conectividad", COLOR.blue),
      tile(sinInv ? "Sin registro" : num(i.equipos_total),
           sinInv ? "Unidades entregadas" :
             "Unidades entregadas (suma de " + i.equipos_tipos + " tipos)",
           COLOR.blue, sinInv),
      tile(sinDiag ? "Sin medir" : num(i.ap_internos), "AP internos", COLOR.blue, sinDiag),
      tile(sinDiag ? "Sin medir" : num(i.ap_externos), "AP externos", COLOR.blue, sinDiag),
      tile(sinDiag ? "Sin medir" : num(i.ap_sin_funcionar), "AP sin funcionar", COLOR.blue, sinDiag)
    ]) +
      tablaReparto("Dispositivo del inventario", i.equipos, "blue", false,
                   "Total de unidades entregadas") +
      nota("<b>Unidades entregadas es una sumatoria</b> de la columna CANTIDAD " +
           "del inventario: mezcla unidades de distinta naturaleza, de modo que " +
           "un DataCenter completo pesa lo mismo que un inyector PoE. " +
           "«Sin medir» y «Sin registro» significan que no se ha levantado el " +
           "diagnóstico o el inventario: no son ceros.");
  }

  function bloqueFibra(o) {
    var f = o.fibra;
    return tiles([
      tile(num(f.metros) + " m", "Metros de fibra", COLOR.teal),
      tile(num(f.municipios), "Municipios en el proyecto", COLOR.teal),
      tile(num(f.sin_metros), "Sin metros reportados", COLOR.teal),
      tile(num(f.sin_coordenadas), "Sin coordenadas", COLOR.teal)
    ]) +
      nota("Corresponde al proyecto departamental de fibra óptica. Es " +
           "independiente de que existan sedes conectadas por fibra de otros " +
           "operadores, que se cuentan arriba en tecnología de conexión.");
  }

  function bloqueEntornos(o) {
    var s = o.seguridad;
    return tiles([
      tile(num(s.puntos), "Entornos intervenidos", COLOR.blue),
      tile(num(s.municipios), "Municipios intervenidos", COLOR.blue),
      tile(num(s.sin_coordenadas), "Sin coordenadas", COLOR.blue)
    ]) +
      nota("<b>Cada registro es una placa deportiva intervenida con cámaras e " +
           "iluminación, no una cámara individual.</b> Un municipio con 1 tiene " +
           "un entorno intervenido, que puede tener varias cámaras. La fuente no " +
           "registra cuántas hay por entorno.");
  }

  function bloqueSalud(o) {
    var s = o.salud;
    return tiles([
      tile(num(s.puntos), "Puntos conectados", COLOR.blue),
      tile(num(s.kit_fijo), "Con kit satelital fijo", COLOR.blue),
      tile(num(s.kit_itinerante), "Con unidad itinerante", COLOR.blue),
      tile(num(s.sin_kit), "Sin kit satelital", COLOR.blue)
    ]) +
      tablaReparto("Dotación entregada", s.dotacion, "blue", false,
                   "Total de puntos de salud") +
      nota("Un punto puede tener más de una dotación, por eso las filas no " +
           "suman el total. El <b>kit fijo</b> es la sala de telemedicina del " +
           "hospital; la <b>unidad itinerante</b> es portátil, para atención " +
           "fuera de la sede.");
  }

  function bloqueEcosistemas(o, esMunicipio) {
    if (esMunicipio) {
      var g = o.gobierno;
      return tiles([
        tile(estado(g.estado_peti), "Estado PETI", COLOR.amb),
        tile(estado(g.estado_pamuda), "Estado PAMUDA", COLOR.amb),
        tile(g.madurez, "Ficha de madurez", COLOR.amb)
      ]) +
        tabla([{ t: "Instrumento" }, { t: "Estado", n: true },
               { t: "Puntaje en el eje", n: true }], [
          "<tr>" + celdas(["PETI", estado(g.estado_peti),
            "Sí 100% · En proceso 50% · Sin iniciar 0%"]) + "</tr>",
          "<tr>" + celdas(["PAMUDA", estado(g.estado_pamuda),
            "Sí 100% · En proceso 50% · Sin iniciar 0%"]) + "</tr>",
          "<tr>" + celdas(["Ficha de madurez", g.madurez,
            "No entra en el índice"]) + "</tr>"
        ]) +
        nota("Se usan las columnas ESTADO PETI y ESTADO PAMUDA de la fuente.");
    }
    var g2 = o.gobierno || {};
    function conEtiqueta(filas) {
      return (filas || []).map(function (f) {
        return { nombre: estado(f.nombre), total: f.total, part: f.part };
      });
    }
    return tablaReparto("Estado del PETI", conEtiqueta(g2.peti), "amb", false,
                        "Total de municipios") +
      tablaReparto("Estado del PAMUDA", conEtiqueta(g2.pamuda), "amb", false,
                   "Total de municipios") +
      tablaReparto("Nivel de la ficha de madurez", g2.madurez, "amb", false,
                   "Total de municipios");
  }

  function bloqueApropiacion(o) {
    var a = o.apropiacion;
    var prom = a.promedio_sesiones
      ? a.promedio_sesiones.toFixed(1).replace(".", ",") : "—";
    return tiles([
      tile(num(a.personas), "Personas formadas", COLOR.amb),
      tile(num(a.comunidad), "Comunidad", COLOR.amb),
      tile(num(a.funcionarios), "Funcionarios", COLOR.amb),
      tile(num(a.actividades), "Actividades de formación", COLOR.amb),
      tile(num(a.acompanados), "Personas capacitadas", COLOR.amb),
      tile(num(a.sesiones), "Sesiones realizadas", COLOR.amb),
      tile(prom, "Sesiones por persona", COLOR.amb),
      tile(num(a.cursos.length), "Cursos distintos", COLOR.amb)
    ]) +
      tablaReparto("Tipo de formación", a.tipos, "amb", false,
                   "Total de actividades") +
      tablaReparto("Modalidad", a.modalidades, "amb", false,
                   "Total de actividades") +
      tablaReparto("Curso · personas alcanzadas", a.cursos, "amb", false,
                   "Total de personas formadas") +
      nota("La tabla de cursos mide <b>personas alcanzadas</b>, no número de " +
           "actividades: un mismo curso puede dictarse varias veces.") +
      tablaReparto("Personas capacitadas por género", a.generos, "amb", false,
                   "Total de personas capacitadas") +
      tablaReparto("Tipo de acompañamiento", a.tipos_acompanamiento, "amb", false,
                   "Total de personas capacitadas") +
      tablaReparto("Cargo de la persona capacitada", a.cargos, "amb", false,
                   "Total de personas capacitadas") +
      nota("<b>Personas capacitadas</b> son las que recibieron acompañamiento " +
           "individual registrado en la hoja CAPACITACIONES, con nombre y cargo. " +
           "Es distinto de <b>personas formadas</b>, que cuenta asistentes a " +
           "charlas, cursos y capacitaciones grupales. Los cargos se muestran " +
           "tal como vienen escritos en la fuente, sin normalizar.");
  }

  /* ---------------- vista FICHA ---------------- */
  function irow(k, v) {
    return '<div class="irow"><span class="il">' + k +
      '</span><span class="iv">' + v + "</span></div>";
  }

  function vistaFicha(m) {
    var e = m.educacion, i = m.infraestructura;
    function programa(nombre) {
      for (var k = 0; k < e.programas.length; k++) {
        if (e.programas[k].nombre === nombre) return e.programas[k];
      }
      return { total: 0 };
    }
    return '<div class="dos"><div class="col mapwrap"><div class="ch">' +
      ico("mapa") + "Ubicación en Antioquia</div>" + mapaGrupo([m.cod], m.cod) +
      '</div><div class="col"><div class="ch">' + ico("tabla") +
      "Ficha municipal</div>" +
      irow("Subregión", m.subregion) +
      irow("EAT", eatNombre(m.eat)) +
      irow("Código DANE", m.cod) +
      irow("Índice de avance", pct(m.indice, 1)) +
      irow("Sedes educativas", num(e.total)) +
      irow("Sedes con tecnología", num(e.conectadas) + " / " + num(e.total)) +
      irow("Puntos de conectividad", num(i.zonas_wifi)) +
      irow("Entornos educativos seguros", num(m.seguridad.puntos)) +
      irow("Puntos de salud", num(m.salud.puntos)) +
      irow("Estado PETI", estado(m.gobierno.estado_peti)) +
      irow("Estado PAMUDA", estado(m.gobierno.estado_pamuda)) +
      irow("Ficha de madurez", m.gobierno.madurez) +
      "</div></div>" +
      seccion("Conectividad · sedes educativas por programa", "conect",
        "var(--teal)", "var(--tealbg)",
        tiles([
          tile(num(e.total), "Sedes educativas", COLOR.teal),
          tile(num(programa("Gobernación").total), "De la Gobernación", COLOR.teal),
          tile(num(programa("MinTIC").total), "De MinTIC", COLOR.teal),
          tile(num(programa("Sin programa").total), "Sin programa asociado", COLOR.teal)
        ]) +
        tablaReparto("Programa", e.programas, "", true, "Total de sedes educativas") +
        nota("La participación indica qué porción de las " + num(e.total) +
             " sedes del municipio corresponde a cada programa.")) +
      seccion("Infraestructura y servicios", "infra", "var(--blue)", "var(--bluebg)",
        tiles([
          tile(si(i.datacenter_gobernacion), "DataCenter Gobernación", COLOR.blue),
          tile(num(i.zonas_wifi), "Puntos de conectividad", COLOR.blue),
          tile(num(m.seguridad.puntos), "Entornos educativos seguros", COLOR.blue),
          tile(num(m.salud.puntos), "Puntos de salud", COLOR.blue)
        ])) +
      seccion("Ecosistemas digitales y apropiación", "gob", "var(--amb)", "var(--ambbg)",
        tiles([
          tile(estado(m.gobierno.estado_peti), "Estado PETI", COLOR.amb),
          tile(estado(m.gobierno.estado_pamuda), "Estado PAMUDA", COLOR.amb),
          tile(m.gobierno.madurez, "Ficha de madurez", COLOR.amb),
          tile(num(m.apropiacion.personas), "Personas formadas", COLOR.amb)
        ]) +
        tiles([
          tile(num(m.apropiacion.acompanados), "Personas capacitadas", COLOR.amb),
          tile(num(m.apropiacion.sesiones), "Sesiones de acompañamiento", COLOR.amb),
          tile(num(m.apropiacion.actividades), "Actividades de formación", COLOR.amb),
          tile(num(m.apropiacion.comunidad), "De comunidad", COLOR.amb)
        ])) +
      '<div class="ft">Índice de avance ' + pct(m.indice, 1) +
      " · promedio simple de los siete ejes aplicables. Promedio de la subregión " +
      pct(SUB[m.subregion].indice, 1) + " y del departamento " + pct(DEP.indice, 1) +
      ". El detalle de cada dato está en la vista Componentes.</div>";
  }

  /* ---------------- vista ZONA ---------------- */
  function tablaMunicipios(miembros) {
    var filas = miembros.slice().sort(function (a, b) {
      return a.nombre.localeCompare(b.nombre, "es");
    }).map(function (m) {
      var e = m.educacion;
      return "<tr>" + celdas([
        m.nombre,
        e.total ? num(e.conectadas) + " / " + num(e.total) : "—",
        e.total ? pct(e.avance) : "n/a",
        m.infraestructura.datacenter_gobernacion ? "Sí" : "—",
        num(m.infraestructura.zonas_wifi),
        num(m.seguridad.puntos),
        num(m.salud.puntos),
        estado(m.gobierno.estado_peti),
        estado(m.gobierno.estado_pamuda),
        pct(m.indice)
      ]) + "</tr>";
    });
    return tabla([{ t: "Municipio" }, { t: "Sedes conectadas / total", n: true },
                  { t: "% avance", n: true }, { t: "DataCenter", n: true },
                  { t: "Puntos de conectividad", n: true },
                  { t: "Entornos seguros", n: true },
                  { t: "Puntos de salud", n: true }, { t: "PETI", n: true },
                  { t: "PAMUDA", n: true }, { t: "Índice", n: true }], filas);
  }

  function vistaZona(a) {
    var o = a.datos, e = o.educacion;
    return '<div class="dos"><div class="col mapwrap"><div class="ch">' +
      ico("mapa") + a.nombre + "</div>" +
      mapaGrupo(a.miembros.map(function (m) { return m.cod; }), null) +
      '</div><div class="col"><div class="ch">' + ico("tabla") +
      "Resumen de la zona</div>" +
      irow("Municipios", num(a.miembros.length)) +
      irow("Índice de avance promedio", pct(o.indice, 1)) +
      irow("Sedes educativas", num(e.total)) +
      irow("Sedes con tecnología", num(e.conectadas) + " / " + num(e.total)) +
      irow("Avance educativo", pct(e.avance)) +
      irow("DataCenter Gobernación", num(o.infraestructura.datacenter_gobernacion)) +
      irow("Puntos de conectividad", num(o.infraestructura.zonas_wifi)) +
      irow("Entornos educativos seguros", num(o.seguridad.puntos)) +
      irow("Puntos de salud", num(o.salud.puntos)) +
      irow("Metros de fibra", num(o.fibra.metros)) +
      irow("Personas formadas", num(o.apropiacion.personas)) +
      "</div></div>" +
      seccion("Municipios de la zona", "tabla", "var(--teal)", "var(--tealbg)",
        tablaMunicipios(a.miembros) +
        nota("«n/a» en avance educativo son los municipios certificados en " +
             "educación: no dependen de la Secretaría departamental y por eso " +
             "no tienen sedes en esta base.")) +
      seccion("Conectividad de sedes educativas", "conect", "var(--teal)",
        "var(--tealbg)", bloqueEducacion(o, false)) +
      seccion("Ecosistemas digitales", "gob", "var(--amb)", "var(--ambbg)",
        bloqueEcosistemas(o, false)) +
      '<div class="ft">Fuente: sábana única del visor. La conformación ' +
      "territorial proviene de la hoja Municipios. Puede consultar la " +
      "información oficial de cada zona en la página de la " +
      '<a href="' + DATOS.enlace_gobernacion + '" target="_blank" rel="noopener">' +
      "Gobernación de Antioquia</a>.</div>";
  }

  /* ---------------- vista COMPONENTES ---------------- */
  function vistaComponente(a) {
    var o = a.datos, esMun = a.tipo === "mun";
    var id = valor("fcomp") || "infraestructura";
    var comp = COMPONENTES.filter(function (c) { return c.id === id; })[0];
    var cuerpo;

    if (id === "ecosistemas") {
      cuerpo = seccion("PETI, PAMUDA y ficha de madurez", "gob", "var(--amb)",
                       "var(--ambbg)", bloqueEcosistemas(o, esMun));
    } else if (id === "apropiacion") {
      cuerpo = seccion("Formación y acompañamiento", "gente", "var(--amb)",
                       "var(--ambbg)", bloqueApropiacion(o));
    } else {
      cuerpo =
        seccion("Conectividad de sedes educativas", "conect", "var(--teal)",
                "var(--tealbg)", bloqueEducacion(o, esMun)) +
        seccion("DataCenter y puntos de conectividad", "infra", "var(--blue)",
                "var(--bluebg)", bloqueDatacenter(o)) +
        seccion("Fibra óptica", "fibra", "var(--teal)", "var(--tealbg)",
                bloqueFibra(o)) +
        seccion("Entornos educativos seguros", "cam", "var(--blue)",
                "var(--bluebg)", bloqueEntornos(o)) +
        seccion("Salud conectada", "salud", "var(--blue)", "var(--bluebg)",
                bloqueSalud(o));
    }

    return '<div class="card2"><div class="ch">' + ico(comp.icono) +
      comp.nombre + " · " + a.nombre + "</div>" +
      '<div class="ambtxt">' + a.detalle + "</div></div>" + cuerpo +
      '<div class="ft">Componente: ' + comp.nombre + ". Ámbito: " + a.nombre +
      ". Fuente: sábana única del visor; las cifras se recalculan desde el " +
      "Excel en cada construcción del informe.</div>";
  }

  /* ---------------- render ---------------- */
  function pintar(titulo, meta, sub, cuerpo) {
    document.getElementById("informe").innerHTML =
      '<img class="pagebg" src="data:image/jpeg;base64,' + IMG.fondo + '" alt="">' +
      '<div class="pageveil"></div>' +
      '<div class="hd"><img class="hdbg" src="data:image/jpeg;base64,' + IMG.plaza +
      '" alt=""><div class="hdov"></div><div class="hdin"><div class="mun">' +
      titulo + '</div><div class="meta">' + meta + "</div></div></div>" +
      '<div class="brand"><img class="badge" src="data:image/png;base64,' + IMG.logo +
      '" alt="Gobernación de Antioquia"><div class="brandtxt"><b>' + META.entidad +
      "</b><br>" + META.dependencia + '<span class="bdoc">' + sub + "</span></div></div>" +
      cuerpo;
  }

  function render() {
    var vista = window.__vista, a = ambito(vista === "zona");

    if (vista === "ficha") {
      if (a.tipo !== "mun") {
        pintar("Seleccione un municipio",
               "La ficha se emite por municipio",
               "Ficha municipal de avance TIC",
               '<div class="card2">Elija un municipio en el filtro para ver su ' +
               "ficha, o use las vistas Zona y Componentes para trabajar con " +
               "agregados territoriales.</div>");
        return;
      }
      pintar(a.nombre, a.detalle,
             "Ficha municipal de avance TIC · Departamento de Antioquia",
             vistaFicha(a.datos));
      return;
    }

    if (vista === "zona") {
      pintar(a.nombre, a.detalle, "Resumen de zona · avance TIC", vistaZona(a));
      return;
    }

    pintar(a.nombre, a.detalle,
           "Informe por componentes · detalle y origen del dato",
           vistaComponente(a));
  }

  /* ---------------- filtros ---------------- */
  // Repuebla conservando la selección si sigue estando disponible.
  function opciones(el, valores, todos) {
    var previo = el.value;
    el.innerHTML = '<option value="">' + todos + "</option>" +
      valores.map(function (v) {
        return '<option value="' + v.valor + '">' + v.texto + "</option>";
      }).join("");
    if (previo) {
      for (var i = 0; i < el.options.length; i++) {
        if (el.options[i].value === previo) { el.value = previo; return; }
      }
    }
  }

  function eatsDisponibles() {
    var fs = valor("fsub"), vistos = [], salida = [];
    MUN.forEach(function (m) {
      if (fs && m.subregion !== fs) return;
      var e = eatNombre(m.eat);
      if (vistos.indexOf(e) < 0) { vistos.push(e); salida.push({ valor: e, texto: e }); }
    });
    salida.sort(function (x, y) { return x.texto.localeCompare(y.texto, "es"); });
    return salida;
  }

  function municipiosDisponibles() {
    var fs = valor("fsub"), fe = valor("feat");
    return MUN.filter(function (m) {
      return (!fs || m.subregion === fs) && (!fe || eatNombre(m.eat) === fe);
    }).sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); })
      .map(function (m) { return { valor: m.cod, texto: m.nombre }; });
  }

  // Cada vista habilita solo los filtros que usa.
  function aplicarBloqueos() {
    var v = window.__vista;
    var comp = document.getElementById("fcomp"),
        mun = document.getElementById("fmun");
    comp.disabled = (v !== "comp");
    mun.disabled = (v === "zona");
    document.getElementById("lcomp").className = comp.disabled ? "lbl off" : "lbl";
    document.getElementById("lmun").className = mun.disabled ? "lbl off" : "lbl";
    document.getElementById("prev").disabled = mun.disabled;
    document.getElementById("next").disabled = mun.disabled;
    document.getElementById("ayuda").innerHTML =
      v === "ficha"
        ? "La ficha se emite por municipio. Use Subregión y EAT para acotar la lista."
        : v === "zona"
          ? "La zona es el EAT o la subregión seleccionada. Sin filtros muestra todo el departamento."
          : "El componente se calcula sobre el ámbito más específico que tenga seleccionado.";
  }

  // desde: "sub" cuando cambió la subregión, "eat" cuando cambió el EAT.
  // Solo se repuebla lo que está por debajo del filtro que cambió, para no
  // borrar la selección del propio filtro que el usuario acaba de tocar.
  function recargarFiltros(desde) {
    var mun = document.getElementById("fmun"),
        eat = document.getElementById("feat");
    if (desde !== "eat") {
      opciones(eat, eatsDisponibles(), "Todos");
    }
    opciones(mun, municipiosDisponibles(), "Todos");
    if (window.__vista === "ficha" && !mun.value && mun.options.length > 1) {
      mun.selectedIndex = 1;
    }
  }

  function setVista(v) {
    window.__vista = v;
    ["ficha", "zona", "comp"].forEach(function (k) {
      document.getElementById("v" + k).className = (k === v) ? "on" : "";
    });
    aplicarBloqueos();
    var mun = document.getElementById("fmun");
    if (v === "zona") {
      mun.selectedIndex = 0;              // "Todos": la zona no es un municipio
    } else if (!mun.value && mun.options.length > 1) {
      mun.selectedIndex = 1;
    }
    render();
  }

  function mover(paso) {
    var sel = document.getElementById("fmun");
    if (sel.disabled || sel.options.length < 2) return;
    var i = sel.selectedIndex + paso;
    if (i < 1) i = sel.options.length - 1;
    if (i >= sel.options.length) i = 1;
    sel.selectedIndex = i;
    render();
  }

  /* ---------------- exportación ---------------- */
  function exportar() {
    var a = ambito(window.__vista === "zona");
    var enc = ["COD_DANE", "Municipio", "Subregion", "EAT", "Indice (%)",
      "Sedes educativas", "Sedes con tecnologia", "Sedes sin dato",
      "Sedes rurales", "Sedes urbanas", "Sedes sin clasificar",
      "Sedes Gobernacion", "Sedes MinTIC", "Sedes sin programa",
      "Sedes sin georreferenciar", "DataCenter Gobernacion", "DataCenter propio",
      "Diagnostico aplicado", "Unidades entregadas", "AP internos", "AP externos",
      "AP sin funcionar", "Puntos de conectividad", "Entornos educativos seguros",
      "Metros de fibra", "Puntos de salud", "Kit satelital fijo",
      "Unidad itinerante", "Sin kit satelital", "Estado PETI", "Estado PAMUDA",
      "Ficha de madurez", "Personas formadas", "Comunidad", "Funcionarios",
      "Actividades", "Funcionarios acompanados", "Sesiones"];

    function busca(lista, nombre) {
      for (var i = 0; i < (lista || []).length; i++) {
        if (lista[i].nombre === nombre) return lista[i].total;
      }
      return 0;
    }
    function fila(m) {
      var e = m.educacion, i = m.infraestructura, s = m.salud, ap = m.apropiacion;
      return [m.cod, m.nombre, m.subregion, eatNombre(m.eat),
        (m.indice * 100).toFixed(1).replace(".", ","),
        e.total, e.conectadas, e.sin_dato,
        busca(e.zonas, "Rural"), busca(e.zonas, "Urbana"),
        busca(e.zonas, "Sin clasificar"),
        busca(e.programas, "Gobernación"), busca(e.programas, "MinTIC"),
        busca(e.programas, "Sin programa"), e.sin_geo,
        i.datacenter_gobernacion, i.datacenter_propio, i.diagnosticados,
        i.equipos_total, i.ap_internos, i.ap_externos, i.ap_sin_funcionar,
        i.zonas_wifi, m.seguridad.puntos, m.fibra.metros,
        s.puntos, s.kit_fijo, s.kit_itinerante, s.sin_kit,
        estado(m.gobierno.estado_peti), estado(m.gobierno.estado_pamuda),
        m.gobierno.madurez, ap.personas, ap.comunidad, ap.funcionarios,
        ap.actividades, ap.acompanados, ap.sesiones];
    }

    var lineas = [enc.join(";")];
    a.miembros.slice().sort(function (x, y) {
      return x.nombre.localeCompare(y.nombre, "es");
    }).forEach(function (m) {
      lineas.push(fila(m).map(function (v) {
        var t = String(v === null || v === undefined ? "" : v);
        return (t.indexOf(";") >= 0 || t.indexOf('"') >= 0)
          ? '"' + t.replace(/"/g, '""') + '"' : t;
      }).join(";"));
    });

    var texto = "\uFEFF" + lineas.join("\r\n");
    var blob = new Blob([texto], { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var enlace = document.createElement("a");
    var limpio = a.nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^A-Za-z0-9]+/g, "_").toLowerCase();
    enlace.href = url;
    enlace.download = "cifras_tic_" + limpio + ".csv";
    document.body.appendChild(enlace);
    enlace.click();
    document.body.removeChild(enlace);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  /* ---------------- arranque ---------------- */
  window.__vista = "ficha";

  var subs = Object.keys(SUB).sort(function (a, b) {
    return a.localeCompare(b, "es");
  }).map(function (s) { return { valor: s, texto: s }; });
  opciones(document.getElementById("fsub"), subs, "Todas");

  var fcomp = document.getElementById("fcomp");
  fcomp.innerHTML = COMPONENTES.map(function (c) {
    return '<option value="' + c.id + '">' + c.nombre + "</option>";
  }).join("");
  fcomp.value = "infraestructura";

  recargarFiltros("sub");

  document.getElementById("fsub").onchange = function () {
    document.getElementById("feat").value = "";   // el EAT anterior ya no aplica
    document.getElementById("fmun").value = "";
    recargarFiltros("sub"); render();
  };
  document.getElementById("feat").onchange = function () {
    document.getElementById("fmun").value = "";
    recargarFiltros("eat"); render();
  };
  document.getElementById("fmun").onchange = render;
  document.getElementById("fcomp").onchange = render;
  document.getElementById("prev").onclick = function () { mover(-1); };
  document.getElementById("next").onclick = function () { mover(1); };
  document.getElementById("vficha").onclick = function () { setVista("ficha"); };
  document.getElementById("vzona").onclick = function () { setVista("zona"); };
  document.getElementById("vcomp").onclick = function () { setVista("comp"); };
  document.getElementById("exportar").onclick = exportar;
  document.getElementById("imprimir").onclick = function () {
    try {
      if (typeof window.print === "function") {
        setTimeout(function () { window.print(); }, 60);
      } else {
        alert("Su navegador no permite imprimir desde el botón. Use Ctrl+P.");
      }
    } catch (err) {
      alert("No se pudo abrir el diálogo de impresión. Use Ctrl+P (Cmd+P en Mac).");
    }
  };
  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "SELECT") return;
    if (e.key === "ArrowLeft") mover(-1);
    if (e.key === "ArrowRight") mover(1);
  });

  setVista("ficha");
})();

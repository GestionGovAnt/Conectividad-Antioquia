/* ------------------------------------------------------------------
   Observatorio de Conectividad — versión con mapa base (MapLibre GL)
   Requiere internet: la librería y las teselas del mapa base se
   descargan de un CDN. Los datos van embebidos en este archivo.
   ------------------------------------------------------------------ */
(function () {
  "use strict";

  var MUN = DATOS.municipios,
      DEP = DATOS.departamento,
      EJES = DATOS.ejes,
      INV = DATOS.inversion,
      CAPAS = DATOS.capas;

  var VER_INVERSION = DATOS.mostrar_inversion && INV.disponible;

  var POR_COD = {};
  MUN.forEach(function (m) { POR_COD[m.cod] = m; });

  var estado = {
    eje: "educacion",
    metrica: "unidades",
    subregion: "",
    eat: "",
    municipio: null,
    tresD: false,
    tema: "oscuro",
    capas: {}
  };
  CAPAS.forEach(function (c) { estado.capas[c.id] = (c.eje === "educacion"); });
  estado.capas.fibra = false;

  var mapa = null, cargado = false, hover = null, reconstruir = false;
  var pulso = 0;

  /* ---------------- formato ---------------- */
  function num(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return Math.round(v).toLocaleString("es-CO");
  }
  function pct(v, dec) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v * 100).toFixed(dec === undefined ? 0 : dec).replace(".", ",") + "%";
  }
  function plata(v) {
    if (!v) return "$0";
    if (v >= 1e9) return "$" + (v / 1e9).toFixed(1).replace(".", ",") + " mil M";
    if (v >= 1e6) return "$" + (v / 1e6).toFixed(0) + " M";
    return "$" + num(v);
  }
  function ejeActual() {
    for (var i = 0; i < EJES.length; i++) if (EJES[i].id === estado.eje) return EJES[i];
    return EJES[0];
  }
  function colorEje(id) {
    for (var i = 0; i < EJES.length; i++) if (EJES[i].id === id) return EJES[i].color;
    return "#666";
  }
  // En oscuro la escala va del fondo casi negro al color pleno; en claro,
  // del blanco al color. Es el mismo gradiente, invertido.
  function mezcla(hex, f) {
    var r = parseInt(hex.substr(1, 2), 16),
        g = parseInt(hex.substr(3, 2), 16),
        b = parseInt(hex.substr(5, 2), 16),
        base = estado.tema === "oscuro" ? 12 : 248,
        m = function (c) { return Math.round(base - (base - c) * f); };
    return "rgb(" + m(r) + "," + m(g) + "," + m(b) + ")";
  }
  function colorPorTema(id) {
    var claro = { educacion: "#0F6E56", salud: "#B0324B",
                  seguridad: "#185FA5", tic: "#8A5209" };
    var oscuro = { educacion: "#2BE5A0", salud: "#FF4D7E",
                   seguridad: "#38A3FF", tic: "#FFB020" };
    return (estado.tema === "oscuro" ? oscuro : claro)[id] || colorEje(id);
  }

  /* ---------------- métrica ---------------- */
  function campo() {
    return estado.eje + "_" + estado.metrica;
  }
  function valorDe(m) {
    var e = m.ejes[estado.eje];
    if (estado.metrica === "cobertura")
      return e.cobertura === null || e.cobertura === undefined
        ? null : e.cobertura * 100;
    if (estado.metrica === "inversion") return m.inversion[estado.eje];
    return e.unidades;
  }
  function rango() {
    var v = MUN.map(valorDe).filter(function (x) {
      return x !== null && x !== undefined && !isNaN(x);
    });
    if (!v.length) return [0, 1];
    var min = Math.min.apply(null, v), max = Math.max.apply(null, v);
    return [min, max === min ? min + 1 : max];
  }
  function fmtMetrica(v) {
    if (estado.metrica === "cobertura") return (v || 0).toFixed(0) + "%";
    if (estado.metrica === "inversion") return plata(v);
    return num(v);
  }

  /* ---------------- pintura del mapa ---------------- */
  function escalaColor() {
    var eje = ejeActual(), r = rango(), min = r[0], max = r[1];
    var tono = colorPorTema(eje.id), paradas = [];
    [0.12, 0.3, 0.48, 0.66, 0.84, 1].forEach(function (f, i) {
      paradas.push(min + (max - min) * (i / 5));
      paradas.push(mezcla(tono, f));
    });
    return ["interpolate", ["linear"],
            ["coalesce", ["get", campo()], min]].concat(paradas);
  }

  function aplicarEstilo() {
    if (!cargado) return;
    var r = rango();
    mapa.setPaintProperty("municipios-relleno", "fill-color", escalaColor());
    mapa.setPaintProperty("municipios-3d", "fill-extrusion-color", escalaColor());
    mapa.setPaintProperty("municipios-3d", "fill-extrusion-height",
      ["interpolate", ["linear"], ["coalesce", ["get", campo()], 0],
       r[0], 0, r[1], 60000]);
    mapa.setLayoutProperty("municipios-3d", "visibility",
      estado.tresD ? "visible" : "none");
    mapa.setLayoutProperty("municipios-relleno", "visibility",
      estado.tresD ? "none" : "visible");

    listaCapas().forEach(function (c) {
      var vis = estado.capas[c.id] ? "visible" : "none";
      ["capa-" + c.id, "capa-" + c.id + "-cluster",
       "capa-" + c.id + "-cluster-txt", "capa-" + c.id + "-glow"]
        .forEach(function (id) {
          if (mapa.getLayer(id)) mapa.setLayoutProperty(id, "visibility", vis);
        });
    });

    mapa.setFilter("municipios-sel", ["==", ["get", "cod"],
                                      estado.municipio || "__"]);

    // Lo que queda fuera del ámbito se atenúa en vez de ocultarse: sigue
    // dando contexto geográfico sin competir con lo seleccionado.
    var dentro = codigosAmbito();
    var opacidad = (dentro.length === MUN.length)
      ? 0.78
      : ["case", ["in", ["get", "cod"], ["literal", dentro]], 0.85, 0.12];
    mapa.setPaintProperty("municipios-relleno", "fill-opacity", opacidad);
  }

  function registrarEventos() {
      mapa.on("mousemove", "municipios-relleno", function (e) {
        mapa.getCanvas().style.cursor = "pointer";
        var cod = e.features[0].properties.cod;
        if (cod !== hover) {
          hover = cod;
          mapa.setFilter("municipios-hover", ["==", ["get", "cod"], cod]);
        }
      });
      mapa.on("mouseleave", "municipios-relleno", function () {
        mapa.getCanvas().style.cursor = "";
        hover = null;
        mapa.setFilter("municipios-hover", ["==", ["get", "cod"], "__"]);
      });
      mapa.on("click", "municipios-relleno", function (e) {
        var p = e.features[0].properties, eje = ejeActual();
        seleccionar(p.cod, false);
        volarA(p.cod);          // un clic selecciona y acerca
        new maplibregl.Popup({ closeButton: false, offset: 8 })
          .setLngLat(e.lngLat)
          .setHTML("<b>" + p.nombre + "</b><br>" +
            '<span class="pop-l">' + eje.unidad + ":</span> " +
            num(p[estado.eje + "_unidades"]) +
            (p[estado.eje + "_cobertura"] !== null &&
             p[estado.eje + "_cobertura"] !== undefined
              ? '<br><span class="pop-l">Cobertura:</span> ' +
                p[estado.eje + "_cobertura"] + "%" : "") +
            (VER_INVERSION
              ? '<br><span class="pop-l">Inversión:</span> ' +
                plata(p[estado.eje + "_inversion"]) : ""))
          .addTo(mapa);
      });
  }

  function construirMapa() {
    mapa = new maplibregl.Map({
      container: "mapa",
      style: DATOS.estilo_mapa,
      center: [-75.55, 6.95],
      zoom: 6.6,
      maxZoom: 15,
      attributionControl: true
    });
    mapa.addControl(new maplibregl.NavigationControl({ visualizePitch: true }),
                    "bottom-right");
    mapa.addControl(new maplibregl.ScaleControl({ unit: "metric" }),
                    "bottom-right");
    mapa.addControl(new maplibregl.FullscreenControl(), "bottom-right");

    registrarEventos();

    mapa.on("load", function () {
      armarCapas();
      cargado = true;
      aplicarEstilo();
      animarPulso();
      if (estado.municipio) volarA(estado.municipio); else volarAAmbito();
    });
  }

  // Cambiar de mapa base destruye las capas propias: hay que rearmarlas
  // cuando el nuevo estilo termine de cargar. `style.load` es el evento
  // documentado para eso; `styledata` se dispara varias veces y no sirve.
  function cambiarEstiloBase(url) {
    if (!cargado) return;
    mapa.once("style.load", function () {
      armarCapas();
      aplicarEstilo();
    });
    mapa.setStyle(url);
  }

  function armarCapas() {
      mapa.addSource("municipios", { type: "geojson", data: GEOJSON.municipios });

      mapa.addLayer({
        id: "municipios-relleno", type: "fill", source: "municipios",
        paint: { "fill-color": escalaColor(), "fill-opacity": 0.78 }
      });
      mapa.addLayer({
        id: "municipios-3d", type: "fill-extrusion", source: "municipios",
        layout: { visibility: "none" },
        paint: { "fill-extrusion-color": escalaColor(),
                 "fill-extrusion-opacity": 0.85,
                 "fill-extrusion-height": 0 }
      });
      mapa.addLayer({
        id: "municipios-borde", type: "line", source: "municipios",
        paint: { "line-color": "#FFFFFF", "line-width": 0.7 }
      });
      mapa.addLayer({
        id: "municipios-hover", type: "line", source: "municipios",
        filter: ["==", ["get", "cod"], "__"],
        paint: { "line-color": "#0E2A20", "line-width": 1.8 }
      });
      mapa.addLayer({
        id: "municipios-sel", type: "line", source: "municipios",
        filter: ["==", ["get", "cod"], "__"],
        paint: { "line-color": "#0E2A20", "line-width": 3 }
      });

      // Las sedes son casi 4.000 puntos: se agrupan para que se lean.
      CAPAS.forEach(function (c) {
        var color = colorPorTema(c.eje), agrupa = c.puntos.length > 600;
        mapa.addSource("src-" + c.id, {
          type: "geojson", data: GEOJSON.puntos[c.id],
          cluster: agrupa, clusterRadius: 42, clusterMaxZoom: 10
        });
        if (agrupa) {
          mapa.addLayer({
            id: "capa-" + c.id + "-cluster", type: "circle",
            source: "src-" + c.id, filter: ["has", "point_count"],
            paint: {
              "circle-color": color, "circle-opacity": 0.82,
              "circle-stroke-color": "#fff", "circle-stroke-width": 1.4,
              "circle-radius": ["interpolate", ["linear"], ["get", "point_count"],
                                2, 11, 50, 19, 300, 28]
            }
          });
          mapa.addLayer({
            id: "capa-" + c.id + "-cluster-txt", type: "symbol",
            source: "src-" + c.id, filter: ["has", "point_count"],
            layout: { "text-field": ["get", "point_count_abbreviated"],
                      "text-size": 11 },
            paint: { "text-color": "#fff" }
          });
        }
        mapa.addLayer({
          id: "capa-" + c.id, type: "circle", source: "src-" + c.id,
          filter: agrupa ? ["!", ["has", "point_count"]] : ["all"],
          paint: {
            "circle-color": color, "circle-opacity": 0.9,
            "circle-stroke-color": "#fff", "circle-stroke-width": 0.7,
            "circle-radius": ["interpolate", ["linear"], ["zoom"],
                              6, 2.2, 10, 4.5, 14, 8]
          }
        });
      });

      if (GEOJSON.fibra && GEOJSON.fibra.features.length) {
        mapa.addSource("src-fibra", { type: "geojson", data: GEOJSON.fibra });
        mapa.addLayer({
          id: "capa-fibra-glow", type: "line", source: "src-fibra",
          layout: { visibility: "none", "line-cap": "round" },
          paint: { "line-color": colorPorTema("seguridad"), "line-width": 7,
                   "line-opacity": 0.22, "line-blur": 5 }
        });
        mapa.addLayer({
          id: "capa-fibra", type: "line", source: "src-fibra",
          layout: { visibility: "none", "line-cap": "butt" },
          paint: { "line-color": "#BFE6FF", "line-width": 2.1,
                   "line-dasharray": [0, 4, 3] }
        });
      }


  }

  // Latido de los puntos del eje activo: el mapa se siente vivo sin animar
  // cifras, que es donde estos tableros suelen mentir.
  // Recorrido del trazo de fibra: el punteado se desplaza, como si la señal
  // viajara por el cable. Es el patrón de "hormigas en marcha".
  var PASOS_FIBRA = [
    [0, 4, 3], [0.5, 4, 2.5], [1, 4, 2], [1.5, 4, 1.5], [2, 4, 1],
    [2.5, 4, 0.5], [3, 4, 0], [0, 0.5, 3, 3.5], [0, 1, 3, 3],
    [0, 1.5, 3, 2.5], [0, 2, 3, 2], [0, 2.5, 3, 1.5], [0, 3, 3, 1],
    [0, 3.5, 3, 0.5]
  ];
  var pasoFibra = 0, ultimoPaso = 0;

  function animarFibra(ahora) {
    if (!cargado || !estado.capas.fibra || !mapa.getLayer("capa-fibra")) return;
    if (ahora - ultimoPaso < 55) return;
    ultimoPaso = ahora;
    pasoFibra = (pasoFibra + 1) % PASOS_FIBRA.length;
    mapa.setPaintProperty("capa-fibra", "line-dasharray", PASOS_FIBRA[pasoFibra]);
  }

  function animarPulso(ahora) {
    animarFibra(ahora || 0);
    pulso += 0.045;
    if (cargado) {
      var f = 1 + 0.38 * Math.sin(pulso);
      CAPAS.forEach(function (c) {
        var id = "capa-" + c.id;
        if (!mapa.getLayer(id) || !estado.capas[c.id]) return;
        var base = c.eje === estado.eje ? 1 : 0.62;
        mapa.setPaintProperty(id, "circle-radius",
          ["interpolate", ["linear"], ["zoom"],
           6, 2.2 * base * (c.eje === estado.eje ? f : 1),
           10, 4.5 * base * (c.eje === estado.eje ? f : 1),
           14, 8 * base]);
        mapa.setPaintProperty(id, "circle-opacity",
          c.eje === estado.eje ? 0.65 + 0.3 * Math.abs(Math.sin(pulso)) : 0.75);
      });
    }
    requestAnimationFrame(animarPulso);
  }

  /* ---------------- panel ---------------- */
  function kpi(k, v) {
    return '<div class="kpi"><span class="k">' + k + '</span><span class="v">' +
      v + "</span></div>";
  }
  function filaRep(f, color, fmt) {
    return '<div class="fila-rep"><span class="n">' + f.nombre +
      '</span><span class="b"><span style="width:' +
      Math.round((f.part || 0) * 64) + "px;background:" + color +
      '"></span></span><span class="v">' + (fmt || num)(f.total) + "</span></div>";
  }

  // Ámbito: el más específico que esté seleccionado.
  function ambito() {
    if (estado.municipio && POR_COD[estado.municipio]) {
      var m = POR_COD[estado.municipio];
      return { tipo: "mun", nombre: m.nombre, datos: m, miembros: [m],
               detalle: "Código DANE " + m.cod + " · Subregión " + m.subregion };
    }
    if (estado.eat) {
      var me = MUN.filter(function (x) { return nombreEat(x) === estado.eat; });
      return { tipo: "eat", nombre: estado.eat, datos: DATOS.eats[claveEat(estado.eat)],
               miembros: me,
               detalle: "Esquema asociativo territorial · " + me.length + " municipios" };
    }
    if (estado.subregion) {
      var ms = MUN.filter(function (x) { return x.subregion === estado.subregion; });
      return { tipo: "sub", nombre: estado.subregion,
               datos: DATOS.subregiones[estado.subregion], miembros: ms,
               detalle: "Subregión · " + ms.length + " municipios" };
    }
    return { tipo: "dep", nombre: "Antioquia", datos: DEP, miembros: MUN,
             detalle: "Departamento · 125 municipios" };
  }
  function nombreEat(m) { return DATOS.eat_display[m.eat] || m.eat; }
  function claveEat(nombre) {
    for (var i = 0; i < MUN.length; i++) {
      if (nombreEat(MUN[i]) === nombre) return MUN[i].eat;
    }
    return nombre;
  }
  function codigosAmbito() {
    return ambito().miembros.map(function (m) { return m.cod; });
  }

  function pintarPanel() {
    var eje = ejeActual();
    var amb = ambito();
    var m = amb.tipo === "mun" ? amb.datos : null;
    var o = amb.datos || DEP;
    var e = o.ejes[estado.eje];
    var invEje = m ? m.inversion[estado.eje]
      : (amb.tipo === "dep" ? INV.totales[estado.eje]
         : (o.inversion ? o.inversion[estado.eje] : 0));

    var acciones = [];
    if (amb.tipo !== "dep") {
      acciones.push('<button class="btn-sec" id="volver">' +
                    "&larr; Todo el departamento</button>");
    }
    if (m) {
      acciones.push('<a class="btn-pri" id="verficha" target="_blank" ' +
                    'rel="noopener" title="Abre ' + DATOS.enlace_ficha +
                    ' en otra pestaña. Los dos archivos deben estar en la ' +
                    'misma carpeta.">Ficha completa &rarr;</a>');
    }
    var cab = '<div class="ambito">' + amb.nombre + "</div>" +
      '<div class="ambito-sub">' + amb.detalle + "</div>" +
      (acciones.length ? '<div class="acciones">' + acciones.join("") + "</div>" : "");

    var tono = colorPorTema(eje.id);
    var tarjeta = '<div class="grande" style="border-color:' + tono +
      ";box-shadow:0 0 26px " + mezcla(tono, 0.35) + '">' +
      '<div class="n" style="color:' + tono + '">' + num(e.unidades) + "</div>" +
      '<div class="e">' + eje.unidad + "</div>" +
      (e.cobertura !== null && e.cobertura !== undefined
        ? '<div class="d">Cobertura ' + pct(e.cobertura, 1) + "</div>" : "") +
      "</div>";

    var detalle = Object.keys(e.detalle).map(function (k) {
      return kpi(k, num(e.detalle[k]));
    }).join("");

    // Qué significan las dos métricas en este eje. Cambian de eje a eje,
    // así que se explican donde se leen.
    var glosario = '<div class="glosario">' +
      "<b>" + eje.unidad + ":</b> " + eje.unidad_desc +
      (eje.cobertura ? "<br><b>Cobertura:</b> " + eje.cobertura + "." : "") +
      "</div>";

    var repartos = (e.repartos || []).filter(function (r) {
      return r.filas && r.filas.length;
    }).map(function (r) {
      return '<div class="bloque"><h3>' + r.titulo + "</h3>" +
        r.filas.map(function (f) { return filaRep(f, tono); }).join("") +
        "</div>";
    }).join("");

    var bloqueInv = !VER_INVERSION ? "" : '<div class="bloque"><h3>Inversión ' + INV.etiqueta_valor + "</h3>" +
        kpi("En " + eje.nombre, plata(invEje)) +
        kpi("Total todos los ejes",
            plata(amb.tipo === "dep" ? INV.total : (o.inversion_total || 0))) +
        INV.reparto_ejes.map(function (f) {
          return filaRep({ nombre: f.nombre, part: f.part, total: f.total },
                         colorPorTema(f.id), plata);
        }).join("") + "</div>"
      ;

    document.getElementById("panel").innerHTML = cab + tarjeta +
      '<div class="bloque"><h3>' + eje.nombre + " · detalle</h3>" + detalle +
      glosario + "</div>" + bloqueInv + repartos +
      '<div class="pie">Fuente: sábana única del visor · ' + META.dependencia +
      ". Mapa base © OpenStreetMap y CARTO. " +
      '<a href="' + DATOS.enlace_gobernacion + '" target="_blank" rel="noopener">' +
      "Mapa oficial de Antioquia</a>.</div>";

    var volver = document.getElementById("volver");
    if (volver) volver.onclick = function () {
      estado.municipio = null; estado.eat = ""; estado.subregion = "";
      refrescarSelectores();
      volarAAmbito();
      sincronizar();
    };
    var ficha = document.getElementById("verficha");
    if (ficha && m) ficha.href = DATOS.enlace_ficha + "?mun=" + m.cod;
  }

  function seleccionar(cod) {
    estado.municipio = cod;
    document.getElementById("fmun").value = cod || "";
    if (cargado) {
      mapa.setFilter("municipios-sel", ["==", ["get", "cod"], cod || "__"]);
      aplicarEstilo();
    }
    pintarPanel(); pintarFranja();
  }

  // Encaja la cámara sobre un conjunto de municipios.
  function limites(codigos) {
    var dentro = {}, x1 = 180, y1 = 90, x2 = -180, y2 = -90, hay = false;
    codigos.forEach(function (c) { dentro[c] = true; });
    GEOJSON.municipios.features.forEach(function (f) {
      if (!dentro[f.properties.cod]) return;
      f.geometry.coordinates[0].forEach(function (p) {
        hay = true;
        if (p[0] < x1) x1 = p[0];
        if (p[1] < y1) y1 = p[1];
        if (p[0] > x2) x2 = p[0];
        if (p[1] > y2) y2 = p[1];
      });
    });
    return hay ? [[x1, y1], [x2, y2]] : null;
  }
  // Límites del trazado de fibra de un municipio, si tiene KMZ cargado.
  function limitesFibra(cod) {
    if (!GEOJSON.fibra || !GEOJSON.fibra.features.length) return null;
    var x1 = 180, y1 = 90, x2 = -180, y2 = -90, hay = false;
    GEOJSON.fibra.features.forEach(function (f) {
      if (f.properties.cod !== cod) return;
      f.geometry.coordinates.forEach(function (linea) {
        linea.forEach(function (p) {
          hay = true;
          if (p[0] < x1) x1 = p[0];
          if (p[1] < y1) y1 = p[1];
          if (p[0] > x2) x2 = p[0];
          if (p[1] > y2) y2 = p[1];
        });
      });
    });
    return hay ? [[x1, y1], [x2, y2]] : null;
  }

  function volarA(cod) {
    if (!cargado) return;
    // Con la capa de fibra encendida el acercamiento se hace al trazado,
    // que es lo que se quiere ver de cerca, no al contorno del municipio.
    var trazado = estado.capas.fibra ? limitesFibra(cod) : null;
    var b = trazado || limites([cod]);
    if (b) mapa.fitBounds(b, { padding: trazado ? 60 : 110, duration: 900,
                               maxZoom: trazado ? 14 : 11.5 });
  }
  function volarAAmbito() {
    if (!cargado) return;
    var b = limites(codigosAmbito());
    if (b) mapa.fitBounds(b, { padding: 70, duration: 800 });
  }

  /* ---------------- controles ---------------- */
  function pintarPills() {
    document.getElementById("pills").innerHTML = EJES.map(function (e) {
      return '<button data-eje="' + e.id + '"' +
        (e.id === estado.eje ? ' class="on"' : "") +
        '><span class="pt" style="background:' + e.color + '"></span>' +
        e.nombre + "</button>";
    }).join("");
    Array.prototype.forEach.call(document.querySelectorAll("#pills button"),
      function (b) {
        b.onclick = function () {
          estado.eje = b.getAttribute("data-eje");
          CAPAS.forEach(function (c) { estado.capas[c.id] = (c.eje === estado.eje); });
          sincronizar();
        };
      });
  }

  function listaCapas() {
    var l = CAPAS.slice();
    if (GEOJSON.fibra && GEOJSON.fibra.features.length) {
      l.push({ id: "fibra", eje: "seguridad", nombre: "Trazado de fibra óptica",
               georreferenciados: GEOJSON.fibra.features.length });
    }
    return l;
  }

  function pintarCapas() {
    document.getElementById("capas").innerHTML = "<h4>Capas del mapa</h4>" +
      listaCapas().map(function (c) {
        return '<label class="capa"><input type="checkbox" data-capa="' + c.id + '"' +
          (estado.capas[c.id] ? " checked" : "") + '>' +
          '<span class="pto" style="background:' + colorPorTema(c.eje) + ';color:' + colorPorTema(c.eje) + '"></span>' +
          '<span class="cn">' + c.nombre + '</span>' +
          '<span class="cc">' + num(c.georreferenciados) + "</span></label>";
      }).join("");
    Array.prototype.forEach.call(document.querySelectorAll("#capas input"),
      function (i) {
        i.onchange = function () {
          estado.capas[i.getAttribute("data-capa")] = i.checked;
          aplicarEstilo();
        };
      });
  }

  // Franja inferior con los cuatro ejes, al estilo de una sala de monitoreo.
  function pintarFranja() {
    var m = estado.municipio ? POR_COD[estado.municipio] : null;
    var o = m || DEP;
    document.getElementById("franja").innerHTML = EJES.map(function (x) {
      var tono = colorPorTema(x.id), activo = x.id === estado.eje;
      return '<div class="mx" data-eje="' + x.id + '" style="border-color:' + tono +
        (activo ? "" : ";opacity:.62") + '">' +
        '<div class="mn mono" style="color:' + tono + '">' +
        num(o.ejes[x.id].unidades) + "</div>" +
        '<div class="ml">' + x.nombre + " · " + x.unidad + "</div></div>";
    }).join("");
    Array.prototype.forEach.call(document.querySelectorAll("#franja .mx"),
      function (d) {
        d.onclick = function () {
          estado.eje = d.getAttribute("data-eje");
          listaCapas().forEach(function (c) {
            estado.capas[c.id] = (c.eje === estado.eje);
          });
          sincronizar();
        };
      });
  }

  function pintarLeyenda() {
    var eje = ejeActual(), r = rango();
    var etiqueta = estado.metrica === "cobertura" ? "Cobertura"
      : estado.metrica === "inversion" ? "Inversión" : eje.unidad;
    var cajas = [0.12, 0.3, 0.48, 0.66, 0.84, 1].map(function (f) {
      return '<i style="background:' + mezcla(colorPorTema(eje.id), f) + '"></i>';
    }).join("");
    document.getElementById("leyenda").innerHTML = "<h4>" + etiqueta + "</h4>" +
      '<div class="escala">' + cajas + "</div>" +
      '<div class="escala-txt"><span>' + fmtMetrica(r[0]) + "</span><span>" +
      fmtMetrica(r[1]) + "</span></div>";
  }

  // Subregión -> EAT -> Municipio. Cada uno acota al siguiente.
  function refrescarSelectores() {
    var fs = document.getElementById("fsub"),
        fe = document.getElementById("feat"),
        fm = document.getElementById("fmun");

    var subs = [];
    MUN.forEach(function (m) {
      if (subs.indexOf(m.subregion) < 0) subs.push(m.subregion);
    });
    subs.sort(function (a, b) { return a.localeCompare(b, "es"); });
    fs.innerHTML = '<option value="">Todas las subregiones</option>' +
      subs.map(function (v) {
        return '<option value="' + v + '">' + v + "</option>";
      }).join("");
    fs.value = estado.subregion;

    var eats = [];
    MUN.forEach(function (m) {
      if (estado.subregion && m.subregion !== estado.subregion) return;
      var e = nombreEat(m);
      if (eats.indexOf(e) < 0) eats.push(e);
    });
    eats.sort(function (a, b) { return a.localeCompare(b, "es"); });
    fe.innerHTML = '<option value="">Todos los EAT</option>' +
      eats.map(function (v) {
        return '<option value="' + v + '">' + v + "</option>";
      }).join("");
    if (eats.indexOf(estado.eat) < 0) estado.eat = "";
    fe.value = estado.eat;

    var lista = MUN.filter(function (m) {
      return (!estado.subregion || m.subregion === estado.subregion)
        && (!estado.eat || nombreEat(m) === estado.eat);
    }).sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); });
    fm.innerHTML = '<option value="">Todos los municipios</option>' +
      lista.map(function (m) {
        return '<option value="' + m.cod + '">' + m.nombre + "</option>";
      }).join("");
    if (estado.municipio &&
        !lista.some(function (m) { return m.cod === estado.municipio; })) {
      estado.municipio = null;
    }
    fm.value = estado.municipio || "";
  }

  function pintarMunicipios() {
    refrescarSelectores();
    document.getElementById("fsub").onchange = function () {
      estado.subregion = this.value; estado.eat = ""; estado.municipio = null;
      refrescarSelectores(); volarAAmbito(); sincronizar();
    };
    document.getElementById("feat").onchange = function () {
      estado.eat = this.value; estado.municipio = null;
      refrescarSelectores(); volarAAmbito(); sincronizar();
    };
    document.getElementById("fmun").onchange = function () {
      estado.municipio = this.value || null;
      seleccionar(estado.municipio);
      if (estado.municipio) volarA(estado.municipio); else volarAAmbito();
      sincronizar();
    };
  }

  function sincronizar() {
    refrescarMetricas();
    pintarPills(); pintarCapas(); pintarLeyenda(); pintarPanel(); pintarFranja();
    aplicarEstilo();
  }

  /* ---------------- exportación ---------------- */
  function exportar() {
    var enc = ["COD_DANE", "Municipio", "Subregion", "EAT"];
    EJES.forEach(function (e) {
      enc.push(e.nombre + " · unidades");
      enc.push(e.nombre + " · cobertura");
      if (VER_INVERSION) enc.push(e.nombre + " · inversion");
    });
    if (VER_INVERSION) enc.push("Inversion total");
    var lineas = [enc.join(";")];
    MUN.slice().sort(function (a, b) {
      return a.nombre.localeCompare(b.nombre, "es");
    }).forEach(function (m) {
      var f = [m.cod, m.nombre, m.subregion, DATOS.eat_display[m.eat] || m.eat];
      EJES.forEach(function (e) {
        var x = m.ejes[e.id];
        f.push(x.unidades);
        f.push(x.cobertura === null || x.cobertura === undefined ? ""
               : (x.cobertura * 100).toFixed(1).replace(".", ","));
        if (VER_INVERSION) f.push(Math.round(m.inversion[e.id]));
      });
      if (VER_INVERSION) f.push(Math.round(m.inversion_total));
      lineas.push(f.join(";"));
    });
    var blob = new Blob(["\uFEFF" + lineas.join("\r\n")],
                        { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = "observatorio_conectividad.csv";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  /* ---------------- arranque ---------------- */
  document.getElementById("logo").src = "data:image/png;base64," + IMG.logo;
  function refrescarMetricas() {
    var eje = ejeActual(), sel = document.getElementById("metrica");
    var ops = [{ v: "unidades", t: eje.unidad }];
    if (eje.cobertura) ops.push({ v: "cobertura", t: "Cobertura (%)" });
    if (VER_INVERSION) ops.push({ v: "inversion", t: "Inversión ($)" });
    if ((!eje.cobertura && estado.metrica === "cobertura")
        || (!VER_INVERSION && estado.metrica === "inversion")) {
      estado.metrica = "unidades";
    }
    sel.innerHTML = ops.map(function (o) {
      return '<option value="' + o.v + '">' + o.t + "</option>";
    }).join("");
    sel.value = estado.metrica;
    document.getElementById("ayudaMetrica").textContent =
      estado.metrica === "cobertura" ? eje.cobertura
      : estado.metrica === "inversion"
        ? "Pesos imputados a este eje, " + INV.etiqueta_valor
        : eje.unidad_desc;
  }

  document.getElementById("metrica").onchange = function () {
    estado.metrica = this.value;
    refrescarMetricas(); aplicarEstilo(); pintarLeyenda(); pintarPanel();
  };
  document.getElementById("btn3d").title =
    "Levanta cada municipio como una columna cuya altura es el indicador " +
    "seleccionado, y bascula la cámara. Sirve para comparar magnitudes de un " +
    "vistazo: entre más alto, más alto el valor.";
  document.getElementById("btn3d").onclick = function () {
    estado.tresD = !estado.tresD;
    this.className = "accion" + (estado.tresD ? " on" : "");
    document.getElementById("ayuda").textContent = estado.tresD
      ? "Relieve activo: la altura de cada municipio es el indicador seleccionado"
      : "Clic en un municipio para acercar y ver su detalle";
    if (cargado) {
      mapa.easeTo({ pitch: estado.tresD ? 52 : 0,
                    bearing: estado.tresD ? -18 : 0, duration: 700 });
    }
    aplicarEstilo();
  };
  document.getElementById("exportar").onclick = exportar;

  // Enlace profundo desde la ficha: observatorio_mapa.html?mun=05002
  (function () {
    var m = String(window.location && window.location.search || "")
      .match(/[?&]mun=(\d{4,5})/);
    if (!m) return;
    var cod = m[1].length === 4 ? "0" + m[1] : m[1];
    if (!POR_COD[cod]) return;
    estado.subregion = POR_COD[cod].subregion;
    estado.municipio = cod;
  })();

  pintarMunicipios();
  refrescarMetricas();
  pintarPills(); pintarCapas(); pintarLeyenda(); pintarPanel(); pintarFranja();

  if (typeof maplibregl === "undefined") {
    document.getElementById("sinred").style.display = "block";
  } else {
    construirMapa();
  }
})();

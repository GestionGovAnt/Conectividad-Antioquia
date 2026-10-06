/* ------------------------------------------------------------------
   Observatorio de Conectividad — Antioquia
   Datos inyectados por render.py en DATOS, GEO e IMG.
   Sin cifras en este archivo: solo presentación e interacción.
   ------------------------------------------------------------------ */
(function () {
  "use strict";

  var MUN = DATOS.municipios,
      SUB = DATOS.subregiones,
      DEP = DATOS.departamento,
      EJES = DATOS.ejes,
      INV = DATOS.inversion,
      CAPAS = DATOS.capas;

  var POR_COD = {};
  MUN.forEach(function (m) { POR_COD[m.cod] = m; });

  var estado = {
    eje: "educacion",
    metrica: "unidades",
    municipio: null,
    capas: {}
  };
  CAPAS.forEach(function (c) { estado.capas[c.id] = (c.eje === "educacion"); });

  /* ---------------- formato ---------------- */
  function num(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return Math.round(v).toLocaleString("es-CO");
  }
  function pct(v, dec) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v * 100).toFixed(dec === undefined ? 0 : dec).replace(".", ",") + "%";
  }
  // Pesos en escala legible: mil millones -> "$1.250 M"
  function plata(v) {
    if (!v) return "$0";
    if (v >= 1e9) return "$" + (v / 1e9).toFixed(1).replace(".", ",") + " mil M";
    if (v >= 1e6) return "$" + (v / 1e6).toFixed(0) + " M";
    return "$" + num(v);
  }
  function ejeActual() {
    for (var i = 0; i < EJES.length; i++) {
      if (EJES[i].id === estado.eje) return EJES[i];
    }
    return EJES[0];
  }

  /* ---------------- escala de color ---------------- */
  function mezcla(hex, f) {
    var r = parseInt(hex.substr(1, 2), 16),
        g = parseInt(hex.substr(3, 2), 16),
        b = parseInt(hex.substr(5, 2), 16);
    // f = 0 -> casi blanco, f = 1 -> color pleno
    var m = function (c) { return Math.round(245 - (245 - c) * f); };
    return "rgb(" + m(r) + "," + m(g) + "," + m(b) + ")";
  }

  function valorDe(m) {
    var e = m.ejes[estado.eje];
    if (estado.metrica === "cobertura") return e.cobertura;
    if (estado.metrica === "inversion") return m.inversion[estado.eje];
    return e.unidades;
  }

  function rango() {
    var vals = MUN.map(valorDe).filter(function (v) {
      return v !== null && v !== undefined && !isNaN(v);
    });
    if (!vals.length) return [0, 0];
    return [Math.min.apply(null, vals), Math.max.apply(null, vals)];
  }

  /* ---------------- mapa ---------------- */
  function pintarMapa() {
    var eje = ejeActual(), r = rango(), min = r[0], max = r[1];
    var paths = Object.keys(GEO.paths).map(function (cod) {
      var m = POR_COD[cod];
      var v = m ? valorDe(m) : null;
      var f = (v === null || v === undefined || max === min)
        ? (v ? 0.5 : 0.06)
        : 0.10 + 0.90 * ((v - min) / (max - min));
      var sel = estado.municipio === cod ? " sel" : "";
      return '<path class="mp' + sel + '" data-cod="' + cod + '" d="' +
        GEO.paths[cod] + '" fill="' + mezcla(eje.color, f) + '"></path>';
    }).join("");

    var puntos = CAPAS.filter(function (c) { return estado.capas[c.id]; })
      .map(function (c) {
        var color = colorEje(c.eje);
        return c.puntos.map(function (p) {
          return '<circle class="pt" cx="' + p[0] + '" cy="' + p[1] +
            '" r="' + c.radio + '" fill="' + color + '"></circle>';
        }).join("");
      }).join("");

    document.getElementById("mapa").innerHTML =
      '<svg viewBox="0 0 ' + GEO.W + " " + GEO.H +
      '" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">' +
      paths + '<path class="mout" d="' + GEO.outline + '"/>' + puntos + "</svg>";

    var svg = document.querySelector("#mapa svg");
    svg.addEventListener("click", function (ev) {
      var cod = ev.target.getAttribute && ev.target.getAttribute("data-cod");
      if (cod) { estado.municipio = (estado.municipio === cod) ? null : cod; sincronizar(); }
    });
    svg.addEventListener("mousemove", function (ev) {
      var cod = ev.target.getAttribute && ev.target.getAttribute("data-cod");
      mostrarTooltip(cod, ev);
    });
    svg.addEventListener("mouseleave", function () {
      document.getElementById("tooltip").style.opacity = 0;
    });
  }

  function colorEje(id) {
    for (var i = 0; i < EJES.length; i++) if (EJES[i].id === id) return EJES[i].color;
    return "#666";
  }

  function mostrarTooltip(cod, ev) {
    var t = document.getElementById("tooltip");
    if (!cod || !POR_COD[cod]) { t.style.opacity = 0; return; }
    var m = POR_COD[cod], e = m.ejes[estado.eje], eje = ejeActual();
    t.innerHTML = "<b>" + m.nombre + "</b><br>" +
      '<span class="tv">' + eje.unidad + ":</span> " + num(e.unidades) +
      (e.cobertura !== null && e.cobertura !== undefined
        ? '<br><span class="tv">Cobertura:</span> ' + pct(e.cobertura) : "") +
      (INV.disponible
        ? '<br><span class="tv">Inversión:</span> ' + plata(m.inversion[estado.eje])
        : "");
    var caja = document.getElementById("lienzo").getBoundingClientRect();
    t.style.left = Math.min(ev.clientX - caja.left + 14, caja.width - 250) + "px";
    t.style.top = (ev.clientY - caja.top + 14) + "px";
    t.style.opacity = 1;
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

  function pintarPanel() {
    var eje = ejeActual();
    var m = estado.municipio ? POR_COD[estado.municipio] : null;
    var o = m || DEP;
    var e = o.ejes[estado.eje];
    var invEje = m ? m.inversion[estado.eje] : INV.totales[estado.eje];

    var cab = m
      ? '<div class="ambito">' + m.nombre + "</div>" +
        '<div class="ambito-sub">Código DANE ' + m.cod + " · Subregión " +
        m.subregion + "</div>" +
        '<button class="volver" id="volver">Volver al departamento</button>'
      : '<div class="ambito">Antioquia</div>' +
        '<div class="ambito-sub">125 municipios · 9 subregiones</div>';

    var tarjeta = '<div class="grande" style="background:linear-gradient(135deg,' +
      eje.color + ',' + mezcla(eje.color, 0.72) + ')">' +
      '<div class="n">' + num(e.unidades) + "</div>" +
      '<div class="e">' + eje.unidad + "</div>" +
      (e.cobertura !== null && e.cobertura !== undefined
        ? '<div class="d">Cobertura ' + pct(e.cobertura, 1) + "</div>" : "") +
      "</div>";

    var detalle = Object.keys(e.detalle).map(function (k) {
      return kpi(k, num(e.detalle[k]));
    }).join("");

    var repartos = (e.repartos || []).filter(function (r) {
      return r.filas && r.filas.length;
    }).map(function (r) {
      return '<div class="bloque"><h3>' + r.titulo + "</h3>" +
        r.filas.map(function (f) { return filaRep(f, eje.color); }).join("") +
        "</div>";
    }).join("");

    var bloqueInv;
    if (INV.disponible) {
      bloqueInv = '<div class="bloque"><h3>Inversión ' + INV.etiqueta_valor + "</h3>" +
        kpi("En " + eje.nombre, plata(invEje)) +
        kpi("Total todos los ejes", plata(m ? m.inversion_total : INV.total)) +
        INV.reparto_ejes.map(function (f) {
          return filaRep({ nombre: f.nombre, part: f.part, total: f.total },
                         colorEje(f.id), plata);
        }).join("") + "</div>";
    } else {
      bloqueInv = '<div class="aviso"><b>Falta cargar la inversión.</b><br>' +
        "Complete <code>datos/inversion.csv</code> y vuelva a ejecutar " +
        "<code>python build.py</code>. Los cuatro ejes de conectividad ya " +
        "están completos; las tarjetas de inversión esperan el dato.</div>";
    }

    document.getElementById("panel").innerHTML = cab + tarjeta +
      '<div class="bloque"><h3>' + eje.nombre + " · detalle</h3>" + detalle + "</div>" +
      bloqueInv + repartos +
      '<div class="pie">Fuente: sábana única del visor · ' + META.dependencia +
      ". Las cifras se recalculan desde el Excel en cada construcción. " +
      '<a href="' + DATOS.enlace_gobernacion + '" target="_blank" rel="noopener">' +
      "Mapa oficial de Antioquia</a>.</div>";

    var volver = document.getElementById("volver");
    if (volver) volver.onclick = function () { estado.municipio = null; sincronizar(); };
  }

  /* ---------------- controles ---------------- */
  function pintarPills() {
    document.getElementById("pills").innerHTML = EJES.map(function (e) {
      return '<button data-eje="' + e.id + '"' +
        (e.id === estado.eje ? ' class="on"' : "") +
        '><span class="pt" style="background:' + e.color + '"></span>' +
        e.nombre + "</button>";
    }).join("");
    Array.prototype.forEach.call(
      document.querySelectorAll("#pills button"), function (b) {
        b.onclick = function () {
          estado.eje = b.getAttribute("data-eje");
          CAPAS.forEach(function (c) { estado.capas[c.id] = (c.eje === estado.eje); });
          sincronizar();
        };
      });
  }

  function pintarCapas() {
    document.getElementById("capas").innerHTML = "<h4>Capas del mapa</h4>" +
      CAPAS.map(function (c) {
        return '<label class="capa"><input type="checkbox" data-capa="' + c.id + '"' +
          (estado.capas[c.id] ? " checked" : "") + '>' +
          '<span class="pto" style="background:' + colorEje(c.eje) + '"></span>' +
          '<span class="cn">' + c.nombre + '</span>' +
          '<span class="cc">' + num(c.georreferenciados) + "</span></label>";
      }).join("");
    Array.prototype.forEach.call(
      document.querySelectorAll("#capas input"), function (i) {
        i.onchange = function () {
          estado.capas[i.getAttribute("data-capa")] = i.checked;
          pintarMapa();
        };
      });
  }

  function pintarLeyenda() {
    var eje = ejeActual(), r = rango();
    var etiqueta = estado.metrica === "cobertura" ? "Cobertura"
      : estado.metrica === "inversion" ? "Inversión" : eje.unidad;
    var fmt = estado.metrica === "cobertura" ? pct
      : estado.metrica === "inversion" ? plata : num;
    var cajas = [0.10, 0.30, 0.50, 0.70, 0.90, 1].map(function (f) {
      return '<i style="background:' + mezcla(eje.color, f) + '"></i>';
    }).join("");
    document.getElementById("leyenda").innerHTML = "<h4>" + etiqueta + "</h4>" +
      '<div class="escala">' + cajas + "</div>" +
      '<div class="escala-txt"><span>' + fmt(r[0]) + "</span><span>" +
      fmt(r[1]) + "</span></div>";
  }

  function pintarMunicipios() {
    var sel = document.getElementById("fmun");
    sel.innerHTML = '<option value="">Todo el departamento</option>' +
      MUN.slice().sort(function (a, b) {
        return a.nombre.localeCompare(b.nombre, "es");
      }).map(function (m) {
        return '<option value="' + m.cod + '">' + m.nombre + "</option>";
      }).join("");
    sel.value = estado.municipio || "";
    sel.onchange = function () {
      estado.municipio = sel.value || null;
      sincronizar();
    };
  }

  function sincronizar() {
    pintarPills();
    pintarMapa();
    pintarPanel();
    pintarCapas();
    pintarLeyenda();
    document.getElementById("fmun").value = estado.municipio || "";
  }

  /* ---------------- exportación ---------------- */
  function exportar() {
    var enc = ["COD_DANE", "Municipio", "Subregion", "EAT"];
    EJES.forEach(function (e) {
      enc.push(e.nombre + " · unidades");
      enc.push(e.nombre + " · cobertura");
      enc.push(e.nombre + " · inversion");
    });
    enc.push("Inversion total");

    var lineas = [enc.join(";")];
    MUN.slice().sort(function (a, b) {
      return a.nombre.localeCompare(b.nombre, "es");
    }).forEach(function (m) {
      var f = [m.cod, m.nombre, m.subregion,
               DATOS.eat_display[m.eat] || m.eat];
      EJES.forEach(function (e) {
        var x = m.ejes[e.id];
        f.push(x.unidades);
        f.push(x.cobertura === null || x.cobertura === undefined ? ""
               : (x.cobertura * 100).toFixed(1).replace(".", ","));
        f.push(Math.round(m.inversion[e.id]));
      });
      f.push(Math.round(m.inversion_total));
      lineas.push(f.map(function (v) {
        var t = String(v === null || v === undefined ? "" : v);
        return t.indexOf(";") >= 0 ? '"' + t + '"' : t;
      }).join(";"));
    });

    var blob = new Blob(["\uFEFF" + lineas.join("\r\n")],
                        { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "observatorio_conectividad.csv";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  /* ---------------- arranque ---------------- */
  document.getElementById("logo").src = "data:image/png;base64," + IMG.logo;
  document.getElementById("dependencia").textContent =
    "Dirección de Gestión Territorial TIC · Gobernación de Antioquia";
  document.getElementById("metrica").onchange = function () {
    estado.metrica = this.value;
    pintarMapa(); pintarLeyenda(); pintarPanel();
  };
  document.getElementById("exportar").onclick = exportar;
  pintarMunicipios();
  sincronizar();
})();

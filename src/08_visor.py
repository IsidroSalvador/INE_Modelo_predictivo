"""Ensamblaje del visor web interactivo standalone (outputs/maps/visor.html)."""

import json
import pandas as pd
from config import OUT_MAP, OUT_TAB

esc = pd.read_csv(OUT_TAB / "escenarios_resumen.csv").to_dict("records")
mun = (OUT_MAP / "municipios.geojson").read_text(encoding="utf-8")
dis = (OUT_MAP / "distritos.geojson").read_text(encoding="utf-8")

PLANTILLA = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Riesgo de abstención 2027 – Semáforo territorial</title>
<meta name="description" content="Semáforo de riesgo de abstención 2027 por municipio y distrito, con y sin intervención. Basado en los Conteos Censales de Participación del INE.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  :root { --bg:#0f1420; --panel:rgba(22,28,43,.94); --txt:#e8ecf4; --muted:#93a0b8;
          --rojo:#d64541; --amarillo:#f2c230; --verde:#2e9e5b; --acento:#7c9cff; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Inter,sans-serif; background:var(--bg); color:var(--txt); }
  #mapa { position:absolute; inset:0; }
  .panel { position:absolute; z-index:1000; background:var(--panel); backdrop-filter:blur(8px);
           border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:18px;
           box-shadow:0 10px 30px rgba(0,0,0,.4); }
  #control { top:16px; left:16px; width:340px; }
  h1 { font-size:19px; margin:0 0 4px; font-weight:800; }
  .sub { color:var(--muted); font-size:12px; margin-bottom:14px; }
  .grupo { margin-bottom:12px; position:relative; }
  .grupo label { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); display:block; }
  .buscador-wrap { position:relative; margin-top:6px; display:flex; gap:6px; }
  #buscador { flex:1; width:100%; padding:8px 28px 8px 10px; border-radius:8px;
              border:1px solid rgba(255,255,255,.15); background:rgba(255,255,255,.05);
              color:var(--txt); font:400 12.5px Inter; outline:none; transition:.2s; }
  #buscador:focus { border-color:var(--acento); background:rgba(255,255,255,.08); }
  #buscador::placeholder { color:var(--muted); }
  #btn-limpiar { position:absolute; right:8px; top:50%; transform:translateY(-50%);
                 background:none; border:none; color:var(--muted); cursor:pointer;
                 font-size:15px; line-height:1; padding:2px 4px; display:none; }
  #btn-limpiar:hover { color:var(--txt); }
  #sugerencias { position:absolute; left:0; right:0; top:100%; margin-top:4px;
                 background:#182032; border:1px solid rgba(255,255,255,.14); border-radius:10px;
                 max-height:230px; overflow-y:auto; z-index:2000; display:none;
                 box-shadow:0 12px 28px rgba(0,0,0,.55); }
  .sug-item { display:flex; align-items:center; gap:8px; padding:8px 10px; cursor:pointer;
              font-size:12px; border-bottom:1px solid rgba(255,255,255,.05); }
  .sug-item:last-child { border-bottom:none; }
  .sug-item:hover, .sug-item.activo { background:rgba(124,156,255,.18); }
  .sug-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
  .sug-txt { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sug-txt small { color:var(--muted); margin-left:4px; }
  .sug-tag { font-size:10px; color:var(--muted); border:1px solid rgba(255,255,255,.12);
             border-radius:4px; padding:1px 5px; text-transform:uppercase; }
  .sug-vacio { padding:10px; font-size:12px; color:var(--muted); text-align:center; }
  .botones { display:flex; gap:6px; margin-top:6px; }
  .botones button { flex:1; padding:8px; border:1px solid rgba(255,255,255,.12); border-radius:8px;
           background:transparent; color:var(--txt); cursor:pointer; font:600 12px Inter; transition:.2s; }
  .botones button:hover { border-color:var(--acento); }
  .botones button.activo { background:var(--acento); border-color:var(--acento); color:#0f1420; }
  .kpis { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }
  .kpi { background:rgba(255,255,255,.04); border-radius:10px; padding:10px; }
  .kpi b { display:block; font-size:18px; }
  .kpi span { font-size:11px; color:var(--muted); }
  #leyenda { bottom:24px; left:16px; font-size:12px; }
  .item { display:flex; align-items:center; gap:8px; margin:4px 0; }
  .caja { width:14px; height:14px; border-radius:4px; }
  #info { top:16px; right:16px; width:295px; display:none; font-size:13px; }
  #info-head { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:8px; }
  #info h2 { font-size:16px; margin:0; line-height:1.25; }
  #btn-cerrar-info { background:none; border:none; color:var(--muted); cursor:pointer; font-size:16px; padding:0 2px; }
  #btn-cerrar-info:hover { color:var(--txt); }
  .fila { display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid rgba(255,255,255,.06); gap:8px; }
  .nota { font-size:11px; color:var(--muted); margin-top:10px; line-height:1.4; }
</style>
</head>
<body>
<main>
<div id="mapa" role="application" aria-label="Mapa de riesgo de abstención"></div>

<section class="panel" id="control">
  <h1>Riesgo de abstención 2027</h1>
  <div class="sub">Semáforo territorial · Conteos Censales de Participación (INE) 2009–2024</div>

  <div class="grupo">
    <label for="buscador">Buscar municipio o distrito</label>
    <div class="buscador-wrap">
      <input id="buscador" type="text" autocomplete="off" placeholder="Ej. Distrito 14, Tijuana, León...">
      <button id="btn-limpiar" title="Limpiar selección" onclick="limpiarSeleccion()">×</button>
    </div>
    <div id="sugerencias"></div>
  </div>

  <div class="grupo"><label>Nivel territorial</label>
    <div class="botones">
      <button id="btn-municipio" class="activo" onclick="cambiarNivel('municipio')">Municipios</button>
      <button id="btn-distrito" onclick="cambiarNivel('distrito')">Distritos</button>
    </div></div>
  <div class="grupo"><label>Escenario</label>
    <div class="botones">
      <button id="btn-sin" class="activo" onclick="cambiarEscenario('sin')">Sin intervención</button>
      <button id="btn-con" onclick="cambiarEscenario('con')">Con intervención</button>
    </div></div>
  <div class="kpis" id="kpis"></div>
  <div class="nota">La intervención es un <b>supuesto</b> (+2.5 pp en secciones rojas), no un efecto estimado.
    Sensibilidad: +1 pp y +4 pp en el reporte.</div>
</section>

<section class="panel" id="leyenda">
  <div class="item"><div class="caja" style="background:var(--rojo)"></div>Rojo · participación esperada muy baja</div>
  <div class="item"><div class="caja" style="background:var(--amarillo)"></div>Amarillo · baja o en caída ≥ 3 pp</div>
  <div class="item"><div class="caja" style="background:var(--verde)"></div>Verde · sin alerta</div>
</section>

<aside class="panel" id="info"></aside>
</main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATOS = { municipio: __MUN__, distrito: __DIS__ };
const ESCENARIOS = __ESC__;
const COLOR = { rojo:"#d64541", amarillo:"#f2c230", verde:"#2e9e5b", sin_dato:"#555" };
const ENTIDADES = {
  1:"Aguascalientes", 2:"Baja California", 3:"Baja California Sur", 4:"Campeche",
  5:"Coahuila", 6:"Colima", 7:"Chiapas", 8:"Chihuahua", 9:"Ciudad de México",
  10:"Durango", 11:"Guanajuato", 12:"Guerrero", 13:"Hidalgo", 14:"Jalisco",
  15:"Estado de México", 16:"Michoacán", 17:"Morelos", 18:"Nayarit", 19:"Nuevo León",
  20:"Oaxaca", 21:"Puebla", 22:"Querétaro", 23:"Quintana Roo", 24:"San Luis Potosí",
  25:"Sinaloa", 26:"Sonora", 27:"Tabasco", 28:"Tamaulipas", 29:"Tlaxcala",
  30:"Veracruz", 31:"Yucatán", 32:"Zacatecas"
};
const ALIAS_ENT = {
  2:"bc", 3:"bcs", 9:"cdmx df", 15:"edomex mex", 19:"nl", 22:"qro", 23:"qroo", 24:"slp"
};

let nivel = "municipio", escenario = "sin", capa = null;
let capasPorId = {};
let idSeleccionado = null;
let resultadosActuales = [];
let indiceSug = -1;

const mapa = L.map("mapa", { zoomControl:false }).setView([23.6, -102.5], 5);
L.control.zoom({ position:"bottomright" }).addTo(mapa);
L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  { attribution:"© OpenStreetMap · © CARTO", maxZoom:12 }).addTo(mapa);

const pct = v => v == null ? "–" : (v * 100).toFixed(1) + "%";
const num = v => v == null ? "–" : Math.round(v).toLocaleString("es-MX");
const norm = s => (s || "").toString().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

function claveFeature(tipo, p) {
  return tipo === "municipio" ? `m_${p.ent}_${p.mun}` : `d_${p.ent}_${Math.round(p.DEF)}`;
}

const INDICE = [];
["distrito", "municipio"].forEach(tipo => {
  DATOS[tipo].features.forEach(f => {
    const p = f.properties;
    const entNom = ENTIDADES[p.ent] || ("Entidad " + p.ent);
    const alias = ALIAS_ENT[p.ent] || "";
    const defNum = tipo === "distrito" ? Math.round(p.DEF) : null;
    const defPad = defNum != null ? String(defNum).padStart(2, "0") : "";
    const titulo = tipo === "distrito" ? `Distrito Federal ${defNum}` : p.nombre;
    const texto = tipo === "distrito"
      ? norm(`distrito federal ${defNum} distrito ${defPad} df ${defNum} def ${defNum} ${entNom} ${alias}`)
      : norm(`municipio ${p.nombre} ${entNom} ${alias}`);
    INDICE.push({
      id: claveFeature(tipo, p),
      tipo,
      defNum,
      titulo,
      entNom,
      props: p,
      texto
    });
  });
});

function estilo(f) {
  const s = escenario === "sin" ? f.properties.semaforo : f.properties.semaforo_medio;
  const id = claveFeature(nivel, f.properties);
  const activo = id === idSeleccionado;
  return {
    fillColor: COLOR[s] || "#555",
    fillOpacity: activo ? .92 : .78,
    color: activo ? "#ffffff" : "#0f1420",
    weight: activo ? 2.6 : .4
  };
}

function mostrarInfo(p, tipoVista = nivel) {
  const nombre = tipoVista === "municipio" ? p.nombre : "Distrito Federal " + Math.round(p.DEF);
  const entNom = ENTIDADES[p.ent] || p.ent;
  const s = escenario === "sin" ? p.semaforo : p.semaforo_medio;
  const pctRojo = escenario === "sin" ? p.pct_LN_rojo : p.pct_LN_rojo_medio;
  document.getElementById("info").style.display = "block";
  document.getElementById("info").innerHTML = `
    <div id="info-head">
      <h2>${nombre}</h2>
      <button id="btn-cerrar-info" title="Cerrar" onclick="limpiarSeleccion()">×</button>
    </div>
    <div class="fila"><span>Entidad</span><b>${entNom}</b></div>
    <div class="fila"><span>Semáforo</span><b style="color:${COLOR[s]}">${(s||"").toUpperCase()}</b></div>
    <div class="fila"><span>Participación 2021</span><b>${pct(p.part_2021)}</b></div>
    <div class="fila"><span>Esperada 2027 (sin intervención)</span><b>${pct(p.pred_2027)}</b></div>
    <div class="fila"><span>Esperada 2027 (con intervención)</span><b>${pct(p.pred_interv_medio)}</b></div>
    <div class="fila"><span>Lista nominal</span><b>${num(p.LN)}</b></div>
    <div class="fila"><span>% lista en secciones rojas</span><b>${pct(pctRojo)}</b></div>
    <div class="fila"><span>Secciones</span><b>${num(p.secciones)}</b></div>`;
}

function dibujar() {
  if (capa) mapa.removeLayer(capa);
  capasPorId = {};
  capa = L.geoJSON(DATOS[nivel], {
    style: estilo,
    onEachFeature: (f, l) => {
      const id = claveFeature(nivel, f.properties);
      capasPorId[id] = l;
      l.on("mouseover", () => {
        l.setStyle({ weight: 2.4, color: "#fff" });
        l.bringToFront();
        mostrarInfo(f.properties, nivel);
      });
      l.on("mouseout", () => {
        capa.resetStyle(l);
        if (idSeleccionado && capasPorId[idSeleccionado]) {
          capasPorId[idSeleccionado].bringToFront();
          mostrarInfo(capasPorId[idSeleccionado].feature.properties, nivel);
        }
      });
      l.on("click", () => seleccionarItem({
        id,
        tipo: nivel,
        titulo: nivel === "distrito" ? `Distrito Federal ${Math.round(f.properties.DEF)}` : f.properties.nombre,
        entNom: ENTIDADES[f.properties.ent] || f.properties.ent,
        props: f.properties
      }, false));
    }
  }).addTo(mapa);
  if (idSeleccionado && capasPorId[idSeleccionado]) {
    capasPorId[idSeleccionado].bringToFront();
  }
  actualizarKPIs();
}

function actualizarKPIs() {
  const e = ESCENARIOS.find(x => x.escenario === (escenario === "sin" ? "sin_intervencion" : "intervencion_medio"));
  const conteo = { rojo:0, amarillo:0, verde:0 };
  DATOS[nivel].features.forEach(f => {
    const s = escenario === "sin" ? f.properties.semaforo : f.properties.semaforo_medio;
    if (s in conteo) conteo[s]++;
  });
  document.getElementById("kpis").innerHTML = `
    <div class="kpi"><b>${pct(e.part_nacional)}</b><span>Participación nacional esperada</span></div>
    <div class="kpi"><b>${num(e.votos_adicionales)}</b><span>Votos adicionales</span></div>
    <div class="kpi"><b style="color:var(--rojo)">${conteo.rojo}</b><span>${nivel}s en rojo</span></div>
    <div class="kpi"><b>${num(e.secciones_rojas)}</b><span>Secciones en rojo</span></div>`;
}

function cambiarNivel(n, mantenerSeleccion = false) {
  nivel = n;
  if (!mantenerSeleccion) idSeleccionado = null;
  document.getElementById("btn-municipio").classList.toggle("activo", n === "municipio");
  document.getElementById("btn-distrito").classList.toggle("activo", n === "distrito");
  dibujar();
}

function cambiarEscenario(e) {
  escenario = e;
  document.getElementById("btn-sin").classList.toggle("activo", e === "sin");
  document.getElementById("btn-con").classList.toggle("activo", e === "con");
  capa.setStyle(estilo);
  actualizarKPIs();
  if (idSeleccionado && capasPorId[idSeleccionado]) {
    mostrarInfo(capasPorId[idSeleccionado].feature.properties, nivel);
  }
}

function buscarItems(consulta) {
  const q = norm(consulta);
  if (!q) return [];
  const tokens = q.split(/\s+/).filter(Boolean);
  const numBuscado = (q.match(/\b0*(\d{1,2})\b/) || [])[1];
  const pideDistrito = /\b(distrito|dist|df|def)\b/.test(q);
  const pideMunicipio = /\b(municipio|mun)\b/.test(q);

  const coincidencias = [];
  for (const item of INDICE) {
    let ok = true;
    for (const tk of tokens) {
      if (/^\d+$/.test(tk)) {
        const n = parseInt(tk, 10);
        if (item.tipo === "distrito") {
          if (item.defNum !== n && !String(item.defNum).startsWith(String(n))) { ok = false; break; }
        } else if (!item.texto.includes(tk)) {
          ok = false; break;
        }
      } else if (!item.texto.includes(tk)) {
        ok = false; break;
      }
    }
    if (!ok) continue;

    let score = 0;
    if (pideDistrito && item.tipo === "distrito") score += 50;
    if (pideMunicipio && item.tipo === "municipio") score += 50;
    if (!pideDistrito && !pideMunicipio && item.tipo === nivel) score += 20;
    if (numBuscado && item.tipo === "distrito" && item.defNum === parseInt(numBuscado, 10)) score += 40;
    if (norm(item.titulo).startsWith(q)) score += 30;
    coincidencias.push({ item, score });
  }

  coincidencias.sort((a, b) => b.score - a.score || a.item.entNom.localeCompare(b.item.entNom, "es"));
  return coincidencias.slice(0, 40).map(x => x.item);
}

function renderizarSugerencias(lista) {
  const cont = document.getElementById("sugerencias");
  resultadosActuales = lista;
  indiceSug = lista.length ? 0 : -1;

  if (!document.getElementById("buscador").value.trim()) {
    cont.style.display = "none";
    return;
  }
  if (!lista.length) {
    cont.innerHTML = `<div class="sug-vacio">Sin coincidencias</div>`;
    cont.style.display = "block";
    return;
  }
  cont.innerHTML = lista.map((it, idx) => {
    const sem = escenario === "sin" ? it.props.semaforo : it.props.semaforo_medio;
    const color = COLOR[sem] || "#555";
    const etiq = it.tipo === "distrito" ? "Distrito" : "Municipio";
    return `<div class="sug-item ${idx === 0 ? "activo" : ""}" data-idx="${idx}">
      <span class="sug-dot" style="background:${color}"></span>
      <span class="sug-txt"><b>${it.titulo}</b> <small>· ${it.entNom}</small></span>
      <span class="sug-tag">${etiq}</span>
    </div>`;
  }).join("");
  cont.style.display = "block";

  cont.querySelectorAll(".sug-item").forEach(el => {
    el.addEventListener("mousedown", ev => {
      ev.preventDefault();
      seleccionarItem(resultadosActuales[parseInt(el.dataset.idx, 10)], true);
    });
  });
}

function seleccionarItem(item, hacerZoom = true) {
  if (!item) return;
  idSeleccionado = item.id;
  if (item.tipo !== nivel) {
    cambiarNivel(item.tipo, true);
  } else {
    capa.setStyle(estilo);
  }
  const layer = capasPorId[item.id];
  if (layer) {
    layer.bringToFront();
    if (hacerZoom) {
      mapa.fitBounds(layer.getBounds(), { padding: [70, 70], maxZoom: 10 });
    }
  }
  mostrarInfo(item.props, item.tipo);
  const input = document.getElementById("buscador");
  input.value = `${item.titulo} · ${item.entNom}`;
  document.getElementById("btn-limpiar").style.display = "block";
  document.getElementById("sugerencias").style.display = "none";
}

function limpiarSeleccion() {
  idSeleccionado = null;
  document.getElementById("buscador").value = "";
  document.getElementById("btn-limpiar").style.display = "none";
  document.getElementById("sugerencias").style.display = "none";
  document.getElementById("info").style.display = "none";
  if (capa) capa.setStyle(estilo);
  mapa.setView([23.6, -102.5], 5);
}

const inputBuscador = document.getElementById("buscador");
inputBuscador.addEventListener("focus", () => {
  if (inputBuscador.value) inputBuscador.select();
});
inputBuscador.addEventListener("input", e => {
  const val = e.target.value;
  document.getElementById("btn-limpiar").style.display = val ? "block" : "none";
  renderizarSugerencias(buscarItems(val));
});

inputBuscador.addEventListener("keydown", e => {
  const cont = document.getElementById("sugerencias");
  if (cont.style.display === "none" || !resultadosActuales.length) return;
  const items = cont.querySelectorAll(".sug-item");
  if (e.key === "ArrowDown") {
    e.preventDefault();
    indiceSug = (indiceSug + 1) % resultadosActuales.length;
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    indiceSug = (indiceSug - 1 + resultadosActuales.length) % resultadosActuales.length;
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (indiceSug >= 0) seleccionarItem(resultadosActuales[indiceSug], true);
    return;
  } else if (e.key === "Escape") {
    cont.style.display = "none";
    return;
  } else {
    return;
  }
  items.forEach((el, i) => el.classList.toggle("activo", i === indiceSug));
  if (items[indiceSug]) items[indiceSug].scrollIntoView({ block: "nearest" });
});

document.addEventListener("click", e => {
  if (!e.target.closest("#control")) {
    document.getElementById("sugerencias").style.display = "none";
  }
});

dibujar();
</script>
</body>
</html>"""

html = (PLANTILLA.replace("__MUN__", mun).replace("__DIS__", dis)
        .replace("__ESC__", json.dumps(esc)))
(OUT_MAP / "visor.html").write_text(html, encoding="utf-8")
print("Visor guardado en outputs/maps/visor.html")

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
  :root { --bg:#0f1420; --panel:rgba(22,28,43,.92); --txt:#e8ecf4; --muted:#93a0b8;
          --rojo:#d64541; --amarillo:#f2c230; --verde:#2e9e5b; --acento:#7c9cff; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Inter,sans-serif; background:var(--bg); color:var(--txt); }
  #mapa { position:absolute; inset:0; }
  .panel { position:absolute; z-index:1000; background:var(--panel); backdrop-filter:blur(8px);
           border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:18px;
           box-shadow:0 10px 30px rgba(0,0,0,.4); }
  #control { top:16px; left:16px; width:330px; }
  h1 { font-size:19px; margin:0 0 4px; font-weight:800; }
  .sub { color:var(--muted); font-size:12px; margin-bottom:14px; }
  .grupo { margin-bottom:12px; }
  .grupo label { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
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
  #info { top:16px; right:16px; width:280px; display:none; font-size:13px; }
  #info h2 { font-size:16px; margin:0 0 8px; }
  .fila { display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid rgba(255,255,255,.06); }
  .nota { font-size:11px; color:var(--muted); margin-top:10px; line-height:1.4; }
</style>
</head>
<body>
<main>
<div id="mapa" role="application" aria-label="Mapa de riesgo de abstención"></div>

<section class="panel" id="control">
  <h1>Riesgo de abstención 2027</h1>
  <div class="sub">Semáforo territorial · Conteos Censales de Participación (INE) 2009–2024</div>
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
let nivel = "municipio", escenario = "sin", capa = null;

const mapa = L.map("mapa", { zoomControl:false }).setView([23.6, -102.5], 5);
L.control.zoom({ position:"bottomright" }).addTo(mapa);
L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  { attribution:"© OpenStreetMap · © CARTO", maxZoom:12 }).addTo(mapa);

const pct = v => v == null ? "–" : (v * 100).toFixed(1) + "%";
const num = v => v == null ? "–" : Math.round(v).toLocaleString("es-MX");

function estilo(f) {
  const s = escenario === "sin" ? f.properties.semaforo : f.properties.semaforo_medio;
  return { fillColor: COLOR[s] || "#555", fillOpacity:.78, color:"#0f1420", weight:.4 };
}

function mostrarInfo(p) {
  const nombre = nivel === "municipio" ? p.nombre : "Distrito federal " + p.DEF;
  const s = escenario === "sin" ? p.semaforo : p.semaforo_medio;
  document.getElementById("info").style.display = "block";
  document.getElementById("info").innerHTML = `
    <h2>${nombre}</h2>
    <div class="fila"><span>Entidad</span><b>${p.ent}</b></div>
    <div class="fila"><span>Semáforo</span><b style="color:${COLOR[s]}">${(s||"").toUpperCase()}</b></div>
    <div class="fila"><span>Participación 2021</span><b>${pct(p.part_2021)}</b></div>
    <div class="fila"><span>Esperada 2027 (sin intervención)</span><b>${pct(p.pred_2027)}</b></div>
    <div class="fila"><span>Esperada 2027 (con intervención)</span><b>${pct(p.pred_interv_medio)}</b></div>
    <div class="fila"><span>Lista nominal</span><b>${num(p.LN)}</b></div>
    <div class="fila"><span>% lista en secciones rojas</span><b>${pct(p.pct_LN_rojo)}</b></div>
    <div class="fila"><span>Secciones</span><b>${num(p.secciones)}</b></div>`;
}

function dibujar() {
  if (capa) mapa.removeLayer(capa);
  capa = L.geoJSON(DATOS[nivel], {
    style: estilo,
    onEachFeature: (f, l) => {
      l.on("mouseover", () => { l.setStyle({ weight:2, color:"#fff" }); mostrarInfo(f.properties); });
      l.on("mouseout", () => capa.resetStyle(l));
    }
  }).addTo(mapa);
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

function cambiarNivel(n) {
  nivel = n;
  document.getElementById("btn-municipio").classList.toggle("activo", n === "municipio");
  document.getElementById("btn-distrito").classList.toggle("activo", n === "distrito");
  dibujar();
}
function cambiarEscenario(e) {
  escenario = e;
  document.getElementById("btn-sin").classList.toggle("activo", e === "sin");
  document.getElementById("btn-con").classList.toggle("activo", e === "con");
  capa.setStyle(estilo); actualizarKPIs();
}
dibujar();
</script>
</body>
</html>"""

html = (PLANTILLA.replace("__MUN__", mun).replace("__DIS__", dis)
        .replace("__ESC__", json.dumps(esc)))
(OUT_MAP / "visor.html").write_text(html, encoding="utf-8")
print("Visor guardado en outputs/maps/visor.html")

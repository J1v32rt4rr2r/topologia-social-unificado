from __future__ import annotations

import json
from datetime import datetime

from topologia.math.operations import detectar_operaciones
from topologia.math.torus import theta_cultura, theta_nodo
from topologia.models.schemas import (
    EstadoCultural,
    Estudio,
    Especulacion,
    InformeDiario,
    ItemInformativo,
    OperacionCinetica,
)
from topologia.paths import get_reportes_dir
from topologia.storage.store import FileStore


TEMPLATE_PANEL = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Panel Orbital - {sociedad}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 20px; }
  h1 { color: #e94560; font-size: 1.5em; margin-bottom: 4px; }
  .subtitle { color: #888; font-size: 0.9em; margin-bottom: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px; }
  .card { background: #1a1a2e; border-radius: 12px; padding: 16px; border: 1px solid #2a2a4a; }
  .card h2 { color: #e94560; font-size: 1em; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
  .delta { font-size: 2.5em; font-weight: bold; }
  .resumen { background: #16213e; border-radius: 8px; padding: 16px; margin-bottom: 20px; border-left: 4px solid #e94560; font-size: 0.95em; line-height: 1.5; }
  .nodo-card { background: #16213e; border-radius: 8px; padding: 12px; border-left: 4px solid #2ecc71; }
  .nodo-card.fragil { border-left-color: #e94560; }
  .nodo-card h4 { font-size: 0.85em; color: #ccc; margin-bottom: 6px; }
  .nodo-card .fuentes { margin-top: 8px; font-size: 0.8em; }
  .nodo-card .fuentes a { color: #4a8cff; text-decoration: none; display: block; padding: 2px 0; }
  .nodo-card .fuentes a:hover { text-decoration: underline; }
  .nodo-card .fuentes summary { cursor: pointer; color: #888; font-size: 0.85em; }
  .orbita-container { width: 100%; height: 500px; position: relative; }
  #orbita-canvas { width: 100%; height: 500px; border-radius: 12px; }
  .slider-container { margin-top: 12px; text-align: center; }
  .slider-container input[type=range] { width: 80%; accent-color: #e94560; }
  .slider-container .fecha-label { color: #e94560; font-weight: bold; font-size: 1.1em; }
  .slider-container .btn { background: #e94560; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer; margin: 0 4px; }
  .slider-container .btn:hover { background: #d63850; }
  .slider-container .era-badge { display:inline-block; background:#e94560; color:#fff; padding:2px 10px; border-radius:10px; font-size:0.8em; margin-left:8px; }
  .ops-list { list-style: none; }
  .ops-list li { padding: 8px; margin-bottom: 6px; background: #16213e; border-radius: 6px; font-size: 0.85em; border-left: 3px solid #e94560; }
  .alert-box { padding: 12px; margin-bottom: 8px; border-radius: 8px; font-size: 0.9em; }
  .alert-critical { background: #2d1a1a; border: 1px solid #e94560; color: #e94560; }
  .alert-warning { background: #2d2d1a; border: 1px solid #f39c12; color: #f39c12; }
  .spec-card { background: #16213e; border-radius: 8px; padding: 12px; margin-bottom: 8px; border-left: 3px solid #4a8cff; font-size: 0.85em; }
  .spec-card.ok { border-left-color: #2ecc71; }
  .spec-card.fail { border-left-color: #e94560; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
  td, th { padding: 6px 8px; text-align: left; border-bottom: 1px solid #2a2a4a; }
  @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } .chart-grid { grid-template-columns: 1fr; } }
  .chart-grid { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; margin-bottom: 20px; }
</style>
</head>
<body>
<h1>Panel Orbital: {sociedad}</h1>
<div class="subtitle" id="subtitle">Cargando... | Era <span id="era-display">1</span></div>

{alertas_html}

{resumen_html}

<div class="chart-grid">
  <div class="card">
    <h2>Diagrama Orbital Cultural</h2>
    <div class="orbita-container">
      <canvas id="orbita-canvas"></canvas>
    </div>
    <div class="slider-container">
      <div>
        <button class="btn" id="playBtn">Reproducir</button>
        <span class="fecha-label" id="fecha-label"></span>
        <span class="era-badge" id="era-badge">Era 1</span>
      </div>
      <input type="range" id="time-slider" min="0" max="0" value="0" step="1">
      <div style="font-size:0.8em;color:#888;margin-top:4px;" id="historial-info"></div>
    </div>
  </div>
  <div class="card">
    <h2>Evolucion</h2>
    <div style="height:200px;"><canvas id="delta-chart"></canvas></div>
    <div style="height:200px;margin-top:8px;"><canvas id="m-chart"></canvas></div>
  </div>
</div>

<div id="nodo-info-panel" class="card" style="margin-bottom:16px;display:none;">
  <h2 id="nodo-info-titulo"></h2>
  <div id="nodo-info-dims"></div>
  <div id="nodo-info-just" style="font-size:0.85em;color:#aaa;max-height:200px;overflow-y:auto;margin-top:8px;"></div>
</div>

<h2 style="margin:20px 0 10px;">Nodos Culturales</h2>
<div class="grid" id="nodos-grid">
{nodos_html}
</div>

{operaciones_html}

{especulaciones_html}

{estudios_html}

<script id="historial-data" type="application/json">{historial_json}</script>

<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>

const historial = JSON.parse(document.getElementById('historial-data').textContent);
const slider = document.getElementById('time-slider');
const fechaLabel = document.getElementById('fecha-label');
const playBtn = document.getElementById('playBtn');
const infoDiv = document.getElementById('historial-info');
const nodoInfo = document.getElementById('nodo-info-panel');
const eraDisplay = document.getElementById('era-display');
const eraBadge = document.getElementById('era-badge');
let scene, camera, renderer, controls;
let nodoGrupos = [];
let ribbonMeshes = [];
let animId = null;
let playing = false;
let playInterval = null;

const NODOS_IDS = ["ECONOMIA","TRABAJO","CONTINUIDAD","POLITICA","LENGUAJE","ETICA_ESTETICA","TECNOLOGIA","EDUCACION","RELIGION"];

if (historial.length === 0) {
  document.getElementById('subtitle').textContent = 'Sin datos historicos';
} else {
  slider.max = historial.length - 1;
  slider.value = historial.length - 1;
  const last = historial[historial.length-1];
  document.getElementById('subtitle').textContent =
    historial.length + ' observaciones | ' + last.fecha;
  if (last.era_k) { eraDisplay.textContent = last.era_k; eraBadge.textContent = 'Era ' + last.era_k; }
}

// ─── Funciones orbitales ───────────────────────────

function anguloDesdeValor(v) { return 360.0 / Math.max(v, 0.1); }

function thetaNodo(ml) { return anguloDesdeValor(ml); }

function thetaCultura(nodos) {
  if (!nodos || nodos.length === 0) return 0;
  const avg = nodos.reduce((s, n) => s + n.l, 0) / nodos.length;
  return anguloDesdeValor(avg);
}

// ─── Colores por nodo ──────────────────────────────

const COLORES_NODO = {
  ECONOMIA: 0x3498db, TRABAJO: 0x2ecc71, CONTINUIDAD: 0x9b59b6,
  POLITICA: 0xe74c3c, LENGUAJE: 0xf39c12, ETICA_ESTETICA: 0x1abc9c,
  TECNOLOGIA: 0xe67e22, EDUCACION: 0x2980b9, RELIGION: 0x8e44ad
};

function colorNodo(id) { return COLORES_NODO[id] || 0x888888; }

// ─── Escena Three.js ───────────────────────────────

function initEscena() {
  const canvas = document.getElementById('orbita-canvas');
  const container = canvas.parentElement;
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f0f1a);
  const w = container.clientWidth, h = 500;
  camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 500);
  camera.position.set(120, 80, 120);
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.8;
  controls.target.set(75, 75, historial.length * 0.5);
  const amb = new THREE.AmbientLight(0x404060, 0.6);
  scene.add(amb);
  const d1 = new THREE.DirectionalLight(0xffffff, 1.2);
  d1.position.set(50, 100, 70);
  scene.add(d1);
  const d2 = new THREE.DirectionalLight(0x4466ff, 0.4);
  d2.position.set(-50, -30, -50);
  scene.add(d2);
  window.addEventListener('resize', () => {
    const w2 = container.clientWidth;
    renderer.setSize(w2, h);
    camera.aspect = w2 / h;
    camera.updateProjectionMatrix();
  });
  dibujarEjes();
  dibujarTraslacion();
}

function dibujarEjes() {
  const len = 120;
  const material = new THREE.LineBasicMaterial({ color: 0x444466, transparent: true, opacity: 0.3 });
  const materialLabel = new THREE.LineBasicMaterial({ color: 0x6666aa });
  const zero = new THREE.Vector3(0, 0, 0);
  const maxZ = Math.max(historial.length - 1, 1);
  const zLen = maxZ + 2;

  // X axis
  const xPts = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(len, 0, 0)];
  scene.add(new THREE.Mesh(new THREE.BufferGeometry().setFromPoints(xPts), materialLabel));
  // Y axis
  const yPts = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, len, 0)];
  scene.add(new THREE.Mesh(new THREE.BufferGeometry().setFromPoints(yPts), materialLabel));
  // Z axis (time)
  const zPts = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, zLen)];
  scene.add(new THREE.Mesh(new THREE.BufferGeometry().setFromPoints(zPts), materialLabel));

  // Grid at z=0
  const gridMat = new THREE.LineBasicMaterial({ color: 0x333355, transparent: true, opacity: 0.2 });
  for (let x = 0; x <= len; x += 20) {
    const pts = [new THREE.Vector3(x, 0, 0), new THREE.Vector3(x, len, 0)];
    scene.add(new THREE.Mesh(new THREE.BufferGeometry().setFromPoints(pts), gridMat));
  }
  for (let y = 0; y <= len; y += 20) {
    const pts = [new THREE.Vector3(0, y, 0), new THREE.Vector3(len, y, 0)];
    scene.add(new THREE.Mesh(new THREE.BufferGeometry().setFromPoints(pts), gridMat));
  }

  // Z-grid lines (connecting planes)
  for (let t = 1; t < maxZ; t++) {
    const planePts = [
      new THREE.Vector3(0, 0, t), new THREE.Vector3(len, 0, t),
      new THREE.Vector3(len, len, t), new THREE.Vector3(0, len, t), new THREE.Vector3(0, 0, t)
    ];
    const geo = new THREE.BufferGeometry().setFromPoints(planePts);
    scene.add(new THREE.Mesh(geo, gridMat));
  }

  // Labels via sprite
  function crearLabel(texto, pos, color='#6666aa') {
    const c = document.createElement('canvas');
    c.width = 128; c.height = 48;
    const ctx = c.getContext('2d');
    ctx.fillStyle = color;
    ctx.font = 'bold 20px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText(texto, 64, 32);
    const tex = new THREE.CanvasTexture(c);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
    sprite.position.set(pos.x, pos.y, pos.z);
    sprite.scale.set(15, 5, 1);
    scene.add(sprite);
  }
  crearLabel('θ nodo →', new THREE.Vector3(len + 5, 0, 0));
  crearLabel('θ cultura ↑', new THREE.Vector3(0, len + 5, 0));
  crearLabel('tiempo', new THREE.Vector3(0, 0, zLen + 0.5));
}

function dibujarTraslacion() {
  if (historial.length < 2) return;
  // Draw line Y = X (cultura-nodo alignment) at each time layer
  const maxZ = Math.max(historial.length - 1, 1);
  const mat = new THREE.LineDashedMaterial({ color: 0x445566, transparent: true, opacity: 0.15, dashSize: 2, gapSize: 2 });
  for (let t = 0; t < maxZ; t++) {
    const pts = [new THREE.Vector3(0, 0, t), new THREE.Vector3(100, 100, t)];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const line = new THREE.Line(geo, mat);
    line.computeLineDistances();
    scene.add(line);
  }
}

// ─── Ribbons (cintas) ───────────────────────────────

function construirCintas() {
  ribbonMeshes.forEach(m => scene.remove(m));
  ribbonMeshes = [];
  if (historial.length < 2) return;

  const puntosPorNodo = {};
  NODOS_IDS.forEach(id => { puntosPorNodo[id] = []; });

  historial.forEach((h, tIdx) => {
    const c = thetaCultura(h.nodos);
    h.nodos.forEach(n => {
      const x = thetaNodo(n.l);
      puntosPorNodo[n.id].push({ x, y: c, z: tIdx, ms: n.s, mm: n.m, delta: n.delta || 0, fragil: n.fragil || false });
    });
  });

  NODOS_IDS.forEach(nodoId => {
    const pts = puntosPorNodo[nodoId];
    if (pts.length < 2) return;
    const color = colorNodo(nodoId);
    const group = new THREE.Group();

    // Ribbon as a TubeGeometry varying radius
    const curvePoints = pts.map(p => new THREE.Vector3(p.x, p.y, p.z));
    if (curvePoints.length < 2) return;

    // Build ribbon as extruded tube using CatmullRomCurve3
    const curve = new THREE.CatmullRomCurve3(curvePoints);
    // Approximate tube with varying radius along path
    const tubularSegments = (pts.length - 1) * 8;
    const radialSegments = 6;
    const vertices = [];
    const indices = [];
    const normals = [];

    for (let i = 0; i <= tubularSegments; i++) {
      const t = i / tubularSegments;
      const pt = curve.getPoint(t);
      const tangent = curve.getTangent(t).normalize();
      const frame = curve.computeFrenetFrames(tubularSegments, false);
      const binormal = frame.binormals ? frame.binormals[Math.min(i, frame.binormals.length - 1)] : new THREE.Vector3(0, 1, 0);
      const normal = new THREE.Vector3().crossVectors(tangent, binormal).normalize();

      // Get thickness from nearest observation point
      const obsIdx = Math.min(Math.floor(t * (pts.length - 1)), pts.length - 2);
      const frac = t * (pts.length - 1) - obsIdx;
      const ms0 = pts[obsIdx].ms;
      const ms1 = pts[Math.min(obsIdx + 1, pts.length - 1)].ms;
      const ms = ms0 + (ms1 - ms0) * frac;
      const radio = Math.max(ms * 0.15, 0.3);

      for (let j = 0; j <= radialSegments; j++) {
        const angle = (j / radialSegments) * Math.PI * 2;
        const rDir = new THREE.Vector3()
          .addScaledVector(normal, Math.cos(angle))
          .addScaledVector(binormal, Math.sin(angle));
        const v = new THREE.Vector3().copy(pt).addScaledVector(rDir, radio);
        vertices.push(v.x, v.y, v.z);
        normals.push(rDir.x, rDir.y, rDir.z);
      }
    }

    for (let i = 0; i < tubularSegments; i++) {
      for (let j = 0; j < radialSegments; j++) {
        const a = i * (radialSegments + 1) + j;
        const b = a + radialSegments + 1;
        indices.push(a, b, a + 1);
        indices.push(b, b + 1, a + 1);
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geo.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    const colorObj = new THREE.Color(color);
    const mat = new THREE.MeshPhongMaterial({
      color: colorObj,
      emissive: colorObj,
      emissiveIntensity: 0.15,
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide,
      wireframe: false,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.userData = { nodoId: nodoId, type: 'ribbon' };
    group.add(mesh);
    ribbonMeshes.push(group);
    scene.add(group);
  });
}

// ─── Nodos en tiempo actual ──────────────────────────

function dibujarNodosEnTiempo(tIdx) {
  nodoGrupos.forEach(g => scene.remove(g));
  nodoGrupos = [];
  const h = historial[tIdx];
  if (!h) return;
  const c = thetaCultura(h.nodos);

  h.nodos.forEach(n => {
    const x = thetaNodo(n.l);
    const y = c;
    const z = tIdx;
    const grupo = new THREE.Group();
    const radio = Math.max(n.s * 0.18, 0.4);
    const colorHex = colorNodo(n.id);
    const color = new THREE.Color(colorHex);
    const esfera = new THREE.Mesh(
      new THREE.SphereGeometry(radio, 20, 20),
      new THREE.MeshPhongMaterial({ color, emissive: color, emissiveIntensity: 0.4 })
    );
    esfera.position.set(x, y, z);
    esfera.userData = { nodoId: n.id };
    grupo.add(esfera);

    // Halo for weight (M_m)
    if (n.m > 3) {
      const halo = new THREE.Mesh(
        new THREE.RingGeometry(radio * 1.4, radio * 1.4 + n.m * 0.08, 24),
        new THREE.MeshBasicMaterial({
          color: 0xe94560,
          transparent: true,
          opacity: Math.min(n.m / 15, 0.5),
          side: THREE.DoubleSide,
        })
      );
      halo.position.set(x, y, z);
      halo.lookAt(camera.position);
      grupo.add(halo);
    }

    // Etiqueta
    const cvs = document.createElement('canvas');
    cvs.width = 256; cvs.height = 64;
    const ctx = cvs.getContext('2d');
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.roundRect(0, 0, 256, 64, 8); ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 22px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText(n.id, 128, 40);
    const tex = new THREE.CanvasTexture(cvs);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
    sprite.position.set(x, y - 1.2, z);
    sprite.scale.set(12, 3, 1);
    grupo.add(sprite);

    // Línea al plano base
    const linea = new THREE.Mesh(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x, y, z), new THREE.Vector3(x, 0, z)
      ]),
      new THREE.LineBasicMaterial({ color: 0x4466aa, transparent: true, opacity: 0.15 })
    );
    grupo.add(linea);

    scene.add(grupo);
    nodoGrupos.push(grupo);
  });
}

// ─── Click en nodos ─────────────────────────────────

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
setTimeout(() => {
  if (!renderer) return;
  renderer.domElement.addEventListener('click', (event) => {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const meshes = [];
    scene.traverse(child => {
      if (child.isMesh && child.geometry?.type === 'SphereGeometry') meshes.push(child);
    });
    const hits = raycaster.intersectObjects(meshes);
    if (hits.length > 0 && hits[0].object.userData?.nodoId) {
      mostrarNodoInfo(hits[0].object.userData.nodoId);
    }
  });
}, 500);

function mostrarNodoInfo(nodoId) {
  const idx = parseInt(slider.value);
  const data = historial[idx];
  if (!data) return;
  const n = data.nodos.find(x => x.id === nodoId);
  if (!n) return;
  nodoInfo.style.display = 'block';
  const tCultura = thetaCultura(data.nodos);
  const tNodo = thetaNodo(n.l);
  const thetaDiff = Math.abs(tCultura - tNodo);
  document.getElementById('nodo-info-titulo').textContent = n.id + ' - ' + data.fecha;
  document.getElementById('nodo-info-dims').innerHTML =
    'θ_nodo: ' + tNodo.toFixed(1) + '° | θ_cultura: ' + tCultura.toFixed(1) + '° | Δθ: ' + thetaDiff.toFixed(1) + '°' +
    ' | M_m: ' + n.m.toFixed(1) + ' | M_l: ' + n.l.toFixed(1) + ' | M_s: ' + n.s.toFixed(1) +
    (n.fragil ? ' | <span style="color:#e94560;">FRAGIL</span>' : '') +
    (n.delta ? ' | δ: ' + n.delta.toFixed(1) + '°' : '');
  let j = '';
  if (n.just_m) j += '<p><strong>M_m:</strong> ' + n.just_m + '</p>';
  if (n.just_l) j += '<p><strong>M_l:</strong> ' + n.just_l + '</p>';
  if (n.just_s) j += '<p><strong>M_s:</strong> ' + n.just_s + '</p>';
  document.getElementById('nodo-info-just').innerHTML = j || '<p style="color:#888;">(dato reconstruido)</p>';
}

// ─── Slider y reproducción ─────────────────────────

function mostrarFecha(idx) {
  const data = historial[idx];
  if (!data) return;
  const c = thetaCultura(data.nodos);
  const titulos = data.nodos.map(n => n.id + ':θ=' + thetaNodo(n.l).toFixed(0) + '°').join(' | ');
  fechaLabel.textContent = data.fecha + ' | θ_cultura=' + c.toFixed(1) + '°';
  infoDiv.textContent = historial.length + ' observaciones | tensión=' + (data.tension || 0).toFixed(0) + ' | ' + titulos;
  if (data.era_k) { eraDisplay.textContent = data.era_k; eraBadge.textContent = 'Era ' + data.era_k; }
  dibujarNodosEnTiempo(idx);
}

slider.addEventListener('input', () => {
  mostrarFecha(parseInt(slider.value));
  mostrarInfoGlobal(parseInt(slider.value));
});

function mostrarInfoGlobal(idx) {
  const data = historial[idx];
  if (!data) return;
  document.querySelectorAll('.nodo-card').forEach(c => c.style.opacity = '0.5');
  data.nodos.forEach(n => {
    const el = document.getElementById('nodo-card-' + n.id);
    if (el) el.style.opacity = '1';
  });
}

function togglePlay() {
  if (playing) {
    clearInterval(playInterval);
    playing = false;
    playBtn.textContent = 'Reproducir';
    controls.autoRotate = true;
  } else {
    playing = true;
    playBtn.textContent = 'Detener';
    controls.autoRotate = false;
    playInterval = setInterval(() => {
      let val = parseInt(slider.value) + 1;
      if (val >= historial.length) val = 0;
      slider.value = val;
      mostrarFecha(val);
    }, 1000);
  }
}

playBtn.addEventListener('click', togglePlay);

// roundRect polyfill
if (!CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function(x,y,w,h,r) {
    this.moveTo(x+r,y); this.lineTo(x+w-r,y);
    this.quadraticCurveTo(x+w,y,x+w,y+r);
    this.lineTo(x+w,y+h-r); this.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    this.lineTo(x+r,y+h); this.quadraticCurveTo(x,y+h,x,y+h-r);
    this.lineTo(x,y+r); this.quadraticCurveTo(x,y,x+r,y);
  };
}

// ─── Inicialización ────────────────────────────────

initEscena();
construirCintas();
if (historial.length > 0) {
  mostrarFecha(parseInt(slider.value));
  mostrarInfoGlobal(parseInt(slider.value));
}

function animar() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(animar);
}
animar();

// Charts
const fechas = historial.map(h => h.fecha.slice(5));
const deltas = historial.map(h => h.delta);
const mm = historial.map(h => h.M_m);
const ml = historial.map(h => h.M_l);
const ms = historial.map(h => h.M_s);

new Chart(document.getElementById('delta-chart'), {
  type: 'line',
  data: { labels: fechas, datasets: [{ label: 'd', data: deltas, borderColor: '#e94560', backgroundColor: 'rgba(233,69,96,0.1)', fill: true, tension: 0.3, pointRadius: 3 }] },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#888', font: { size: 9 } } }, y: { ticks: { color: '#888' } } } }
});

new Chart(document.getElementById('m-chart'), {
  type: 'line',
  data: { labels: fechas, datasets: [
    { label: 'M_m', data: mm, borderColor: '#3498db', tension: 0.3, pointRadius: 2 },
    { label: 'M_l', data: ml, borderColor: '#2ecc71', tension: 0.3, pointRadius: 2 },
    { label: 'M_s', data: ms, borderColor: '#f39c12', tension: 0.3, pointRadius: 2 }
  ] },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#888', font: { size: 9 } } } }, scales: { x: { ticks: { color: '#888', font: { size: 9 } } }, y: { ticks: { color: '#888' } } } }
});
</script>
</body>
</html>"""


def generar_panel(
    sociedad: str = "Chile",
    estado: EstadoCultural | None = None,
    operaciones: list[OperacionCinetica] | None = None,
    especulaciones: list[Especulacion] | None = None,
    estudios: list[Estudio] | None = None,
    items_por_nodo: dict[str, list[ItemInformativo]] | None = None,
    informe_redactor: InformeDiario | None = None,
) -> str:
    store = FileStore()
    if estado is None:
        estado = store.cargar_estado(sociedad)
    if estado is None:
        return ""

    if operaciones is None:
        operaciones = detectar_operaciones(estado)

    # Alertas
    alertas_html = ""
    if informe_redactor and informe_redactor.alertas:
        partes = []
        for a in informe_redactor.alertas:
            cls = "alert-critical" if a.tipo.value == "reconfiguracion" else "alert-warning"
            partes.append(f'<div class="{cls}">{a.mensaje}</div>')
        if partes:
            alertas_html = '<div class="card" style="margin-bottom:16px;">' + "".join(partes) + "</div>"

    # Resumen
    resumen_html = ""
    if informe_redactor and informe_redactor.resumen_ejecutivo:
        resumen_html = f'<div class="resumen"><strong>Resumen:</strong> {informe_redactor.resumen_ejecutivo}</div>'

    # Nodos
    nodos_parts = []
    items_por_nodo = items_por_nodo or {}
    for n in estado.nodos:
        cls = "fragil" if n.fragil else ""
        fuentes = items_por_nodo.get(n.nodo_id, [])
        fuentes_html = ""
        if fuentes:
            items_list = []
            for it in fuentes[:5]:
                if it.url:
                    items_list.append(f'<a href="{it.url}" target="_blank" rel="noopener">{it.titulo}</a>')
                else:
                    items_list.append(f'<span>{it.titulo} ({it.fuente})</span>')
            fuentes_html = f"""
            <div class="fuentes">
              <details><summary>Fuentes ({len(fuentes)})</summary>
                {"".join(items_list)}
              </details>
            </div>"""
        tn = theta_nodo(n.dimension_l)
        tc = theta_cultura([nd.dimension_l for nd in estado.nodos])
        nodos_parts.append(f"""<div class="nodo-card {cls}" id="nodo-card-{n.nodo_id}">
  <h4>{n.nodo_id} <span style="float:right;font-size:0.8em;color:{'#e94560' if n.fragil else '#888'};">θ<sub>n</sub>={tn:.0f}° Δθ={abs(tc-tn):.0f}°</span></h4>
  <table>
    <tr><td>M_m</td><td>{n.dimension_m:.1f}</td><td style="color:#888;">peso</td></tr>
    <tr><td>M_l</td><td>{n.dimension_l:.1f}</td><td style="color:#888;">θ={tn:.0f}°</td></tr>
    <tr><td>M_s</td><td>{n.dimension_s:.1f}</td><td style="color:#888;">volumen</td></tr>
  </table>
  {fuentes_html}
</div>""")

    # Operaciones
    operaciones_html = ""
    if operaciones:
        items = []
        for o in operaciones:
            pct = int(o.intensidad * 100)
            barra = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            items.append(f'<li><strong>{o.codigo}</strong> {o.nombre} <span style="float:right;color:{"#e94560" if o.intensidad > 0.5 else "#888"};">{barra} {pct}%</span><br><span style="font-size:0.8em;color:#888;">Nodos: {", ".join(o.nodos_implicados)} | {o.descripcion}</span></li>')
        operaciones_html = f'<div class="card"><h2>Operaciones Activas</h2><ul class="ops-list">{"".join(items)}</ul></div>'

    # Especulaciones
    especulaciones_html = ""
    if especulaciones:
        items = []
        for e in especulaciones:
            items.append(f"""<div class="spec-card">
  <strong>{e.patron_id}</strong> <span style="float:right;color:#888;">confianza: {e.confianza:.0%}</span>
  <p style="margin:4px 0;font-size:0.85em;">{e.argumento[:200]}</p>
  {f'<span style="font-size:0.8em;color:#888;">Nodos: {", ".join(e.nodos_sugeridos)}</span>' if e.nodos_sugeridos else ''}
  {f'<details style="font-size:0.8em;margin-top:4px;"><summary>Pregunta abierta</summary><p style="color:#888;">{e.pregunta_abierta}</p></details>' if e.pregunta_abierta else ''}
</div>""")
        especulaciones_html = f'<div class="card" style="margin-top:16px;"><h2>Especulaciones del Artista</h2>{"".join(items)}</div>'

    # Estudios
    estudios_html = ""
    if estudios:
        items = []
        for est in estudios:
            veredicto_cls = "ok" if est.veredicto == "validado" else "fail"
            analisis_str = "".join(
                f'<div>{dim}: {"CONFIRMADO" if a.confirmado else "NO"} (confianza: {a.confianza:.0%})<br><span style="color:#aaa;">{a.conclusion[:100]}</span></div>'
                for dim, a in est.analisis.items()
            )
            items.append(f"""<div class="spec-card {veredicto_cls}">
  <strong>{est.patron_id}</strong> -> <strong>{est.veredicto.upper()}</strong>
  <div style="font-size:0.8em;color:#888;margin-top:4px;">{analisis_str}</div>
</div>""")
        estudios_html = f'<div class="card" style="margin-top:16px;"><h2>Estudios</h2>{"".join(items)}</div>'

    # Construir historial completo para el diagrama orbital
    fechas = store.listar_estados(sociedad)
    historial_completo = []
    for f in fechas:
        e = store.cargar_estado(sociedad, f)
        if e:
            nodos_ml = [n.dimension_l for n in e.nodos]
            tc = theta_cultura(nodos_ml)
            historial_completo.append({
                "fecha": f,
                "M_m": e.M_m,
                "M_l": e.M_l,
                "M_s": e.M_s,
                "delta": e.delta_promedio,
                "tension": e.tension_total,
                "era_k": e.era_k,
                "theta_cultura": round(tc, 1),
                "nodos": [
                    {
                        "id": n.nodo_id,
                        "m": n.dimension_m,
                        "l": n.dimension_l,
                        "s": n.dimension_s,
                        "delta": n.delta,
                        "fragil": n.fragil,
                        "just_m": n.justificacion_m,
                        "just_l": n.justificacion_l,
                        "just_s": n.justificacion_s,
                    }
                    for n in e.nodos
                ],
            })

    historial_json = json.dumps(historial_completo, ensure_ascii=False)

    html = TEMPLATE_PANEL.replace("{sociedad}", sociedad)
    html = html.replace("{alertas_html}", alertas_html)
    html = html.replace("{resumen_html}", resumen_html)
    html = html.replace("{nodos_html}", "\n".join(nodos_parts))
    html = html.replace("{operaciones_html}", operaciones_html)
    html = html.replace("{especulaciones_html}", especulaciones_html)
    html = html.replace("{estudios_html}", estudios_html)
    html = html.replace("{historial_json}", historial_json)

    libs_dir = get_reportes_dir().parent / "libs"
    replacements = [
        ('chart.min.js', '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'),
        ('three.min.js', '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>'),
        ('OrbitControls.js', '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>'),
    ]
    for lib_name, tag in replacements:
        lib_path = libs_dir / lib_name
        if lib_path.exists():
            lib_code = lib_path.read_text(encoding="utf-8")
            html = html.replace(tag, "<script>" + lib_code + "</script>")

    ruta = get_reportes_dir()
    ruta.mkdir(parents=True, exist_ok=True)
    archivo = ruta / f"panel_{sociedad}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.html"
    archivo.write_text(html, encoding="utf-8")
    return str(archivo)

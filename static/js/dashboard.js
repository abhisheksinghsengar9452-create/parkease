import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

const toast = document.querySelector('#toast');
let toastTimer;
function notify(message, error = false) {
  toast.textContent = message;
  toast.classList.toggle('error', error);
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3800);
}

async function apiRequest(url, method = 'POST', body = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    }
  };
  if (body) options.body = JSON.stringify(body);
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.error || 'Request failed');
  return payload;
}

let state;

const clockEl = document.querySelector('#clock');
function updateClock() {
  if (clockEl) {
    clockEl.textContent = new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    }).format(new Date());
  }
}
updateClock();
setInterval(updateClock, 1000);

function updateLiveDurations() {
  document.querySelectorAll('.live-duration').forEach(cell => {
    const raw = cell.dataset.entry;
    if (!raw) return;
    const entryTime = new Date(raw.endsWith('Z') || raw.includes('+') ? raw : raw + 'Z').getTime();
    const minutes = Math.max(0, Math.floor((Date.now() - entryTime) / 60000));
    cell.textContent = `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
  });
}
setInterval(updateLiveDurations, 1000);

// ==========================================
// 3D Scene Initialization
// ==========================================
const host = document.querySelector('#scene');
const scene = new THREE.Scene();
const sceneWidth = host?.clientWidth || 800;
const sceneHeight = host?.clientHeight || 450;
const camera = new THREE.PerspectiveCamera(45, sceneWidth / sceneHeight, .1, 100);
camera.position.set(13, 17, 19);

const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(sceneWidth, sceneHeight);
renderer.setClearColor(0x000000, 0);
if (host) host.append(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0, 0);

scene.add(new THREE.HemisphereLight(0x75dfff, 0x07111e, 2.2));
const light = new THREE.DirectionalLight(0x00f0ff, 3);
light.position.set(8, 16, 6);
scene.add(light);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(24, 18), new THREE.MeshStandardMaterial({color: 0x0b1724, roughness: .6, metalness: .3}));
ground.rotation.x = -Math.PI / 2;
ground.position.y = -.12;
scene.add(ground);

const colors = {available: 0x10b981, occupied: 0xf59e0b, maintenance: 0xef4444, unavailable: 0x64748b, ev: 0x00f0ff, vip: 0xf59e0b, disabled: 0x38bdf8};
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let bays = [];
let slotGroup = new THREE.Group();
scene.add(slotGroup);

function makeLabel(label) {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 64;
  const x = c.getContext('2d');
  x.fillStyle = '#dffcff';
  x.font = 'bold 30px monospace';
  x.textAlign = 'center';
  x.fillText(label, 128, 40);
  return new THREE.CanvasTexture(c);
}

function rebuild3DSlots() {
  if (!slotGroup || !state || !state.slots) return;
  while (slotGroup.children.length > 0) {
    const obj = slotGroup.children[0];
    slotGroup.remove(obj);
  }
  bays = [];

  state.slots.forEach((slot, index) => {
    const row = Math.floor(index / 10);
    const col = index % 10;
    const group = new THREE.Group();
    group.position.set((col - 4.5) * 1.55, 0, (row - 0.5) * 3.4);

    let slotColor = colors[slot.status] || colors.available;
    if (slot.status === 'available') {
      if (slot.type === 'ev') slotColor = colors.ev;
      else if (slot.type === 'vip') slotColor = colors.vip;
      else if (slot.type === 'disabled') slotColor = colors.disabled;
    }
    const mat = new THREE.MeshStandardMaterial({
      color: slotColor,
      emissive: slotColor,
      emissiveIntensity: .25,
      roughness: .42,
      metalness: .35
    });
    const bay = new THREE.Mesh(new THREE.BoxGeometry(.86, .12, 2.55), mat);
    bay.userData = slot;
    group.add(bay);

    const lines = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(.9, .15, 2.58)),
      new THREE.LineBasicMaterial({color: slotColor})
    );
    group.add(lines);

    if (slot.status === 'occupied') {
      const car = new THREE.Mesh(
        new THREE.BoxGeometry(.58, .32, 1.35),
        new THREE.MeshStandardMaterial({color: 0x173047, metalness: .7, roughness: .25})
      );
      car.position.y = .28;
      group.add(car);
    }

    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({map: makeLabel(slot.code), transparent: true}));
    sprite.position.set(0, .5, 0);
    sprite.scale.set(.75, .23, 1);
    group.add(sprite);

    slotGroup.add(group);
    bays.push(bay);
  });
}

function selectBayInHud(slot) {
  const hudCode = document.querySelector('#hudBayCode');
  const hudStatus = document.querySelector('#hudBayStatus');
  const hudDot = document.querySelector('#hudDot');
  const hudActions = document.querySelector('#hudBayActions');
  const hudExitBtn = document.querySelector('#hudExitBtn');

  const typeLabel = slot.type === 'ev' ? '⚡ EV Fast Charging' : slot.type === 'vip' ? '👑 VIP Reserved' : slot.type === 'disabled' ? '♿ Accessible' : 'Standard Bay';
  hudCode.textContent = `${slot.code} (Zone ${slot.zone || 'A'})`;
  hudDot.className = `dot ${slot.status}`;
  if (slot.status === 'occupied') {
    hudStatus.innerHTML = `<b>${slot.plate || 'Parked Vehicle'}</b> · ${typeLabel} · Ref: ${slot.session_id || 'Active'}`;
    hudActions.style.display = 'block';
    hudExitBtn.href = `/anpr`;
  } else {
    hudStatus.textContent = `${typeLabel} · ${slot.status === 'available' ? 'Available for Assignment' : slot.status.toUpperCase()}`;
    hudActions.style.display = 'none';
  }
}

host.addEventListener('click', e => {
  const bounds = host.getBoundingClientRect();
  mouse.x = ((e.clientX - bounds.left) / bounds.width) * 2 - 1;
  mouse.y = -((e.clientY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const hit = raycaster.intersectObjects(bays)[0];
  if (!hit) return;
  const slot = hit.object.userData;
  selectBayInHud(slot);

  const typeLabel = slot.type === 'ev' ? '⚡ EV Fast Charging' : slot.type === 'vip' ? '👑 VIP Reserved' : slot.type === 'disabled' ? '♿ Accessible' : 'Standard Bay';
  document.querySelector('#dialogSlot').textContent = `${slot.code} (Zone ${slot.zone || 'A'})`;
  document.querySelector('#dialogContent').innerHTML = `
    <p>Bay Type: <b style="color:#00f0ff;">${typeLabel}</b></p>
    <p>Status: <b class="status ${slot.status}">${slot.status.toUpperCase()}</b></p>
    ${slot.plate ? `<p class="plate">${slot.plate}</p><p>Active session: <code>${slot.session_id}</code></p><p><a class="hud-action-btn" href="/anpr">Process Exit ↗</a></p>` : '<p>No active vehicle session in this bay.</p>'}
  `;
  document.querySelector('#slotDialog').showModal();
});

addEventListener('resize', () => {
  const w = host?.clientWidth || 800;
  const h = host?.clientHeight || 450;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
});

function render() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(render);
}
render();

// ==========================================
// Camera Preset Controls
// ==========================================
document.querySelectorAll('.hud-btn[data-cam]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.hud-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.dataset.cam;
    if (mode === 'top') {
      camera.position.set(0, 22, 0.001);
      controls.target.set(0, 0, 0);
    } else if (mode === 'gate') {
      camera.position.set(-10, 6, 9);
      controls.target.set(0, 0, 0);
    } else {
      camera.position.set(13, 17, 19);
      controls.target.set(0, 0, 0);
    }
  });
});

// ==========================================
// Dashboard DOM Rendering
// ==========================================
function renderDashboard() {
  const icon = {capacity: '🚗', available: '🟢', occupied: '🔴', active_sessions: '⚡', revenue: '₹'};
  const metricNames = {capacity: 'Total Capacity', available: 'Available Slots', occupied: 'Occupied Slots', active_sessions: 'Active Sessions', revenue: "Today's Revenue"};
  const tones = {capacity: '#00f0ff', available: '#10b981', occupied: '#f59e0b', active_sessions: '#00d9ff', revenue: '#10b981'};
  const metricOrder = ['capacity', 'available', 'occupied', 'active_sessions', 'revenue'];

  document.querySelector('#metrics').innerHTML = metricOrder.map(key => `
    <article class="metric glass" style="--tone:${tones[key]}">
      <span class="metric-label">${metricNames[key]}</span>
      <strong>${key === 'revenue' ? '₹' + Number(state.metrics[key]).toLocaleString('en-IN') : state.metrics[key]}</strong>
      <small>${key === 'available' ? 'Ready for assignment' : key === 'occupied' ? 'Currently in use' : key === 'revenue' ? 'Confirmed cash & online totals' : 'Live system total'}</small>
      <i>${icon[key]}</i>
    </article>
  `).join('');

  // Zone status in HUD
  if (state.zones) {
    const parts = Object.entries(state.zones).map(([z, inf]) => `${z}: ${inf.available}/${inf.total} Free`);
    document.querySelector('#zoneStatus').textContent = parts.join(' · ');
  } else {
    const freeSlots = state.slots.filter(s => s.status === 'available').length;
    document.querySelector('#zoneStatus').textContent = `${freeSlots} of ${state.slots.length} Bays Free`;
  }

  // Devices
  const devicesEl = document.querySelector('#devices');
  if (state.devices && state.devices.length) {
    devicesEl.innerHTML = state.devices.map(d => `
      <div class="device">
        <div><b>${d.name}</b><small>${d.detail}</small></div>
        <span class="status ${d.status}">${d.status.toUpperCase()}</span>
      </div>
    `).join('');
  } else {
    devicesEl.innerHTML = `
      <div class="empty-state">
        <b>No IoT devices connected</b>
        <span>Connect an MQTT gateway or use the simulation controls below.</span>
      </div>
    `;
  }

  // Sessions Table
  const sessionRowsEl = document.querySelector('#sessionRows');
  if (state.sessions && state.sessions.length) {
    sessionRowsEl.innerHTML = state.sessions.map(s => `
      <tr>
        <td class="mono">${s.id}</td>
        <td class="mono"><b>${s.plate}</b></td>
        <td>${s.slot}</td>
        <td>${s.entry}</td>
        <td class="live-duration" data-entry="${s.entry_timestamp}">${s.duration}</td>
        <td class="mono">${s.fee}</td>
        <td><span class="payment">${s.payment}</span></td>
        <td><a class="exit" href="/anpr" style="text-decoration:none;">Process exit ↗</a></td>
      </tr>
    `).join('');
  } else {
    sessionRowsEl.innerHTML = `
      <tr class="empty-row">
        <td colspan="8">
          <div class="empty-action-box">
            <p>🚗 No active parking sessions right now.</p>
            <button class="primary" id="btnQuickEntryPrompt" type="button">⚡ Quick Gate Check-In</button>
            <button class="secondary" id="btnSeedDemoPrompt" type="button">Dispatch Demo Traffic</button>
          </div>
        </td>
      </tr>
    `;
    document.querySelector('#btnQuickEntryPrompt')?.addEventListener('click', () => {
      document.querySelector('#anprQuickPlate')?.focus();
    });
    document.querySelector('#btnSeedDemoPrompt')?.addEventListener('click', triggerSeedTraffic);
  }

  // ANPR Card
  const anpr = state.anpr || {};
  document.querySelector('#anprPlate').textContent = anpr.plate || 'Ready for vehicle';
  document.querySelector('#cameraPlate').textContent = anpr.plate || 'Ready for vehicle';
  document.querySelector('#confidence').textContent = `${anpr.confidence || 96.8}%`;
  document.querySelector('#confidenceBar').style.width = `${anpr.confidence || 96.8}%`;
  if (anpr.status) {
    document.querySelector('#cameraStatusBadge').innerHTML = `<i></i>${anpr.status}`;
  }

  rebuild3DSlots();
  updateLiveDurations();
}

// ==========================================
// Instant ANPR Check-In & Gate Trigger
// ==========================================
async function performInstantCheckIn(plateInput = '') {
  const cameraBox = document.querySelector('.camera');
  cameraBox.classList.add('scanning-active');
  try {
    const result = await apiRequest('/api/anpr/instant-entry', 'POST', {plate: plateInput});
    notify(result.message);
    document.querySelector('#anprQuickPlate').value = '';
    await fetchState();
  } catch (err) {
    notify(err.message, true);
  } finally {
    cameraBox.classList.remove('scanning-active');
  }
}

document.querySelector('#btnInstantScan')?.addEventListener('click', () => {
  const plate = document.querySelector('#anprQuickPlate').value.trim();
  performInstantCheckIn(plate);
});

document.querySelector('#anprQuickPlate')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    performInstantCheckIn(e.target.value.trim());
  }
});

document.querySelector('#btnSimulateTrigger')?.addEventListener('click', () => {
  notify('Gate 01 camera optical sensor triggered. Recognizing plate...');
  performInstantCheckIn('');
});

// ==========================================
// Barrier Controls
// ==========================================
document.querySelectorAll('.barrier-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const barrier = btn.dataset.barrier;
    const action = btn.dataset.action;
    btn.disabled = true;
    try {
      const res = await apiRequest('/api/devices/barrier/operate', 'POST', {barrier, action});
      notify(res.message);
      await fetchState();
    } catch (err) {
      notify(err.message, true);
    } finally {
      btn.disabled = false;
    }
  });
});

// ==========================================
// Demo Traffic Generator
// ==========================================
async function triggerSeedTraffic() {
  try {
    const res = await apiRequest('/api/demo/seed-traffic', 'POST');
    notify(res.message);
    await fetchState();
  } catch (err) {
    notify(err.message, true);
  }
}
document.querySelector('#btnSeedDemo')?.addEventListener('click', triggerSeedTraffic);

// ==========================================
// Quick Search Modal (Command Palette)
// ==========================================
const searchDialog = document.querySelector('#searchDialog');
const searchInput = document.querySelector('#searchInput');
const searchResults = document.querySelector('#searchResults');

document.querySelector('#searchBtn')?.addEventListener('click', () => {
  searchDialog.showModal();
  searchInput.focus();
});

addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    if (searchDialog.open) searchDialog.close();
    else {
      searchDialog.showModal();
      searchInput.focus();
    }
  }
});

let searchTimer;
searchInput?.addEventListener('input', () => {
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (!q) {
    searchResults.innerHTML = '<p class="search-empty">Type a vehicle plate, bay code (e.g. A-01), or session ID...</p>';
    return;
  }
  searchTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      let html = '';
      if (data.vehicles?.length) {
        html += `<div class="search-group"><div class="search-group-title">VEHICLES</div>`;
        html += data.vehicles.map(v => `<a class="search-item" href="/vehicles"><span>🚗 ${v.registration}</span><small>${v.type}</small></a>`).join('');
        html += `</div>`;
      }
      if (data.sessions?.length) {
        html += `<div class="search-group"><div class="search-group-title">PARKING SESSIONS</div>`;
        html += data.sessions.map(s => `<a class="search-item" href="/anpr"><span>🏷️ ${s.id} (${s.plate})</span><small>Bay: ${s.slot} · ${s.status}</small></a>`).join('');
        html += `</div>`;
      }
      if (data.slots?.length) {
        html += `<div class="search-group"><div class="search-group-title">PARKING BAYS</div>`;
        html += data.slots.map(sl => `<a class="search-item" href="/slots"><span>🅿️ ${sl.code} (Zone ${sl.zone})</span><small class="status ${sl.status}">${sl.status}</small></a>`).join('');
        html += `</div>`;
      }
      if (data.devices?.length) {
        html += `<div class="search-group"><div class="search-group-title">HARDWARE DEVICES</div>`;
        html += data.devices.map(d => `<a class="search-item" href="/hardware"><span>⌁ ${d.name} (${d.code})</span><small class="status ${d.status}">${d.status}</small></a>`).join('');
        html += `</div>`;
      }
      if (!html) {
        html = `<p class="search-empty">No results found matching "${q}".</p>`;
      }
      searchResults.innerHTML = html;
    } catch (e) {
      searchResults.innerHTML = '<p class="search-empty">Search query error.</p>';
    }
  }, 180);
});

// ==========================================
// Notifications Flyout
// ==========================================
const notifDialog = document.querySelector('#notifDialog');
const notifList = document.querySelector('#notifList');

document.querySelector('#notifBtn')?.addEventListener('click', async () => {
  notifDialog.showModal();
  notifList.innerHTML = '<p class="search-empty">Loading audit events...</p>';
  try {
    const res = await fetch('/api/notifications');
    const logs = await res.json();
    if (logs.length) {
      notifList.innerHTML = logs.map(l => `
        <div class="notif-card">
          <b>${l.action}</b>
          <small>${l.time} · Actor: ${l.actor} · Entity: ${l.entity} (${l.entity_id})</small>
        </div>
      `).join('');
    } else {
      notifList.innerHTML = '<p class="search-empty">No recent system notifications.</p>';
    }
  } catch (err) {
    notifList.innerHTML = '<p class="search-empty">Could not load notifications.</p>';
  }
});

// ==========================================
// Device Guide Modal
// ==========================================
const deviceGuideDialog = document.querySelector('#deviceGuideDialog');
document.querySelector('#deviceMoreBtn')?.addEventListener('click', () => {
  deviceGuideDialog.showModal();
});

// Sidebar toggle
document.querySelector('#sidebarToggle')?.addEventListener('click', () => {
  document.querySelector('#sidebar').classList.toggle('collapsed');
  document.body.classList.toggle('sidebar-collapsed');
  setTimeout(() => dispatchEvent(new Event('resize')), 180);
});

// ==========================================
// Dashboard State Loader & Polling
// ==========================================
async function fetchState(isInitial = false) {
  try {
    const response = await fetch('/api/dashboard/state');
    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = '/login';
        return;
      }
      throw new Error(`Server returned HTTP ${response.status}`);
    }
    state = await response.json();
    renderDashboard();
  } catch (err) {
    console.error('Failed to load dashboard state:', err);
    if (isInitial && !state) {
      throw err;
    }
  }
}

try {
  await fetchState(true);
  setInterval(() => fetchState(false), 5000);
} catch (error) {
  console.error('ParkEase dashboard initialization error:', error);
  document.body.innerHTML = `
    <main class="load-error">
      <h1>ParkEase could not load live data.</h1>
      <p>${error.message || 'Please refresh the page or verify the MySQL connection.'}</p>
      <p style="margin-top:1.5rem;"><a href="/" style="display:inline-block;padding:.6rem 1.4rem;background:#00f0ff;color:#050c14;border-radius:8px;font-weight:700;text-decoration:none;">Retry Connection</a></p>
    </main>
  `;
}

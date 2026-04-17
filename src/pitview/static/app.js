'use strict';

// --- Navigation ---
const pages = document.querySelectorAll('.page');
const navBtns = document.querySelectorAll('.nav-btn');

navBtns.forEach(btn => btn.addEventListener('click', () => {
  const target = btn.dataset.page;
  pages.forEach(p => p.classList.toggle('active', p.id === `page-${target}`));
  navBtns.forEach(b => b.classList.toggle('active', b === btn));

  // Lazy-load iframes on first visit using server-injected URLs
  if (target === 'photonvision') {
    const frame = document.getElementById('frame-photon');
    if (!frame.src || frame.src === 'about:blank') frame.src = frame.dataset.url;
  }
  if (target === 'radio') {
    const frame = document.getElementById('frame-radio');
    if (!frame.src || frame.src === 'about:blank') frame.src = frame.dataset.url;
  }
}));

// --- State ---
let ntValues = {};
let rioState = {};

// --- NT key buckets for Dashboard ---
const DRIVE_KEYS = ['/swervelib/', '/SmartDashboard/Swerve/', '/photonvision/'];
const VISION_KEYS = ['/photonvision/', '/Vision/', '/SmartDashboard/Vision'];
const MATCH_KEYS = ['/FMSInfo/', '/DriverStation/', '/SmartDashboard/Match'];
const SUBSYSTEM_KEYS = ['/SmartDashboard/', '/LiveWindow/'];

function keyBucket(key) {
  if (VISION_KEYS.some(p => key.startsWith(p))) return 'vision';
  if (key.startsWith('/FMSInfo/') || key.startsWith('/DriverStation/')) return 'match';
  if (key.startsWith('/swervelib/') || key.includes('Swerve')) return 'drive';
  return 'subsystems';
}

function renderKV(containerId, entries) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = entries.slice(0, 20).map(([k, v]) => {
    const shortKey = k.split('/').pop();
    const display = formatVal(v);
    const cls = typeof v === 'boolean' ? (v ? 'bool-true' : 'bool-false') : '';
    return `<div class="kv-row"><span class="kv-key" title="${k}">${shortKey}</span><span class="kv-val ${cls}">${display}</span></div>`;
  }).join('') || '<span class="dim">No data</span>';
}

function formatVal(v) {
  if (v === null || v === undefined) return '--';
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  if (typeof v === 'number') return Number.isInteger(v) ? v : v.toFixed(3);
  if (Array.isArray(v)) return `[${v.slice(0, 4).map(x => typeof x === 'number' ? x.toFixed(2) : x).join(', ')}${v.length > 4 ? '...' : ''}]`;
  if (typeof v === 'string' && v.length > 40) return v.slice(0, 40) + '…';
  return String(v);
}

function updateDashboard() {
  const entries = Object.entries(ntValues);
  renderKV('kv-drive', entries.filter(([k]) => keyBucket(k) === 'drive'));
  renderKV('kv-vision', entries.filter(([k]) => keyBucket(k) === 'vision'));
  renderKV('kv-match', entries.filter(([k]) => keyBucket(k) === 'match'));
  renderKV('kv-subsystems', entries.filter(([k]) => keyBucket(k) === 'subsystems'));

  // Status bar
  const battery = ntValues['/DriverStation/BatteryVoltage'] ?? ntValues['/SmartDashboard/Battery'];
  document.getElementById('battery').textContent = battery != null ? `${Number(battery).toFixed(2)}V` : '--V';

  const mode = ntValues['/DriverStation/Enabled']
    ? (ntValues['/DriverStation/Autonomous'] ? 'AUTO' : 'TELEOP')
    : 'DISABLED';
  const modeEl = document.getElementById('robot-mode');
  modeEl.textContent = mode;
  modeEl.style.color = mode === 'DISABLED' ? 'var(--dim)' : mode === 'AUTO' ? 'var(--yellow)' : 'var(--green)';

  const mt = ntValues['/FMSInfo/MatchTime'];
  if (mt != null) {
    const s = Math.max(0, Math.floor(Number(mt)));
    document.getElementById('match-time').textContent = `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  }
}

function updateNtExplorer() {
  const filter = document.getElementById('nt-filter').value.toLowerCase();
  const entries = Object.entries(ntValues).filter(([k]) => !filter || k.toLowerCase().includes(filter));
  document.getElementById('nt-count').textContent = `${entries.length} keys`;
  document.getElementById('nt-tree').innerHTML = entries.map(([k, v]) =>
    `<div class="nt-entry"><span class="nt-topic">${k}</span><span class="nt-value">${formatVal(v)}</span></div>`
  ).join('');
}

function updateSystem() {
  const s = rioState.system || {};
  const pct = v => v != null ? `${Number(v).toFixed(1)}%` : '--';
  const entries = [
    ['CPU', pct(s.cpu_percent)],
    ['Memory', pct(s.memory_percent)],
    ['Disk', pct(s.disk_percent)],
    ['Uptime', s.uptime ? `${Math.floor(s.uptime / 60)}m` : '--'],
  ];
  renderKV('kv-rio', entries.map(([k, v]) => [`/${k}`, v]));
  renderKV('kv-can', [
    ['/CAN Utilization', s.can_utilization != null ? pct(s.can_utilization) : '--'],
  ]);
}

document.getElementById('nt-filter').addEventListener('input', updateNtExplorer);

// --- WebSocket ---
function connect() {
  const ws = new WebSocket(`ws://127.0.0.1:${location.port || 8765}/ws`);

  ws.onopen = () => {};

  ws.onmessage = e => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'snapshot') {
      ntValues = msg.nt || {};
      rioState = msg.rio || {};
      setNtConnected(msg.nt_connected);
      setRioConnected(rioState.reachable);
      updateDashboard();
      updateNtExplorer();
      updateSystem();
      return;
    }

    if (msg.type === 'value') {
      ntValues[msg.key] = msg.value;
      updateDashboard();
      // NT explorer: only update if visible
      if (document.getElementById('page-nt').classList.contains('active')) updateNtExplorer();
      return;
    }

    if (msg.type === 'connection') {
      setNtConnected(msg.connected);
      return;
    }

    if (msg.type === 'rio') {
      rioState = msg;
      setRioConnected(msg.reachable);
      updateSystem();
      return;
    }
  };

  ws.onclose = () => {
    setNtConnected(false);
    setRioConnected(false);
    setTimeout(connect, 2000);
  };
}

function setNtConnected(v) {
  const el = document.getElementById('conn-nt');
  el.className = `badge ${v ? 'connected' : 'disconnected'}`;
}

function setRioConnected(v) {
  const el = document.getElementById('conn-rio');
  el.className = `badge ${v ? 'connected' : 'disconnected'}`;
}

connect();

// ============================================================
// static/js/app.js — Core Utilities
// ============================================================

// --- API Helper ---
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...opts,
  });
  if (res.status === 401) {
    window.location.href = '/auth/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// --- Toast ---
function toast(title, msg, type = 'success') {
  const container = document.getElementById('toasts');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<div class="toast-title">${title}</div><div class="toast-msg">${msg}</div>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// --- Modal ---
function openModal(id) { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-overlay').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) m.classList.remove('open'); });
  });
});

// --- Clock ---
function updateClock() {
  const el = document.getElementById('live-clock');
  if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// --- Badges ---
function priorityBadge(p) {
  return `<span class="badge badge-${p}">${p.charAt(0).toUpperCase() + p.slice(1)}</span>`;
}
function typeBadge(t) {
  return t === 'telemedicine'
    ? '<span class="badge badge-tele">Telemedicine</span>'
    : '<span class="badge badge-normal">In-Person</span>';
}
function statusBadge(s) {
  const map = { waiting: 'urgent', called: 'tele', completed: 'normal', cancelled: 'critical', scheduled: 'normal' };
  return `<span class="badge badge-${map[s] || 'normal'}">${s.charAt(0).toUpperCase() + s.slice(1)}</span>`;
}

// --- Time formatting ---
function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

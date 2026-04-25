// ============================================================
// static/js/socket.js — SocketIO Client
// ============================================================

let socket = null;

function initSocket(hospitalId) {
  if (!window.io) return;
  socket = io({ transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    console.log('[Socket] Connected:', socket.id);
    socket.emit('join_hospital', { hospital_id: hospitalId });
  });

  socket.on('joined', (data) => {
    console.log('[Socket] Joined room:', data.room);
  });

  // Queue updated — call whatever refresh functions the page defines
  socket.on('queue_updated', (data) => {
    console.log('[Socket] Queue updated', data);
    if (typeof refreshQueue === 'function')  refreshQueue();
    if (typeof refreshStats  === 'function')  refreshStats();
  });

  // New activity log item — prepend to all feed-list elements
  socket.on('new_activity', (data) => {
    if (!data || !data.message) return;
    console.log('[Socket] Activity:', data.message);
    document.querySelectorAll('.feed-list').forEach(list => {
      const item = document.createElement('div');
      item.className = 'feed-item anim-slide';
      item.innerHTML = `${data.message}<div class="time">just now</div>`;
      list.prepend(item);
      // Cap feed at 30 items
      while (list.children.length > 30) list.lastChild.remove();
    });
  });

  // Patient-specific: notify when their token is called
  socket.on('patient_called', (data) => {
    console.log('[Socket] Patient called:', data);
    // Show prominent alert if this is the patient's token
    const myTokenEl = document.getElementById('my-token');
    if (myTokenEl && myTokenEl.textContent === data.token) {
      _showCalledAlert(data.token);
    }
  });

  socket.on('disconnect', (reason) => {
    console.warn('[Socket] Disconnected:', reason);
  });

  socket.on('connect_error', (err) => {
    console.warn('[Socket] Connection error:', err.message);
  });
}

// Show a full-screen alert when the patient's token is called
function _showCalledAlert(token) {
  let overlay = document.getElementById('_called-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = '_called-overlay';
    overlay.style.cssText = [
      'position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999',
      'display:flex;flex-direction:column;align-items:center;justify-content:center',
      'animation:fadeIn 0.4s ease;cursor:pointer'
    ].join(';');
    overlay.onclick = () => overlay.remove();
    document.body.appendChild(overlay);
  }
  overlay.innerHTML = `
    <div style="text-align:center;padding:40px">
      <div style="font-size:64px;margin-bottom:16px">📣</div>
      <div style="font-family:var(--font-head);font-size:48px;font-weight:800;color:var(--accent);
                  text-shadow:0 0 40px rgba(0,212,255,0.5);animation:pulse 1s infinite">${token}</div>
      <div style="font-size:20px;margin-top:16px;color:var(--text)">Your token is being called!</div>
      <div style="font-size:14px;color:var(--muted);margin-top:8px">Please proceed to the doctor's room</div>
      <div style="margin-top:32px;font-size:12px;color:var(--muted)">Tap anywhere to dismiss</div>
    </div>`;
}

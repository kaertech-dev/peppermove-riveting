const $ = id => document.getElementById(id);

let state = {
  loggedIn:         false,
  operator:         '',
  shift:            'A',
  mode:             'production',   // 'development' | 'production'
  showModeSelector: false,
};

// ── DOM ──
const inpEmp       = $('inp-emp');
const inpShift     = $('inp-shift');
const inpSerial    = $('inp-serial');
const inpSize      = $('inp-size');
const btnLogin     = $('btn-login');
const btnSubmit    = $('btn-submit');
const sbText       = $('sb-text');
const statusLbl    = $('status-label');
const tblBody      = $('tbl-body');
const modeRow      = $('mode-row');
const modeSelect   = $('inp-mode');
const modeBadge    = $('mode-badge');

function setStatus(msg, type = '') {
  statusLbl.textContent = msg;
  statusLbl.className = 'status-label' + (type ? ' ' + type : '');
}

function setSB(msg) { sbText.textContent = msg; }

function setScanEnabled(on) {
  inpSerial.disabled = !on;
  inpSize.disabled   = !on;
  btnSubmit.disabled = !on;
}

function applyMode(mode) {
  state.mode = mode;
  const isDev = mode === 'development';
  modeBadge.textContent  = isDev ? '⚠ DEVELOPMENT' : '✔ PRODUCTION';
  modeBadge.className    = 'mode-badge ' + (isDev ? 'dev' : 'prod');
  modeBadge.style.display = state.showModeSelector ? '' : 'none';
  setSB(`Logged in: ${state.operator} | Shift: ${state.shift} | Mode: ${mode.toUpperCase()}`);
  // Reload the table to show correct data set
  loadRecords();
}

// ── Load suit sizes ──
async function loadSizes() {
  try {
    const res  = await fetch('/api/suit-sizes');
    const data = await res.json();
    if (data.ok && data.sizes.length) {
      inpSize.innerHTML = data.sizes
        .map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join('');
    } else {
      inpSize.innerHTML = '<option>(no sizes loaded)</option>';
    }
  } catch { inpSize.innerHTML = '<option>(error)</option>'; }
}

// ── Load table ──
async function loadRecords() {
  try {
    const params = new URLSearchParams({
      limit: 200,
      mode: state.mode,
      operator_en: state.operator,
    });
    const res  = await fetch(`/api/records?${params.toString()}`);
    const data = await res.json();
    if (!data.ok || !data.records.length) {
      tblBody.innerHTML = '<tr class="empty-row"><td colspan="8">No records yet.</td></tr>';
      return;
    }
    tblBody.innerHTML = data.records.map(r => {
      const st = r.status == 1 ? '<span class="td-pass">1</span>' : '<span class="td-fail">0</span>';
      return `<tr>
        <td>${esc(r.serial_num||'')}</td>
        <td>${esc(r.po_num||'')}</td>
        <td>${esc(r.operator_en||'')}</td>
        <td>${esc(r.shift||'')}</td>
        <td>${esc(r.date_time||'')}</td>
        <td>${esc(r.suit_size||'')}</td>
        <td>${esc(r.remarks||'')}</td>
        <td>${st}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    tblBody.innerHTML = `<tr class="empty-row"><td colspan="8">Error: ${esc(e.message)}</td></tr>`;
  }
}

// ── Login ──
async function doLogin() {
  const emp = inpEmp.value.trim().toUpperCase();
  if (!emp) { setStatus('Please enter your employee number.', 'warn'); return; }

  btnLogin.disabled = true;
  btnLogin.innerHTML = '<span class="spin"></span>…';

  try {
    const res  = await fetch('/api/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ employee_num: emp }),
    });
    const data = await res.json();

    if (!data.ok) {
      setStatus(data.error, 'err');
      btnLogin.disabled   = false;
      btnLogin.textContent = 'login';
      return;
    }

    state.loggedIn         = true;
    state.operator         = emp;
    state.shift            = inpShift.value;
    state.showModeSelector = !!data.show_mode_selector;

    inpEmp.disabled    = true;
    inpShift.disabled  = true;
    btnLogin.textContent = '✓ logged in';
    btnLogin.className   = 'btn-login logged-in';

    // Show mode selector row only for KE0412
    if (state.showModeSelector) {
      modeRow.style.display = '';
      modeSelect.disabled   = false;
      state.mode = modeSelect.value;   // respect current dropdown value
    } else {
      modeRow.style.display = 'none';
      state.mode = 'production';
    }

    applyMode(state.mode);
    setScanEnabled(true);
    inpSerial.focus();
    setStatus(`Welcome, ${emp}! Scan a serial number.`, 'ok');

  } catch (e) {
    setStatus(`Network error: ${e.message}`, 'err');
    btnLogin.disabled   = false;
    btnLogin.textContent = 'login';
  }
}

// ── Scan (Enter in serial field) ──
async function doScanCheck() {
  if (!state.loggedIn) return;
  const serial = inpSerial.value.trim();
  if (!serial) return;

  setStatus('Looking up serial…');
  try {
    const res  = await fetch('/api/check-serial', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ serial_num: serial }),
    });
    const data = await res.json();
    if (!data.ok) { setStatus(data.error, 'err'); inpSerial.select(); return; }
    setStatus(`✔ Serial '${serial}' found & test passed. Select size & submit.`, 'ok');
  } catch (e) { setStatus(`Network error: ${e.message}`, 'err'); }
}

// ── Submit ──
async function doSubmit() {
  if (!state.loggedIn) return;
  const serial = inpSerial.value.trim();
  const size   = inpSize.value.trim();
  if (!serial) { setStatus('Please scan a serial number.', 'warn'); return; }
  if (!size || size === '(no sizes loaded)') { setStatus('Please select a valid suit size.', 'warn'); return; }

  btnSubmit.disabled = true;
  btnSubmit.innerHTML = '<span class="spin"></span>…';
  setStatus('Saving…');

  try {
    const res  = await fetch('/api/submit', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        serial_num:  serial,
        suit_size:   size,
        operator_en: state.operator,
        shift:       state.shift,
        mode:        state.mode,
      }),
    });
    const data = await res.json();

    if (!data.ok) {
      setStatus(data.error, 'err');
      btnSubmit.disabled   = false;
      btnSubmit.textContent = 'Submit';
      return;
    }

    // Trust the mode the server actually used, not just what we asked for
    const effectiveMode = data.mode || state.mode;
    const modeTag = state.showModeSelector ? ` [${effectiveMode.toUpperCase()}]` : '';
    setStatus(`✔ Saved!${modeTag}  Serial: ${serial}  |  Size: ${size}  |  PO: ${data.po_num||'—'}`, 'ok');
    setSB(`Logged in: ${state.operator} | Shift: ${state.shift} | Last: ${serial} | Mode: ${effectiveMode.toUpperCase()}`);
    inpSerial.value = '';
    inpSerial.focus();
    btnSubmit.disabled   = false;
    btnSubmit.textContent = 'Submit';
    loadRecords();

  } catch (e) {
    setStatus(`Network error: ${e.message}`, 'err');
    btnSubmit.disabled   = false;
    btnSubmit.textContent = 'Submit';
  }
}

function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Events ──
btnLogin.addEventListener('click', doLogin);
inpEmp.addEventListener('keydown',    e => e.key === 'Enter' && doLogin());
inpSerial.addEventListener('keydown', e => e.key === 'Enter' && doScanCheck());
btnSubmit.addEventListener('click',   doSubmit);
inpEmp.addEventListener('input', () => { inpEmp.value = inpEmp.value.toUpperCase(); });
modeSelect.addEventListener('change', () => {
  if (state.loggedIn && state.showModeSelector) applyMode(modeSelect.value);
});

// ── Init ──
loadSizes();
loadRecords();
inpEmp.focus();
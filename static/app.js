const appRoot = document.getElementById('app');
const modalRoot = document.getElementById('modal-root');
const toastRoot = document.getElementById('toast');
const state = {
  user: null,
  csrf: '',
  page: 'servers',
  server: null,
  serverTab: 'Overview',
  serverData: null,
  filePath: '',
  fileContentPath: '',
  editorSavedContent: '',
  editorLanguage: '',
  fileSearch: '',
  consoleTimer: null,
  settings: null,
};

const SOFTWARE_OPTIONS = [
  { id: 'paper', name: 'PaperMC', image: 'paper.svg' },
  { id: 'purpur', name: 'PurpurMC', image: 'purpur.svg' },
  { id: 'vanilla', name: 'Vanilla', image: 'vanilla.svg' },
  { id: 'folia', name: 'FoliaMC', image: 'folia.svg' },
  { id: 'forge', name: 'Forge', image: 'forge.svg' },
  { id: 'neoforge', name: 'NeoForge', image: 'neoforge.svg' },
  { id: 'fabric', name: 'Fabric', image: 'fabric.svg' },
  { id: 'mohist', name: 'Mohist', image: 'mohist.svg' },
  { id: 'arclight', name: 'Arclight', image: 'arclight.svg' },
];

const icons = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  servers: '<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/>',
  console: '<path d="m5 7 5 5-5 5"/><path d="M12 17h7"/><rect x="3" y="3" width="18" height="18" rx="4"/>',
  files: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/>',
  versions: '<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z"/><path d="m8 9 4-2 4 2v6l-4 2-4-2z"/><path d="m4 8 8 4 8-4"/>',
  plugins: '<path d="M9 4V2m6 2V2M9 22v-2m6 2v-2M4 9H2m2 6H2m20-6h-2m2 6h-2"/><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 9h6v6H9z"/>',
  admin: '<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.6.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.6-.9l-1.7.7-1.4-2.4L7.5 15a8 8 0 0 1 0-1.9l-1.4-1.2 1.4-2.4 1.7.7a8 8 0 0 1 1.6-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.6.9l1.7-.7 1.4 2.4-1.4 1.2a8 8 0 0 1-.1 1.9z"/>',
  logout: '<path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/>',
  play: '<path d="m8 5 11 7-11 7z"/>',
  restart: '<path d="M20 7v5h-5"/><path d="M20 12a8 8 0 1 1-2.3-5.7L20 9"/>',
  stop: '<circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  newFolder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 11v6m-3-3h6"/>',
  newFile: '<path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10z"/><path d="M13 3v7h7m-8 3v6m-3-3h6"/>',
  upload: '<path d="M12 16V4m-5 5 5-5 5 5"/><path d="M4 17v3h16v-3"/>',
  uploadFolder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 17v-6m-3 3 3-3 3 3"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/>',
  file: '<path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10z"/><path d="M13 3v7h7"/>',
  archive: '<path d="M3 4h18v5H3z"/><path d="M5 9v11h14V9m-7 0v7m-2-2 2 2 2-2"/>',
  extract: '<path d="M3 4h18v5H3z"/><path d="M5 9v11h14V9m-7 7V9m-3 4 3-4 3 4"/>',
  rename: '<path d="M4 20h4l11-11a2.8 2.8 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>',
  delete: '<path d="M3 6h18m-2 0-1 14H6L5 6m4 0V4h6v2m-5 4v6m4-6v6"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
  download: '<path d="M12 4v12m-5-5 5 5 5-5"/><path d="M4 19h16"/>',
  activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  backup: '<path d="M4 7h16v13H4z"/><path d="M8 7V4h8v3m-4 4v5m-2-2 2 2 2-2"/>',
  network: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',
  schedule: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2M8 2v3m8-3v3"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.6.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.6-.9l-1.7.7-1.4-2.4L7.5 15a8 8 0 0 1 0-1.9l-1.4-1.2 1.4-2.4 1.7.7a8 8 0 0 1 1.6-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.6.9l1.7-.7 1.4 2.4-1.4 1.2a8 8 0 0 1-.1 1.9z"/>',
  startup: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="11" cy="18" r="2"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
};

function icon(name, size = 18) {
  return `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || ''}</svg>`;
}

function softwareInfo(id) {
  return SOFTWARE_OPTIONS.find(software => software.id === id) || { name: id, image: 'vanilla.svg' };
}

function softwareImage(id, className = 'software-choice-image') {
  const software = softwareInfo(id);
  return `<img class="${className}" src="/static/software/${software.image}" alt="">`;
}

function softwareChoiceButtons(selected, attribute) {
  return SOFTWARE_OPTIONS.map(software => `<button type="button" class="software-choice ${software.id === selected ? 'active' : ''}" ${attribute}="${software.id}" aria-pressed="${software.id === selected}">
    ${softwareImage(software.id)}<span>${software.name}</span>
  </button>`).join('');
}

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

function toast(message, error = false) {
  toastRoot.textContent = message;
  toastRoot.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { toastRoot.className = 'toast'; }, 3400);
}

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (!['GET', 'HEAD'].includes((options.method || 'GET').toUpperCase()) && state.csrf) {
    headers.set('X-CSRF-Token', state.csrf);
  }
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Error HTTP ${response.status}`);
  return data;
}

function setTheme(theme, accentColor = state.settings?.accentColor || '', buttonStyle = state.settings?.buttonStyle || 'Gradient', backgroundStyle = state.settings?.backgroundStyle || 'Gradient', backgroundStart = state.settings?.backgroundStart || '#151027', backgroundEnd = state.settings?.backgroundEnd || '#211644') {
  document.body.dataset.theme = theme || 'Purple';
  document.body.dataset.buttonStyle = buttonStyle;
  document.body.dataset.appearance = backgroundStyle;
  if (/^#[\da-f]{6}$/i.test(accentColor)) document.body.style.setProperty('--accent', accentColor);
  else document.body.style.removeProperty('--accent');
  if (/^#[\da-f]{6}$/i.test(backgroundStart) && /^#[\da-f]{6}$/i.test(backgroundEnd)) {
    document.body.style.setProperty('--background-start', backgroundStart);
    document.body.style.setProperty('--background-end', backgroundEnd);
  }
}

function stopPolling() {
  clearInterval(state.consoleTimer);
  state.consoleTimer = null;
}

function authPage(setup = false, registrationEnabled = true) {
  stopPolling();
  appRoot.innerHTML = `
    <main class="auth-screen">
      <section class="auth-card">
        <div class="brand">${brandMark()}<span>NexoryPanel</span></div>
        <h1>${setup ? 'Crea el nodo principal' : 'Hola de nuevo'}</h1>
        <p class="sub">${setup ? 'Tu primera cuenta tendrá permisos de administrador.' : 'Inicia sesión para administrar tus servidores.'}</p>
        <form id="auth-form">
          ${setup ? `<label class="field">Nombre del usuario<input class="input" name="username" autocomplete="username" minlength="3" maxlength="24" required placeholder="admin"></label>` : `<label class="field">Usuario<input class="input" name="username" autocomplete="username" required placeholder="Tu usuario"></label>`}
          <label class="field">Contraseña<input class="input" name="password" type="password" autocomplete="${setup ? 'new-password' : 'current-password'}" minlength="${setup ? 10 : 1}" required placeholder="${setup ? 'Mínimo 10 caracteres' : 'Tu contraseña'}"></label>
          ${setup ? `<label class="field">Confirmar contraseña<input class="input" name="confirm" type="password" autocomplete="new-password" minlength="10" required placeholder="Repite la contraseña"></label>` : ''}
          <button class="btn btn-primary btn-block" type="submit">${setup ? 'Crear cuenta de administrador' : 'Iniciar sesión'} <span>→</span></button>
        </form>
        ${setup || !registrationEnabled ? '' : `<p class="auth-foot">¿Todavía no tienes cuenta? <button id="show-register" class="text-button">Regístrate</button></p>`}
        ${!setup && registrationEnabled ? '' : !setup ? `<p class="auth-foot">El registro está desactivado por el administrador.</p>` : ''}
        ${setup ? '<div class="notice">NexoryPanel funciona localmente en este PC. Guarda tus credenciales; no existe una recuperación de contraseña configurada.</div>' : ''}
        <div id="auth-error"></div>
      </section>
    </main>`;

  document.getElementById('auth-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (setup && form.get('password') !== form.get('confirm')) {
      document.getElementById('auth-error').innerHTML = '<div class="notice">Las contraseñas no coinciden.</div>';
      return;
    }
    const endpoint = setup || event.currentTarget.dataset.register === 'true' ? '/api/register' : '/api/login';
    try {
      const result = await api(endpoint, {
        method: 'POST',
        body: JSON.stringify({ username: form.get('username'), password: form.get('password') }),
      });
      state.user = result.user;
      state.csrf = result.csrfToken;
      state.page = 'servers';
      state.settings = { theme: 'Purple', accentColor: '', buttonStyle: 'Gradient', backgroundStyle: 'Gradient', backgroundStart: '#151027', backgroundEnd: '#211644', announcement: '', discordUrl: '', customLinks: [], nodeName: 'Nexory Node', platformLabel: 'Windows' };
      setTheme('Purple');
      renderShell();
    } catch (error) {
      document.getElementById('auth-error').innerHTML = `<div class="notice">${esc(error.message)}</div>`;
    }
  });
  document.getElementById('show-register')?.addEventListener('click', () => {
    authPage(false, true);
    const form = document.getElementById('auth-form');
    form.dataset.register = 'true';
    form.querySelector('label.field').innerHTML = 'Nombre del usuario<input class="input" name="username" autocomplete="username" minlength="3" maxlength="24" required placeholder="Tu usuario">';
    form.querySelector('input[name="password"]').autocomplete = 'new-password';
    form.querySelector('input[name="password"]').minLength = 10;
    form.querySelector('input[name="password"]').placeholder = 'Mínimo 10 caracteres';
    const confirm = document.createElement('label');
    confirm.className = 'field';
    confirm.innerHTML = 'Confirmar contraseña<input class="input" name="confirm" type="password" autocomplete="new-password" minlength="10" required placeholder="Repite la contraseña">';
    form.insertBefore(confirm, form.querySelector('button'));
    form.querySelector('button').innerHTML = 'Crear cuenta <span>→</span>';
    document.querySelector('.auth-card h1').textContent = 'Crea tu cuenta';
    document.querySelector('.auth-card .sub').textContent = 'Regístrate para acceder al panel.';
    document.querySelector('.auth-foot')?.remove();
    form.addEventListener('submit', event => {
      const data = new FormData(form);
      if (data.get('password') !== data.get('confirm')) {
        event.preventDefault();
        document.getElementById('auth-error').innerHTML = '<div class="notice">Las contraseñas no coinciden.</div>';
      }
    }, { once: true });
  });
}

function navButton(page, label, icon) {
  return `<button class="nav-item ${state.page === page ? 'active' : ''}" data-page="${page}"><span class="nav-icon">${icon}</span>${label}</button>`;
}

function brandMark() {
  return `<span class="brand-mark"><img class="brand-icon" src="/api/branding/icon" alt=""></span>`;
}

function serverTabLabel(tab) {
  return ({
    Overview: 'Dashboard', Console: 'Consola', Files: 'Archivos', Versions: 'Versiones',
    Plugins: 'Plugins', Backups: 'Backups', Activity: 'Actividad', Databases: 'Base de datos',
    Network: 'Network', Schedules: 'Schedules', Users: 'Users', Startup: 'Startup', Settings: 'Settings',
  })[tab] || tab;
}

function renderShell() {
  stopPolling();
  const isAdmin = state.user?.role === 'admin';
  const inServer = Boolean(state.server);
  const currentTab = state.serverTab;
  const panelSidebar = `
    <div class="side-brand"><div class="brand">${brandMark()}<span>NexoryPanel</span></div></div>
    <div class="nav-caption">PANEL</div>
    <nav class="nav">
      ${navButton('servers', 'Servidores', icon('servers'))}
      ${isAdmin ? navButton('admin', 'Administración', icon('admin')) : ''}
    </nav>
    <div class="nav-caption">NODO LOCAL</div>
    <div class="notice" style="margin:5px 7px">◉ &nbsp;${esc(state.settings?.nodeName || 'Nexory Node')}<br><span class="tiny muted">127.0.0.1 · ${esc(state.settings?.platformLabel || 'Windows')}</span></div>`;
  const serverSidebar = inServer ? `
    <div class="side-brand server-side-brand">
      <button class="server-brand-back" data-page="servers" title="Volver a servidores">${brandMark()}<span>NexoryPanel</span></button>
    </div>
    <div class="server-side-summary">
      <div class="row between"><strong>${esc(state.server.name)}</strong><span class="status ${state.server.status === 'online' ? 'online' : ''}"></span></div>
      <div class="server-side-address">${icon('servers', 14)} 127.0.0.1:${state.server.port}</div>
      <div class="server-power-actions">
        <button class="power-icon power-start" data-side-power="start" title="Iniciar servidor" aria-label="Iniciar servidor">${icon('play')}</button>
        <button class="power-icon power-restart" data-side-power="restart" title="Reiniciar servidor" aria-label="Reiniciar servidor">${icon('restart')}</button>
        <button class="power-icon power-stop" data-side-power="stop" title="Detener servidor" aria-label="Detener servidor">${icon('stop')}</button>
      </div>
    </div>
    <div class="nav-caption">GENERAL</div>
    <nav class="nav server-nav">
      ${serverNavButton('Overview', 'Dashboard', icon('dashboard'))}
      ${serverNavButton('Console', 'Consola', icon('console'))}
    </nav>
    <div class="nav-caption">GESTIÓN</div>
    <nav class="nav server-nav">
      ${serverNavButton('Files', 'Archivos', icon('files'))}
      ${serverNavButton('Versions', 'Versiones', icon('versions'))}
      ${serverNavButton('Plugins', 'Plugins', icon('plugins'))}
      ${serverNavButton('Backups', 'Backups', icon('backup'))}
      ${serverNavButton('Network', 'Network', icon('network'))}
      ${serverNavButton('Schedules', 'Schedules', icon('schedule'))}
      ${serverNavButton('Databases', 'Base de datos', icon('database'))}
      ${serverNavButton('Activity', 'Actividad', icon('activity'))}
      ${serverNavButton('Users', 'Users', icon('users'))}
      ${serverNavButton('Startup', 'Startup', icon('startup'))}
      ${serverNavButton('Settings', 'Settings', icon('settings'))}
    </nav>` : '';
  appRoot.innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        ${inServer ? serverSidebar : panelSidebar}
        <div class="side-bottom"><div class="account-row"><div><div class="account-name">${esc(state.user?.username)}</div><div class="tiny">${isAdmin ? 'Administrador' : 'Usuario'}</div></div><button id="logout" class="btn btn-quiet" title="Cerrar sesión">${icon('logout')}</button></div></div>
      </aside>
      <main class="main">
        <header class="topbar">
          <div class="row"><button id="mobile-menu" class="btn btn-quiet mobile-menu">☰</button><span class="top-title">${state.page === 'admin' ? 'Administración del nodo' : state.server ? `${esc(state.server.name)} / ${esc(serverTabLabel(currentTab))}` : 'Mis servidores'}</span></div>
          <div class="top-right">${state.settings?.discordUrl ? `<a class="header-link" href="${esc(state.settings.discordUrl)}" target="_blank" rel="noopener noreferrer">Discord ↗</a>` : ''}${(state.settings?.customLinks || []).map(link => `<a class="header-link" href="${esc(link.url)}" target="_blank" rel="noopener noreferrer">${esc(link.label)} ↗</a>`).join('')}<span>${new Date().toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}</span><span class="badge">${esc(state.user?.role)}</span></div>
        </header>
        ${state.settings?.announcement ? `<div class="announcement-bar"><span>${icon('activity', 16)}${esc(state.settings.announcement)}</span></div>` : ''}
        <section id="content" class="content"></section>
      </main>
    </div>`;
  appRoot.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => {
    if (editorIsDirty() && !confirm('Tienes cambios sin guardar. ¿Salir del editor?')) return;
    state.page = button.dataset.page;
    state.server = null;
    renderShell();
    renderPage();
    document.body.classList.remove('nav-open');
  }));
  appRoot.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => {
    if (editorIsDirty() && !confirm('Tienes cambios sin guardar. ¿Salir del editor?')) return;
    state.serverTab = button.dataset.tab;
    state.fileContentPath = '';
    renderShell();
    document.body.classList.remove('nav-open');
  }));
  appRoot.querySelectorAll('[data-side-power]').forEach(button => button.addEventListener('click', () => powerServer(button.dataset.sidePower)));
  document.getElementById('mobile-menu').addEventListener('click', () => document.body.classList.toggle('nav-open'));
  document.getElementById('logout').addEventListener('click', async () => {
    try {
      const result = await api('/api/logout', { method: 'POST', body: '{}' });
      state.csrf = result.csrfToken;
    } catch (error) { toast(error.message, true); }
    state.user = null;
    authPage(false, true);
  });
  renderPage();
}

function serverNavButton(tab, label, svg) {
  return `<button class="nav-item ${state.serverTab === tab ? 'active' : ''}" data-tab="${tab}"><span class="nav-icon">${svg}</span>${label}</button>`;
}

function pageHeading(title, description, action = '') {
  return `<div class="page-heading"><div><div class="eyebrow">NEXORY / ${state.page === 'admin' ? 'ADMIN' : 'SERVERS'}</div><h1>${title}</h1><p>${description}</p></div>${action}</div>`;
}

function statCard(label, value, note, icon) {
  return `<div class="card stat-card"><div><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-note">${note}</div></div><span class="stat-icon">${icon}</span></div>`;
}

async function renderPage() {
  stopPolling();
  setTheme(state.settings?.theme || 'Purple');
  const content = document.getElementById('content');
  if (!content) return;
  if (state.page === 'admin') return renderAdmin();
  if (state.server) return renderServer();
  content.innerHTML = '<div class="empty"><span class="empty-icon">◌</span><span>Cargando servidores…</span></div>';
  try {
    const servers = await api('/api/servers');
    const online = servers.filter(server => server.status === 'online').length;
    const ram = servers.reduce((total, server) => total + server.ram_mb, 0);
    const disk = servers.reduce((total, server) => total + server.disk_mb, 0);
    content.innerHTML = `
      ${pageHeading('Mis servidores', 'Administra tu infraestructura de Minecraft desde un solo lugar.', state.user.role === 'admin' ? '<button id="create-server" class="btn btn-primary">＋ Crear servidor</button>' : '')}
      <div class="grid stat-grid">
        ${statCard('SERVIDORES', servers.length, `${online} en ejecución`, '▦')}
        ${statCard('RAM ASIGNADA', `${(ram / 1024).toFixed(1)} GiB`, 'Límites definidos por nodo', '▤')}
        ${statCard('DISCO ASIGNADO', `${(disk / 1024).toFixed(1)} GiB`, 'Cuota por servidor', '▱')}
        ${statCard('ESTADO DEL NODO', 'Activo', `Ejecución local en ${esc(state.settings?.platformLabel || 'Windows')}`, '◇')}
      </div>
      <div class="section-title"><div><h2>Instancias</h2><p>Servidores disponibles para tu cuenta</p></div><span class="badge">${servers.length} total</span></div>
      ${servers.length ? `<div class="grid server-grid">${servers.map(serverCard).join('')}</div>` : `<div class="card empty"><span class="empty-icon">⬡</span><strong>Aún no hay servidores</strong><span>${state.user.role === 'admin' ? 'Crea el primer servidor y elige su software, versión y recursos.' : 'Un administrador deberá asignarte un servidor.'}</span>${state.user.role === 'admin' ? '<button id="create-server-empty" class="btn btn-primary mt">Crear primer servidor</button>' : ''}</div>`}`;
    document.getElementById('create-server')?.addEventListener('click', openCreateServer);
    document.getElementById('create-server-empty')?.addEventListener('click', openCreateServer);
    content.querySelectorAll('[data-server]').forEach(button => button.addEventListener('click', () => {
      state.server = servers.find(server => server.id === button.dataset.server);
      state.serverTab = 'Overview';
      state.filePath = '';
      renderShell();
    }));
    content.querySelectorAll('[data-delete-server]').forEach(button => button.addEventListener('click', async event => {
      event.stopPropagation();
      const server = servers.find(item => item.id === button.dataset.deleteServer);
      if (!confirm(`¿Eliminar "${server.name}" y todos sus archivos?`)) return;
      try {
        await api(`/api/servers/${server.id}`, { method: 'DELETE' });
        toast('Servidor eliminado.');
        renderPage();
      } catch (error) { toast(error.message, true); }
    }));
  } catch (error) {
    content.innerHTML = `<div class="card empty"><strong>No se pudo cargar el panel</strong><span>${esc(error.message)}</span></div>`;
  }
}

function serverCard(server) {
  const status = server.status === 'online' ? 'online' : server.status === 'starting' ? 'starting' : '';
  const software = softwareInfo(server.software);
  return `<article class="card server-card">
    <div class="server-banner"><div class="server-software">${server.icon ? `<img class="software-mark server-custom-icon" src="${esc(server.icon)}" alt="">` : softwareImage(server.software, 'software-mark')}<div><h3>${esc(server.name)}</h3><p>${esc(software.name)} · ${esc(server.version)}${server.build ? ` · build ${esc(server.build)}` : ''}</p>${server.description ? `<p>${esc(server.description)}</p>` : ''}</div></div></div>
    <div class="server-body">
      <div class="server-meta"><span>IP <strong>127.0.0.1:${server.port}</strong></span><span>CPU <strong>${Number(server.cpu || 0).toFixed(1)}%</strong></span><span>RAM <strong>${server.memory || 0} / ${server.ram_mb} MiB</strong></span><span>Disco <strong>${server.diskUsed} / ${server.disk_mb} MiB</strong></span>${server.owner_name ? `<span>Usuario <strong>${esc(server.owner_name)}</strong></span>` : ''}</div>
      <div class="server-actions"><span class="status ${status}">${server.status === 'online' ? 'En línea' : server.status === 'starting' ? 'Iniciando' : 'Apagado'}</span><div class="row"><button class="btn btn-primary" data-server="${esc(server.id)}">Administrar →</button>${state.user.role === 'admin' ? `<button class="btn btn-danger" data-delete-server="${esc(server.id)}" title="Eliminar servidor">×</button>` : ''}</div></div>
    </div>
  </article>`;
}

function versionId(item) {
  if (typeof item === 'string') return item;
  if (!item || typeof item !== 'object') return '';
  if (typeof item.version === 'string') return item.version;
  if (item.version && typeof item.version.id === 'string') return item.version.id;
  return typeof item.id === 'string' ? item.id : '';
}

function serverTabButton(tab) {
  return `<button class="tab ${state.serverTab === tab ? 'active' : ''}" data-tab="${tab}">${({ Overview: 'Resumen', Console: 'Consola', Files: 'Archivos', Versions: 'Versiones', Plugins: 'Plugins' })[tab] || tab}</button>`;
}

async function refreshServer() {
  const servers = await api('/api/servers');
  state.server = servers.find(item => item.id === state.server.id) || state.server;
}

async function renderServer() {
  stopPolling();
  const content = document.getElementById('content');
  if (!state.server) return renderPage();
  await refreshServer().catch(() => {});
  const server = state.server;
  content.innerHTML = `
    ${pageHeading(esc(server.name), `${esc(server.software)} · Minecraft ${esc(server.version)}${server.build ? ` · build ${esc(server.build)}` : ''}`)}
    <div class="server-detail-banner"><div><h2>${esc(server.name)}</h2><p>127.0.0.1:${server.port} &nbsp;·&nbsp; ${esc(server.owner_name || state.user.username)}</p></div><span class="status ${server.status === 'online' ? 'online' : ''}">${server.status === 'online' ? 'En línea' : 'Apagado'}</span></div>
    <div id="server-tab-content"></div>`;
  const tabRenderers = {
    Activity: renderActivity, Backups: renderBackups, Databases: renderDatabases,
    Network: renderNetwork, Schedules: renderSchedules, Users: renderServerUsers,
    Startup: renderStartup, Settings: renderServerSettings,
  };
  if (state.serverTab === 'Console') return renderConsole();
  if (state.serverTab === 'Files') return renderFiles();
  if (state.serverTab === 'Versions') return renderVersions();
  if (state.serverTab === 'Plugins') return renderPlugins();
  if (tabRenderers[state.serverTab]) return tabRenderers[state.serverTab]();
  document.getElementById('server-tab-content').innerHTML = `
    <div class="grid stat-grid">${statCard('CPU', `${Number(server.cpu || 0).toFixed(1)}%`, 'Uso del proceso del servidor', '⌁')}${statCard('RAM', `${server.memory || 0} MiB`, `Límite ${server.ram_mb} MiB`, '▤')}${statCard('ALMACENAMIENTO', `${server.diskUsed} MiB`, `Límite ${server.disk_mb} MiB`, '▱')}${statCard('DIRECCIÓN LOCAL', `:${server.port}`, 'Solo accesible en este PC por defecto', '◇')}</div>
    <div class="grid admin-grid"><div class="card"><div class="section-title"><h2>Configuración</h2><span class="badge">${esc(server.software)}</span></div><div class="toggle-row"><div class="toggle-copy"><strong>Dirección local</strong><span>El panel no abre el puerto a Internet automáticamente.</span></div><span class="code-token">127.0.0.1:${server.port}</span></div><div class="toggle-row"><div class="toggle-copy"><strong>Versión</strong><span>${esc(server.version)} ${server.build ? `· build ${esc(server.build)}` : ''}</span></div><button class="btn" data-goto-tab="Versions">Cambiar</button></div></div>
    <div class="card"><div class="section-title"><h2>Uso del almacenamiento</h2></div><div class="row between tiny"><span>Ocupado</span><span>${server.diskUsed} / ${server.disk_mb} MiB</span></div><div class="progress mt"><i style="width:${Math.min(100, server.diskUsed / server.disk_mb * 100)}%"></i></div><div class="notice">La cuota se aplica al sistema de archivos gestionado por NexoryPanel.</div></div></div>`;
  document.querySelector('[data-goto-tab="Versions"]').addEventListener('click', () => { state.serverTab = 'Versions'; renderShell(); });
}

function serverModuleHeading(title, description, iconName) {
  return `<div class="module-heading"><span class="module-icon">${icon(iconName, 19)}</span><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div></div>`;
}

async function renderActivity() {
  const box = document.getElementById('server-tab-content');
  try {
    const events = await api(`/api/servers/${state.server.id}/activity`);
    box.innerHTML = `${serverModuleHeading('Actividad', 'Registro de acciones realizadas en este servidor.', 'activity')}
      <section class="card"><div class="table-wrap"><table><thead><tr><th>Usuario</th><th>Evento</th><th>Detalle</th><th>Fecha</th></tr></thead><tbody>${events.length ? events.map(event => `<tr><td>${esc(event.username)}</td><td><span class="event-badge">${esc(event.action)}</span></td><td>${esc(event.detail)}</td><td>${esc(event.created_at)}</td></tr>`).join('') : '<tr><td colspan="4" class="empty-row">Aún no hay actividad registrada.</td></tr>'}</tbody></table></div></section>`;
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderBackups() {
  const box = document.getElementById('server-tab-content');
  try {
    const backups = await api(`/api/servers/${state.server.id}/backups`);
    box.innerHTML = `${serverModuleHeading('Backups', 'Crea, descarga y elimina copias de seguridad del servidor.', 'backup')}
      <section class="card"><div class="section-title"><div><h2>Copias de seguridad</h2><p>El servidor debe estar apagado para crear una copia consistente.</p></div><button id="create-backup" class="btn btn-primary" ${state.server.status === 'online' ? 'disabled' : ''}>${icon('backup', 16)} Crear backup</button></div>
      <div class="table-wrap"><table><thead><tr><th>Archivo</th><th>Tamaño</th><th>Creado</th><th></th></tr></thead><tbody>${backups.length ? backups.map(item => `<tr><td>${esc(item.filename)}</td><td>${(item.size_bytes / 1048576).toFixed(1)} MiB</td><td>${esc(item.created_at)}</td><td class="table-actions"><a class="btn" href="/api/servers/${state.server.id}/backups/${item.id}">${icon('download', 15)} Descargar</a><button class="btn btn-danger" data-remove-backup="${item.id}">Eliminar</button></td></tr>`).join('') : '<tr><td colspan="4" class="empty-row">No hay copias de seguridad todavía.</td></tr>'}</tbody></table></div></section>`;
    document.getElementById('create-backup').addEventListener('click', async () => {
      try { await api(`/api/servers/${state.server.id}/backups`, { method: 'POST', body: '{}' }); toast('Backup creado.'); renderBackups(); }
      catch (error) { toast(error.message, true); }
    });
    box.querySelectorAll('[data-remove-backup]').forEach(button => button.addEventListener('click', async () => {
      if (!confirm('¿Eliminar este backup permanentemente?')) return;
      try { await api(`/api/servers/${state.server.id}/backups/${button.dataset.removeBackup}`, { method: 'DELETE' }); toast('Backup eliminado.'); renderBackups(); }
      catch (error) { toast(error.message, true); }
    }));
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderNetwork() {
  const box = document.getElementById('server-tab-content');
  try {
    const data = await api(`/api/servers/${state.server.id}/network`);
    const firewallNote = data.firewallManaged
      ? `Las reglas entrantes usan el perfil <strong>${esc(data.firewallProfile)}</strong> configurado por el administrador. Windows puede requerir que ejecutes NexoryPanel como administrador. Abrir puertos puede exponer servicios a otros equipos de la red.`
      : 'NexoryPanel registra los puertos, pero no cambia el firewall del sistema en macOS/Linux. Configura el acceso de red por separado antes de permitir conexiones externas.';
    box.innerHTML = `${serverModuleHeading('Network', data.firewallManaged ? 'Administra puertos y reglas de Windows Firewall.' : 'Administra las asignaciones de puertos de tu servidor.', 'network')}
      <div class="notice">${firewallNote}</div>
      <section class="card mt"><div class="section-title"><div><h2>Puertos asignados</h2><p>El puerto principal de Minecraft ya está reservado.</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>Puerto</th><th>Protocolo</th><th>Descripción</th><th>${data.firewallManaged ? 'Regla del Firewall' : 'Gestión de red'}</th><th></th></tr></thead><tbody>${data.ports.map(port => `<tr><td>${port.port}</td><td>${esc(port.protocol)}</td><td>${esc(port.description)}</td><td>${port.primary ? 'Principal' : esc(port.firewall_profile === 'Manual' ? 'Manual' : port.firewall_profile)}</td><td>${port.primary ? '<span class="badge">Principal</span>' : `<button class="btn btn-danger" data-remove-port="${esc(port.id)}">${data.firewallManaged ? 'Cerrar puerto' : 'Quitar asignación'}</button>`}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card mt"><div class="section-title"><div><h2>Añadir puerto</h2><p>${data.firewallManaged ? 'La regla se crea explícitamente al guardar.' : 'El puerto se registra aquí; configura el firewall del sistema manualmente si lo necesitas.'}</p></div></div><form id="network-form" class="form-grid">
      <label class="field">Puerto<input class="input" type="number" name="port" min="1024" max="65535" required placeholder="25575"></label>
      <label class="field">Protocolo<select class="select" name="protocol"><option>TCP</option><option>UDP</option></select></label>
      <label class="field">Descripción<input class="input" name="description" maxlength="80" placeholder="RCON, query, plugin..."></label>
      <div class="field form-end"><span></span><button class="btn btn-primary">${icon('network', 15)} Crear regla</button></div></form></section>`;
    document.getElementById('network-form').addEventListener('submit', async event => {
      event.preventDefault();
      const body = Object.fromEntries(new FormData(event.currentTarget)); body.port = Number(body.port);
      try { await api(`/api/servers/${state.server.id}/network`, { method: 'POST', body: JSON.stringify(body) }); toast(data.firewallManaged ? 'Puerto asignado y regla de Firewall creada.' : 'Puerto asignado al servidor.'); renderNetwork(); }
      catch (error) { toast(error.message, true); }
    });
    box.querySelectorAll('[data-remove-port]').forEach(button => button.addEventListener('click', async () => {
      if (!confirm(data.firewallManaged ? '¿Eliminar la regla entrante de Windows Firewall para este puerto?' : '¿Quitar esta asignación de puerto?')) return;
      try { await api(`/api/servers/${state.server.id}/network/${button.dataset.removePort}`, { method: 'DELETE' }); toast(data.firewallManaged ? 'Regla eliminada y puerto cerrado.' : 'Asignación de puerto eliminada.'); renderNetwork(); }
      catch (error) { toast(error.message, true); }
    }));
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderSchedules() {
  const box = document.getElementById('server-tab-content');
  try {
    const schedules = await api(`/api/servers/${state.server.id}/schedules`);
    const actionNames = { start: 'Iniciar', stop: 'Detener', restart: 'Reiniciar', command: 'Comando' };
    box.innerHTML = `${serverModuleHeading('Schedules', 'Programa tareas recurrentes mientras NexoryPanel esté en ejecución.', 'schedule')}
      <section class="card"><div class="section-title"><div><h2>Tareas programadas</h2><p>Los intervalos se repiten; la próxima ejecución se calcula desde la creación.</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>Nombre</th><th>Acción</th><th>Intervalo</th><th>Próxima ejecución</th><th></th></tr></thead><tbody>${schedules.length ? schedules.map(item => `<tr><td>${esc(item.name)}</td><td>${actionNames[item.action]}${item.action === 'command' ? ` · ${esc(item.command)}` : ''}</td><td>Cada ${item.interval_minutes} min</td><td>${new Date(item.next_run_at * 1000).toLocaleString('es-ES')}</td><td><button class="btn btn-danger" data-remove-schedule="${item.id}">Eliminar</button></td></tr>`).join('') : '<tr><td colspan="5" class="empty-row">No hay tareas programadas.</td></tr>'}</tbody></table></div></section>
      <section class="card mt"><div class="section-title"><div><h2>Crear schedule</h2><p>La cola se ejecuta localmente en segundo plano.</p></div></div>
      <form id="schedule-form" class="form-grid"><label class="field">Nombre<input class="input" name="name" required maxlength="60" placeholder="Reinicio nocturno"></label>
      <label class="field">Acción<select class="select" name="action" id="schedule-action"><option value="restart">Reiniciar</option><option value="start">Iniciar</option><option value="stop">Detener</option><option value="command">Enviar comando</option></select></label>
      <label class="field">Intervalo (minutos)<input class="input" type="number" name="intervalMinutes" min="1" max="525600" value="60" required></label>
      <label class="field" id="schedule-command-field" hidden>Comando<input class="input" name="command" maxlength="256" placeholder="say Reinicio programado"></label>
      <div class="field form-end"><span></span><button class="btn btn-primary">${icon('schedule', 15)} Crear schedule</button></div></form></section>`;
    const actionSelect = document.getElementById('schedule-action');
    const commandField = document.getElementById('schedule-command-field');
    actionSelect.addEventListener('change', () => { commandField.hidden = actionSelect.value !== 'command'; });
    document.getElementById('schedule-form').addEventListener('submit', async event => {
      event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); values.intervalMinutes = Number(values.intervalMinutes);
      try { await api(`/api/servers/${state.server.id}/schedules`, { method: 'POST', body: JSON.stringify(values) }); toast('Schedule creado.'); renderSchedules(); }
      catch (error) { toast(error.message, true); }
    });
    box.querySelectorAll('[data-remove-schedule]').forEach(button => button.addEventListener('click', async () => {
      try { await api(`/api/servers/${state.server.id}/schedules/${button.dataset.removeSchedule}`, { method: 'DELETE' }); toast('Schedule eliminado.'); renderSchedules(); }
      catch (error) { toast(error.message, true); }
    }));
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderServerUsers() {
  const box = document.getElementById('server-tab-content');
  try {
    const data = await api(`/api/servers/${state.server.id}/members`);
    const candidates = data.canManage ? await api(`/api/servers/${state.server.id}/members/candidates`) : [];
    box.innerHTML = `${serverModuleHeading('Users', 'Concede a otras cuentas NexoryPanel acceso para administrar este servidor.', 'users')}
      <section class="card"><div class="section-title"><div><h2>Personas con acceso</h2><p>Los colaboradores pueden gestionar los módulos y el servidor.</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>Cuenta</th><th>Acceso</th><th>Desde</th><th></th></tr></thead><tbody><tr><td>${esc(state.server.owner_name || 'Propietario')}</td><td><span class="badge">Propietario</span></td><td>—</td><td></td></tr>${data.members.map(member => `<tr><td>${esc(member.username)}</td><td><span class="badge">Administrador del servidor</span></td><td>${esc(member.created_at)}</td><td>${data.canManage ? `<button class="btn btn-danger" data-revoke-user="${esc(member.id)}">Revocar</button>` : ''}</td></tr>`).join('')}${!data.members.length ? '<tr><td colspan="4" class="empty-row">Todavía no hay colaboradores.</td></tr>' : ''}</tbody></table></div></section>
      ${data.canManage ? `<section class="card mt"><div class="section-title"><div><h2>Añadir cuenta</h2><p>Solo puedes asignar cuentas ya registradas en este panel.</p></div></div><form id="add-member-form" class="form-grid"><label class="field">Usuario<select class="select" name="userId" required>${candidates.map(user => `<option value="${esc(user.id)}">${esc(user.username)}</option>`).join('')}</select></label><div class="field form-end"><span></span><button class="btn btn-primary" ${candidates.length ? '' : 'disabled'}>Conceder acceso</button></div></form></section>` : ''}`;
    document.getElementById('add-member-form')?.addEventListener('submit', async event => {
      event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
      try { await api(`/api/servers/${state.server.id}/members`, { method: 'POST', body: JSON.stringify(values) }); toast('Acceso concedido.'); renderServerUsers(); }
      catch (error) { toast(error.message, true); }
    });
    box.querySelectorAll('[data-revoke-user]').forEach(button => button.addEventListener('click', async () => {
      if (!confirm('¿Revocar el acceso de esta cuenta al servidor?')) return;
      try { await api(`/api/servers/${state.server.id}/members/${button.dataset.revokeUser}`, { method: 'DELETE' }); toast('Acceso revocado.'); renderServerUsers(); }
      catch (error) { toast(error.message, true); }
    }));
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderStartup() {
  const box = document.getElementById('server-tab-content');
  try {
    const settings = await api(`/api/servers/${state.server.id}/settings`);
    box.innerHTML = `${serverModuleHeading('Startup', 'Configura los argumentos de Java del proceso del servidor.', 'startup')}
      <section class="card"><form id="startup-form"><label class="field">Argumentos JVM<input class="input" name="javaArgs" maxlength="400" value="${esc(settings.javaArgs)}" placeholder="-Xms256M -Xmx{ram}M"></label>
      <div class="notice">Usa <code>{ram}</code> para insertar el límite asignado en MiB. No se permite cambiar el ejecutable, el JAR ni añadir comandos externos.</div>
      <button class="btn btn-primary mt">Guardar startup</button></form></section>`;
    document.getElementById('startup-form').addEventListener('submit', async event => {
      event.preventDefault();
      try { await api(`/api/servers/${state.server.id}/settings`, { method: 'PUT', body: JSON.stringify({ ...settings, javaArgs: new FormData(event.currentTarget).get('javaArgs') }) }); toast('Startup guardado.'); }
      catch (error) { toast(error.message, true); }
    });
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderServerSettings() {
  const box = document.getElementById('server-tab-content');
  try {
    const settings = await api(`/api/servers/${state.server.id}/settings`);
    box.innerHTML = `${serverModuleHeading('Settings', 'Detalles y personalización de esta instancia.', 'settings')}
      <div class="grid admin-grid"><section class="card"><div class="section-title"><div><h2>Detalles del servidor</h2><p>Actualiza el nombre y la descripción visibles en el panel.</p></div></div>
      <form id="server-settings-form"><label class="field">Nombre<input class="input" name="name" maxlength="48" required value="${esc(settings.name)}"></label><label class="field">Descripción<textarea class="textarea" name="description" maxlength="500" rows="4">${esc(settings.description)}</textarea></label><button class="btn btn-primary">Guardar cambios</button></form></section>
      <section class="card"><div class="section-title"><div><h2>Icono del servidor</h2><p>PNG cuadrado o rectangular, máximo 512×512 píxeles.</p></div>${settings.icon ? `<img class="server-icon-preview" src="${esc(settings.icon)}" alt="Icono actual">` : ''}</div>
      <form id="server-icon-form"><label class="field">Seleccionar PNG<input class="input" type="file" name="icon" accept="image/png" required></label><button class="btn btn-primary">${icon('image', 15)} Subir icono</button></form></section></div>`;
    document.getElementById('server-settings-form').addEventListener('submit', async event => {
      event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
      try { await api(`/api/servers/${state.server.id}/settings`, { method: 'PUT', body: JSON.stringify({ ...settings, ...values }) }); await refreshServer(); toast('Detalles guardados.'); renderShell(); }
      catch (error) { toast(error.message, true); }
    });
    document.getElementById('server-icon-form').addEventListener('submit', async event => {
      event.preventDefault();
      try { await api(`/api/servers/${state.server.id}/icon`, { method: 'POST', body: new FormData(event.currentTarget) }); toast('Icono actualizado.'); renderServerSettings(); }
      catch (error) { toast(error.message, true); }
    });
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

async function renderDatabases() {
  const box = document.getElementById('server-tab-content');
  try {
    const data = await api(`/api/servers/${state.server.id}/databases`);
    let mysqlState = null;
    if (state.user.role === 'admin' && !data.available) {
      mysqlState = await api('/api/admin/database/status');
    }
    box.innerHTML = `${serverModuleHeading('Base de datos', 'Crea bases MySQL aisladas y credenciales dedicadas para plugins.', 'database')}
      ${!data.available ? `<section class="card"><div class="empty"><span class="empty-icon">${icon('database', 32)}</span><strong>MySQL Server no está instalado</strong><span>${mysqlState?.installSupported ? 'Un administrador puede instalar MySQL Server 8.4 desde el instalador oficial de Windows.' : 'Instala MySQL Server 8.4 y el cliente mysql desde el gestor de paquetes de tu sistema. El cliente debe estar disponible en PATH.'}</span>${state.user.role === 'admin' && mysqlState?.installSupported ? `<button id="install-mysql" class="btn btn-primary" ${mysqlState.installRunning ? 'disabled' : ''}>${mysqlState.installRunning ? 'Instalación en curso…' : 'Instalar MySQL Server'}</button>` : '<a class="btn mt" href="https://dev.mysql.com/downloads/mysql/" target="_blank" rel="noreferrer">Descargas oficiales de MySQL ↗</a>'}</div></section>` : `<section class="card"><div class="section-title"><div><h2>Bases asignadas</h2><p>La contraseña de la cuenta root se solicita solo al crear/eliminar; no se guarda en NexoryPanel.</p></div><button id="new-database" class="btn btn-primary">＋ Nueva base</button></div>
      <div class="table-wrap"><table><thead><tr><th>Base de datos</th><th>Usuario MySQL</th><th>Host</th><th>Creada</th><th></th></tr></thead><tbody>${data.databases.length ? data.databases.map(database => `<tr><td>${esc(database.database_name)}</td><td>${esc(database.username)}</td><td>127.0.0.1:3306</td><td>${esc(database.created_at)}</td><td><button class="btn btn-danger" data-delete-db="${database.id}">Eliminar</button></td></tr>`).join('') : '<tr><td colspan="5" class="empty-row">Todavía no hay bases asignadas.</td></tr>'}</tbody></table></div></section>`}`;
    document.getElementById('install-mysql')?.addEventListener('click', async () => {
      if (!confirm('Se abrirá el instalador oficial de MySQL Server 8.4 mediante winget. ¿Continuar?')) return;
      try { await api('/api/admin/database/install', { method: 'POST', body: '{}' }); toast('Instalador MySQL abierto en una ventana aparte.'); renderDatabases(); }
      catch (error) { toast(error.message, true); }
    });
    document.getElementById('new-database')?.addEventListener('click', () => openMysqlCredentialsModal('create'));
    box.querySelectorAll('[data-delete-db]').forEach(button => button.addEventListener('click', () => {
      if (confirm('¿Eliminar definitivamente la base de datos y su usuario MySQL?')) openMysqlCredentialsModal('delete', button.dataset.deleteDb);
    }));
  } catch (error) { box.innerHTML = `<div class="notice error-notice">${esc(error.message)}</div>`; }
}

function openMysqlCredentialsModal(action, databaseId = '') {
  openModal(action === 'create' ? 'Crear base MySQL' : 'Eliminar base MySQL', `<form id="mysql-action-form">
    ${action === 'create' ? '<label class="field">Nombre de referencia<input class="input" name="name" maxlength="40" value="plugin" required></label>' : '<div class="notice">Esta acción elimina la base y el usuario MySQL y no se puede deshacer.</div>'}
    <label class="field">Usuario administrador MySQL<input class="input" name="adminUser" value="root" maxlength="32" required></label>
    <label class="field">Contraseña de administrador<input class="input" name="adminPassword" type="password" autocomplete="current-password" required></label>
    <div class="modal-foot"><button type="button" class="btn" data-close>Cancelar</button><button class="btn ${action === 'delete' ? 'btn-danger' : 'btn-primary'}">${action === 'create' ? 'Crear base' : 'Eliminar permanentemente'}</button></div></form>`);
  document.getElementById('mysql-action-form').addEventListener('submit', async event => {
    event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const result = await api(`/api/servers/${state.server.id}/databases${action === 'delete' ? `/${databaseId}` : ''}`, { method: action === 'create' ? 'POST' : 'DELETE', body: JSON.stringify(values) });
      closeModal();
      if (action === 'create') {
        openModal('Guarda estas credenciales', `<div class="notice">La contraseña se muestra una sola vez. Cópiala al plugin ahora; NexoryPanel conserva solo una huella de verificación.</div><dl class="credential-list"><dt>Host</dt><dd>${esc(result.host)}:${result.port}</dd><dt>Base</dt><dd>${esc(result.database)}</dd><dt>Usuario</dt><dd>${esc(result.username)}</dd><dt>Contraseña</dt><dd><code>${esc(result.password)}</code></dd></dl><button class="btn btn-primary" data-close>Cerrar</button>`);
      } else toast('Base y usuario MySQL eliminados.');
      renderDatabases();
    } catch (error) { toast(error.message, true); }
  });
}

async function powerServer(action) {
  try {
    const serverId = state.server.id;
    if (action === 'restart') {
      await api(`/api/servers/${serverId}/power/stop`, { method: 'POST', body: '{}' });
      toast('Esperando que el servidor se apague para reiniciarlo…');
      let stopped = false;
      for (let attempt = 0; attempt < 30; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const servers = await api('/api/servers');
        if (servers.find(server => server.id === serverId)?.status !== 'online') {
          stopped = true;
          break;
        }
      }
      if (!stopped) throw new Error('El servidor no se apagó a tiempo; intenta detenerlo manualmente.');
      await api(`/api/servers/${serverId}/power/start`, { method: 'POST', body: '{}' });
      toast('Servidor reiniciándose.');
    } else {
      const result = await api(`/api/servers/${serverId}/power/${action}`, { method: 'POST', body: '{}' });
      toast(result.status === 'starting' ? 'El proceso está iniciando.' : action === 'stop' ? 'Se envió la orden de apagado.' : 'Servidor activo.');
    }
    await renderServer();
  } catch (error) { toast(error.message, true); }
}

async function renderConsole() {
  const box = document.getElementById('server-tab-content');
  box.innerHTML = `<div class="grid stat-grid">${statCard('CPU', `${Number(state.server.cpu || 0).toFixed(1)}%`, 'Uso del proceso', '⌁')}${statCard('RAM', `${state.server.memory || 0} MiB`, `Límite ${state.server.ram_mb} MiB`, '▤')}${statCard('DISCO', `${state.server.diskUsed} MiB`, `Límite ${state.server.disk_mb} MiB`, '▱')}${statCard('IP', `:${state.server.port}`, '127.0.0.1', '◇')}</div>
    <div class="console-box"><div id="console-log" class="console-log">Cargando consola…</div><form id="console-form" class="console-form"><input class="input" name="command" autocomplete="off" placeholder="Escribe un comando de Minecraft…" aria-label="Comando de consola"><button class="btn btn-primary">Enviar ↵</button></form></div>`;
  const log = document.getElementById('console-log');
  const loadLog = async () => {
    try {
      const data = await api(`/api/servers/${state.server.id}/console`);
      const wasBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 60;
      log.innerHTML = data.lines.map(line => `<span class="console-line">${esc(line)}</span>`).join('') || '<span class="muted">El servidor todavía no ha escrito en la consola.</span>';
      if (wasBottom) log.scrollTop = log.scrollHeight;
    } catch (error) { log.textContent = error.message; }
  };
  await loadLog();
  state.consoleTimer = setInterval(loadLog, 2000);
  const consoleForm = document.getElementById('console-form');
  const commandInput = consoleForm.elements.command;
  consoleForm.addEventListener('submit', async event => {
    event.preventDefault();
    const command = commandInput.value;
    if (!command.trim()) return;
    const serverId = state.server.id;
    try {
      await api(`/api/servers/${serverId}/command`, { method: 'POST', body: JSON.stringify({ command }) });
      commandInput.value = '';
      await loadLog();
    } catch (error) { toast(error.message, true); }
  });
}

function pathLabel(path) {
  const bits = path ? path.split('/') : [];
  let current = '';
  return `<button class="crumb" data-path="">servidor</button>${bits.map(bit => {
    current = current ? `${current}/${bit}` : bit;
    return `<span>›</span><button class="crumb" data-path="${esc(current)}">${esc(bit)}</button>`;
  }).join('')}`;
}

async function renderFiles() {
  const box = document.getElementById('server-tab-content');
  if (state.fileContentPath) return renderFileEditor();
  box.innerHTML = `
    <div class="file-manager">
      <div class="file-toolbar">
        <label class="file-search">${icon('search')}<input id="file-search" class="input" type="search" placeholder="Buscar archivos…" value="${esc(state.fileSearch)}"></label>
        <div class="row wrap gap-sm file-actions">
          <button id="new-folder" class="btn">${icon('newFolder', 15)} Carpeta</button>
          <button id="new-file" class="btn">${icon('newFile', 15)} Archivo</button>
          <button id="upload-files" class="btn">${icon('upload', 15)} Subir</button>
          <input id="file-upload" type="file" multiple hidden>
          <input id="folder-upload" type="file" webkitdirectory multiple hidden>
          <button id="upload-folder" class="btn">${icon('uploadFolder', 15)} Carpeta</button>
        </div>
        <div class="breadcrumbs" id="breadcrumbs"></div>
      </div>
      <div class="file-usage"><span>Almacenamiento usado</span><strong id="disk-quota"></strong></div>
      <div id="file-list" class="file-list">Cargando…</div>
    </div>`;
  await loadFiles();
  document.getElementById('new-folder').addEventListener('click', () => createFilePrompt('folder'));
  document.getElementById('new-file').addEventListener('click', () => createFilePrompt('file'));
  document.getElementById('upload-files').addEventListener('click', () => document.getElementById('file-upload').click());
  document.getElementById('upload-folder').addEventListener('click', () => document.getElementById('folder-upload').click());
  document.getElementById('file-upload').addEventListener('change', event => uploadFiles(event.currentTarget.files));
  document.getElementById('folder-upload').addEventListener('change', event => uploadFiles(event.currentTarget.files, true));
  document.getElementById('file-search').addEventListener('input', event => {
    state.fileSearch = event.currentTarget.value.toLocaleLowerCase();
    document.querySelectorAll('[data-file-row]').forEach(row => {
      row.hidden = !row.dataset.fileRow.toLocaleLowerCase().includes(state.fileSearch);
    });
  });
}

function changePath(event) {
  state.filePath = event.currentTarget.dataset.path || '';
  renderFiles();
}

async function loadFiles() {
  const serverId = state.server.id;
  const data = await api(`/api/servers/${serverId}/files?path=${encodeURIComponent(state.filePath)}`);
  const breadcrumbs = document.getElementById('breadcrumbs');
  breadcrumbs.innerHTML = pathLabel(state.filePath);
  breadcrumbs.querySelectorAll('[data-path]').forEach(button => button.addEventListener('click', changePath));
  document.getElementById('disk-quota').textContent = `${data.usedMb} / ${data.limitMb} MiB`;
  const list = document.getElementById('file-list');
  if (!data.entries.length) {
    list.innerHTML = '<div class="empty"><strong>Esta carpeta está vacía</strong><span>Sube o crea archivos para empezar.</span></div>';
    return;
  }
  const filtered = data.entries.filter(item => item.name.toLocaleLowerCase().includes(state.fileSearch));
  list.innerHTML = `<div class="file-list-head"><span></span><span>Nombre</span><span>Tamaño</span><span>Acciones</span></div>${filtered.map(item => `<div class="file-row" data-file-row="${esc(item.name)}">
      <span class="file-icon ${item.directory ? 'folder' : ''}">${icon(item.directory ? 'folder' : 'file', 19)}</span>
      <button class="crumb file-name" data-open="${esc(item.name)}" data-directory="${item.directory}">${esc(item.name)}</button>
      <span class="file-size">${item.directory ? 'Carpeta' : formatBytes(item.size)}</span>
      <div class="file-row-actions">
        ${!item.directory && item.name.toLowerCase().endsWith('.zip') ? `<button class="btn btn-icon-label" data-unzip="${esc(item.name)}">${icon('extract', 14)}<span>Extraer</span></button>` : `<button class="btn btn-icon-label" data-zip="${esc(item.name)}">${icon('archive', 14)}<span>${item.directory ? 'Comprimir' : 'Zip'}</span></button>`}
        <button class="btn btn-icon-label" data-rename="${esc(item.name)}">${icon('rename', 14)}<span>Renombrar</span></button>
        <button class="btn btn-icon-label" data-edit="${esc(item.name)}" ${item.directory ? 'disabled' : ''}>${icon('edit', 14)}<span>Editar</span></button>
        <button class="btn btn-danger file-delete" data-delete="${esc(item.name)}" title="Eliminar" aria-label="Eliminar ${esc(item.name)}">${icon('delete', 14)}</button>
      </div>
    </div>`).join('') || '<div class="empty"><strong>No se encontraron archivos</strong><span>Prueba con otro término.</span></div>'}`;
  list.querySelectorAll('[data-open]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.directory === 'true') {
      state.filePath = state.filePath ? `${state.filePath}/${button.dataset.open}` : button.dataset.open;
      renderFiles();
    } else openEditor(button.dataset.open);
  }));
  list.querySelectorAll('[data-edit]').forEach(button => button.addEventListener('click', () => {
    if (!button.disabled) openEditor(button.dataset.edit);
  }));
  list.querySelectorAll('[data-rename]').forEach(button => button.addEventListener('click', () => renameFile(button.dataset.rename)));
  list.querySelectorAll('[data-delete]').forEach(button => button.addEventListener('click', async () => {
    const name = button.dataset.delete;
    if (!confirm(`¿Eliminar ${name}?`)) return;
    try {
      const path = state.filePath ? `${state.filePath}/${name}` : name;
      await api(`/api/servers/${serverId}/files?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      toast('Elemento eliminado.');
      loadFiles();
    } catch (error) { toast(error.message, true); }
  }));
  list.querySelectorAll('[data-zip],[data-unzip]').forEach(button => button.addEventListener('click', async () => {
    const name = button.dataset.zip || button.dataset.unzip;
    const path = state.filePath ? `${state.filePath}/${name}` : name;
    try {
      await api(`/api/servers/${serverId}/files/archive`, {
        method: 'POST', body: JSON.stringify({ action: button.dataset.zip ? 'zip' : 'unzip', path }),
      });
      toast(button.dataset.zip ? 'Archivo comprimido.' : 'Archivo descomprimido.');
      loadFiles();
    } catch (error) { toast(error.message, true); }
  }));
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}

function createFilePrompt(type) {
  openModal(type === 'folder' ? 'Nueva carpeta' : 'Nuevo archivo', `
    <form id="create-file-form"><label class="field">Nombre<input class="input" name="name" required maxlength="100" placeholder="${type === 'folder' ? 'plugins' : 'server.properties'}"></label>
    ${type === 'file' ? '<label class="field">Contenido<textarea class="textarea" name="content" rows="8"></textarea></label>' : ''}
    <div class="modal-foot"><button type="button" class="btn" data-close>Cancelar</button><button class="btn btn-primary">Crear</button></div></form>`);
  document.getElementById('create-file-form').addEventListener('submit', async event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await api(`/api/servers/${state.server.id}/files/${type}`, {
        method: 'POST', body: JSON.stringify({ ...values, path: state.filePath }),
      });
      closeModal();
      toast(type === 'folder' ? 'Carpeta creada.' : 'Archivo creado.');
      renderFiles();
    } catch (error) { toast(error.message, true); }
  });
}

async function openEditor(name) {
  const path = state.filePath ? `${state.filePath}/${name}` : name;
  try {
    const data = await api(`/api/servers/${state.server.id}/files/content?path=${encodeURIComponent(path)}`);
    state.fileContentPath = path;
    state.editorSavedContent = data.content;
    state.editorLanguage = fileLanguage(path);
    await renderFileEditor();
  } catch (error) { toast(error.message, true); }
}

function fileLanguage(path) {
  const extension = path.split('.').pop().toLowerCase();
  return ({ yml: 'YAML', yaml: 'YAML', properties: 'Properties', json: 'JSON', txt: 'Text', log: 'Log', conf: 'Config' })[extension] || extension.toUpperCase() || 'Text';
}

function highlightLine(line, language) {
  const parts = line.match(/^(\s*)(.*)$/);
  const indent = esc(parts[1]);
  let rest = parts[2];
  if (!rest) return indent || '&nbsp;';
  if (rest.startsWith('#')) return `${indent}<span class="syntax-comment">${esc(rest)}</span>`;
  const separator = language === 'Properties' ? /^([^=:]+?)(\s*[=:]\s*)(.*)$/.exec(rest) : /^(-?\s*[^:#]+?)(\s*:\s*)(.*)$/.exec(rest);
  if (separator) {
    const [, key, divider, value] = separator;
    return `${indent}<span class="syntax-key">${esc(key)}</span><span class="syntax-punctuation">${esc(divider)}</span>${highlightValue(value)}`;
  }
  return `${indent}${highlightValue(rest)}`;
}

function highlightValue(value) {
  const escaped = esc(value);
  return escaped.replace(/(&quot;[^&]*?&quot;|'[^']*'|\b(?:true|false|null|none|yes|no)\b|-?\b\d+(?:\.\d+)?\b)/gi, token => {
    const cls = /^(?:true|false|null|none|yes|no)$/i.test(token) ? 'syntax-boolean'
      : /^-?\d/.test(token) ? 'syntax-number' : 'syntax-string';
    return `<span class="${cls}">${token}</span>`;
  });
}

function updateEditorHighlight() {
  const textarea = document.getElementById('editor-content');
  const highlight = document.getElementById('editor-highlight');
  const gutter = document.getElementById('editor-gutter');
  if (!textarea || !highlight || !gutter) return;
  const lines = textarea.value.split('\n');
  highlight.innerHTML = `${lines.map(line => highlightLine(line, state.editorLanguage)).join('\n')}\n`;
  gutter.innerHTML = lines.map((_, index) => `<span>${index + 1}</span>`).join('');
  highlight.scrollTop = textarea.scrollTop;
  highlight.scrollLeft = textarea.scrollLeft;
  gutter.scrollTop = textarea.scrollTop;
  document.getElementById('editor-dirty').hidden = textarea.value === state.editorSavedContent;
  document.getElementById('editor-line-count').textContent = `${lines.length} líneas`;
}

function editorIsDirty() {
  const editor = document.getElementById('editor-content');
  return Boolean(editor && editor.value !== state.editorSavedContent);
}

async function renderFileEditor() {
  const box = document.getElementById('server-tab-content');
  if (!box || !state.fileContentPath) return;
  const path = state.fileContentPath;
  const data = await api(`/api/servers/${state.server.id}/files/content?path=${encodeURIComponent(path)}`);
  state.editorSavedContent = data.content;
  state.editorLanguage = fileLanguage(path);
  const lines = data.content.split('\n');
  box.innerHTML = `
    <div class="file-editor">
      <div class="editor-toolbar">
        <div class="breadcrumbs editor-breadcrumbs"><button class="crumb" id="editor-back">${icon('files', 14)} Archivos</button><span>›</span>${pathLabel(path)}</div>
        <div class="row wrap gap-sm"><span class="editor-language">${esc(state.editorLanguage)}</span><span id="editor-dirty" class="editor-unsaved" hidden>● Cambios sin guardar</span><button id="save-editor" class="btn btn-primary">${icon('save', 15)} Guardar</button></div>
      </div>
      <div class="editor-tab"><span class="editor-tab-dot"></span>${icon('file', 14)}<span>${esc(path.split('/').pop())}</span><span class="muted tiny">UTF-8</span></div>
      <div class="code-editor">
        <div id="editor-gutter" class="editor-gutter" aria-hidden="true">${lines.map((_, index) => `<span>${index + 1}</span>`).join('')}</div>
        <div class="editor-code-viewport"><pre id="editor-highlight" class="editor-highlight" aria-hidden="true"></pre><textarea id="editor-content" class="editor-input" spellcheck="false" wrap="off" aria-label="Contenido del archivo">${esc(data.content)}</textarea></div>
      </div>
      <div class="editor-status"><span>${esc(path)}</span><span>${esc(state.editorLanguage)} · UTF-8</span><span id="editor-line-count">${lines.length} líneas</span></div>
    </div>`;
  const textarea = document.getElementById('editor-content');
  const saveButton = document.getElementById('save-editor');
  document.getElementById('editor-back').addEventListener('click', () => {
    if (editorIsDirty() && !confirm('Tienes cambios sin guardar. ¿Volver a los archivos?')) return;
    state.fileContentPath = '';
    renderFiles();
  });
  textarea.addEventListener('input', updateEditorHighlight);
  textarea.addEventListener('scroll', updateEditorHighlight);
  textarea.addEventListener('keydown', event => {
    if (event.key === 'Tab') {
      event.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.setRangeText('  ', start, end, 'end');
      updateEditorHighlight();
    }
  });
  saveButton.addEventListener('click', saveEditorContent);
  updateEditorHighlight();
}

async function saveEditorContent() {
  const textarea = document.getElementById('editor-content');
  const saveButton = document.getElementById('save-editor');
  if (!textarea || !state.fileContentPath) return;
  const path = state.fileContentPath;
  const content = textarea.value;
  saveButton.disabled = true;
  try {
    await api(`/api/servers/${state.server.id}/files/content`, {
      method: 'PUT', body: JSON.stringify({ path, content }),
    });
    state.editorSavedContent = content;
    updateEditorHighlight();
    toast('Archivo guardado correctamente.');
  } catch (error) { toast(error.message, true); }
  finally {
    if (document.getElementById('save-editor')) document.getElementById('save-editor').disabled = false;
  }
}

async function renameFile(name) {
  const path = state.filePath ? `${state.filePath}/${name}` : name;
  openModal('Renombrar elemento', `<form id="rename-file-form"><label class="field">Nuevo nombre<input class="input" name="newName" required maxlength="100" value="${esc(name)}"></label><div class="modal-foot"><button type="button" class="btn" data-close>Cancelar</button><button class="btn btn-primary">Renombrar</button></div></form>`);
  const input = document.querySelector('#rename-file-form input');
  input.focus();
  input.select();
  document.getElementById('rename-file-form').addEventListener('submit', async event => {
    event.preventDefault();
    try {
      const body = Object.fromEntries(new FormData(event.currentTarget));
      await api(`/api/servers/${state.server.id}/files/rename`, { method: 'POST', body: JSON.stringify({ path, ...body }) });
      closeModal();
      toast('Elemento renombrado.');
      await renderFiles();
    } catch (error) { toast(error.message, true); }
  });
}

async function uploadFiles(fileList, preserveFolder = false) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  const form = new FormData();
  form.append('path', state.filePath);
  files.forEach(file => {
    const relative = preserveFolder ? (file.webkitRelativePath || file.name) : file.name;
    form.append('files', file, relative);
  });
  try {
    await api(`/api/servers/${state.server.id}/files/upload`, { method: 'POST', body: form });
    toast(`${files.length} archivo(s) subido(s).`);
    renderFiles();
  } catch (error) { toast(error.message, true); }
}

async function renderVersions() {
  const box = document.getElementById('server-tab-content');
  let selectedSoftware = state.server.software;
  box.innerHTML = `
    <div class="software-switcher" role="group" aria-label="Tipo de software">${softwareChoiceButtons(selectedSoftware, 'data-software')}</div>
    <div class="card version-card">
      <div class="section-title"><div><h2 id="selected-software-name">${softwareInfo(selectedSoftware).name}</h2><p>Elige la versión y build disponibles para instalar en este servidor.</p></div><span class="badge">Fuente oficial</span></div>
      <div class="form-grid">
        <label class="field">Versión<select id="install-version" class="select"><option value="">Cargando versiones oficiales…</option></select></label>
        <label class="field" id="build-field">Build<select id="install-build" class="select"><option value="">Selecciona una versión</option></select></label>
      </div>
      <div id="version-note" class="version-note"></div>
      <div class="row between wrap mt"><span id="software-install-note" class="muted tiny"></span><button id="install-server" class="btn btn-primary">${icon('download', 15)} Instalar software</button></div>
    </div>`;
  const versionSelect = document.getElementById('install-version');
  const buildSelect = document.getElementById('install-build');
  const buildField = document.getElementById('build-field');
  const versionNote = document.getElementById('version-note');
  box.querySelectorAll('[data-software]').forEach(button => button.addEventListener('click', async () => {
    selectedSoftware = button.dataset.software;
    box.querySelectorAll('[data-software]').forEach(option => {
      option.classList.toggle('active', option === button);
      option.setAttribute('aria-pressed', String(option === button));
    });
    document.getElementById('selected-software-name').textContent = softwareInfo(selectedSoftware).name;
    await loadVersions();
  }));
  async function loadVersions() {
    versionSelect.innerHTML = '<option value="">Cargando…</option>';
    buildSelect.innerHTML = '<option value="">Selecciona una versión</option>';
    buildField.style.display = selectedSoftware === 'vanilla' ? 'none' : '';
    versionNote.textContent = selectedSoftware === 'vanilla' ? 'Vanilla no utiliza números de build.' : 'Las builds disponibles dependen de la versión seleccionada.';
    document.getElementById('software-install-note').textContent = ['forge', 'neoforge'].includes(selectedSoftware)
      ? 'Ejecuta el instalador oficial y prepara sus archivos de inicio; conserva los demás archivos del servidor.'
      : selectedSoftware === 'fabric'
        ? 'Instala el launcher Fabric y el JAR vanilla requerido; conserva los demás archivos.'
        : 'Reemplaza server.jar; los demás archivos del servidor se conservan.';
    try {
      const data = await api(`/api/software/${selectedSoftware}/versions`);
      const versions = data.versions || [];
      versionSelect.innerHTML = versions.map(version => {
        const value = versionId(version);
        return value ? `<option value="${esc(value)}" ${value === state.server.version ? 'selected' : ''}>${esc(value)}</option>` : '';
      }).join('');
      if (selectedSoftware === state.server.software && state.server.version && !versions.some(v => versionId(v) === state.server.version)) {
        versionSelect.insertAdjacentHTML('afterbegin', `<option selected value="${esc(state.server.version)}">${esc(state.server.version)} (actual)</option>`);
      }
      if (selectedSoftware === 'vanilla') buildSelect.innerHTML = '<option value="">No aplica</option>';
      else await loadBuilds();
    } catch (error) {
      versionSelect.innerHTML = `<option value="">${esc(error.message)}</option>`;
    }
  }
  async function loadBuilds() {
    if (selectedSoftware === 'vanilla') return;
    const version = versionSelect.value;
    if (!version) return;
    buildSelect.innerHTML = '<option value="">Cargando builds…</option>';
    try {
      const data = await api(`/api/software/${selectedSoftware}/versions/${encodeURIComponent(version)}/builds`);
      const builds = data.builds || [];
      buildSelect.innerHTML = builds.map(build => {
        const id = typeof build === 'string' || typeof build === 'number' ? String(build) : String(build.id || build.build || '');
        const label = typeof build === 'object' && build.label ? String(build.label) : id;
        return id ? `<option value="${esc(id)}" ${id === String(state.server.build) ? 'selected' : ''}>${esc(label)}</option>` : '';
      }).join('') || '<option value="">No hay builds disponibles</option>';
    } catch (error) { buildSelect.innerHTML = `<option value="">${esc(error.message)}</option>`; }
  }
  versionSelect.addEventListener('change', loadBuilds);
  await loadVersions();
  const installButton = document.getElementById('install-server');
  if (!box.isConnected || state.serverTab !== 'Versions' || !installButton) return;
  installButton.addEventListener('click', async () => {
    const version = versionSelect.value;
    if (!version) return toast('Selecciona una versión.', true);
    if (selectedSoftware !== 'vanilla' && !buildSelect.value) return toast('Selecciona una build antes de instalar.', true);
    if (!confirm(`¿Instalar ${softwareInfo(selectedSoftware).name} ${version}${buildSelect.value ? ` (build ${buildSelect.options[buildSelect.selectedIndex].text})` : ''}? Detén el servidor antes de continuar.`)) return;
    const button = document.getElementById('install-server');
    button.disabled = true;
    button.innerHTML = `${icon('download', 15)} Descargando…`;
    try {
      const result = await api(`/api/servers/${state.server.id}/install`, {
        method: 'POST', body: JSON.stringify({ software: selectedSoftware, version, build: buildSelect.value }),
      });
      toast(`Instalación completa: ${result.file}. Revisa el EULA antes de iniciar.`);
      await refreshServer();
      await renderServer();
    } catch (error) {
      toast(error.message, true);
      button.disabled = false;
      button.innerHTML = `${icon('download', 15)} Instalar software`;
    }
  });
}

async function renderPlugins() {
  const box = document.getElementById('server-tab-content');
  box.innerHTML = `<div class="card mb"><div class="section-title"><div><h2>Marketplace de plugins</h2><p>Busca proyectos de Modrinth compatibles con servidores Java.</p></div><div class="row wrap"><span class="badge">Modrinth</span><button id="create-plugin-template" class="btn">＋ Crear plugin Java</button></div></div><form id="plugin-search" class="row"><input class="input" name="query" placeholder="Buscar EssentialsX, LuckPerms…" required><button class="btn btn-primary">Buscar</button></form><div class="notice">Verifica el autor y los permisos del plugin antes de instalarlo. El archivo se guarda en la carpeta plugins/ del servidor.</div></div><div id="plugin-results" class="grid plugin-grid"></div>`;
  document.getElementById('create-plugin-template').addEventListener('click', openPluginTemplate);
  if (['vanilla', 'forge', 'neoforge', 'fabric'].includes(state.server.software)) {
    document.getElementById('plugin-search').remove();
    document.getElementById('plugin-results').innerHTML = '<div class="card empty"><strong>Marketplace de plugins no disponible</strong><span>Este software usa mods en lugar de plugins Bukkit. El generador Java sigue disponible.</span></div>';
    return;
  }
  document.getElementById('plugin-search').addEventListener('submit', async event => {
    event.preventDefault();
    const query = new FormData(event.currentTarget).get('query');
    const results = document.getElementById('plugin-results');
    results.innerHTML = '<div class="card empty">Buscando en Modrinth…</div>';
    try {
      const data = await api(`/api/plugins/search?q=${encodeURIComponent(query)}`);
      if (!data.hits.length) {
        results.innerHTML = '<div class="card empty"><strong>No hay resultados</strong><span>Prueba con otro término.</span></div>';
        return;
      }
      results.innerHTML = data.hits.map(plugin => `<article class="card plugin-card">
        <div class="row"><div class="software-mark">${plugin.icon_url ? `<img src="${esc(plugin.icon_url)}" alt="" width="34" height="34" style="border-radius:8px">` : '✣'}</div><div><h3>${esc(plugin.title)}</h3><span class="tiny muted">por ${esc(plugin.author)}</span></div></div>
        <p>${esc(plugin.description || 'Sin descripción disponible.')}</p><div class="plugin-meta">↓ ${Number(plugin.downloads || 0).toLocaleString('es-ES')} descargas · ${esc((plugin.categories || []).slice(0, 3).join(', '))}</div>
        <button class="btn btn-primary" data-plugin="${esc(plugin.project_id)}" data-plugin-title="${esc(plugin.title)}">Elegir versión</button>
      </article>`).join('');
      results.querySelectorAll('[data-plugin]').forEach(button => button.addEventListener('click', () => choosePluginVersion(button.dataset.plugin, button.dataset.pluginTitle)));
    } catch (error) { results.innerHTML = `<div class="card empty"><strong>Error al buscar</strong><span>${esc(error.message)}</span></div>`; }
  });
}

function openPluginTemplate() {
  openModal('Crear plantilla de plugin Java', `<p class="muted tiny">Descarga un proyecto Maven básico compatible con la API Bukkit. Edita el código y ejecuta <span class="code-token">mvn package</span> para compilarlo.</p>
    <form id="plugin-template-form">
      <label class="field">Nombre del plugin<input class="input" name="name" required minlength="2" maxlength="40" value="Mi Plugin"></label>
      <div class="form-grid">
        <label class="field">Paquete Java<input class="input" name="package" required value="com.ejemplo.miplugin"></label>
        <label class="field">Clase principal<input class="input" name="mainClass" required value="Main"></label>
        <label class="field">Versión de Minecraft<input class="input" name="minecraftVersion" required value="${esc(state.server.version)}"></label>
      </div>
      <div class="notice">La plantilla incluye plugin.yml, una clase principal Java y pom.xml. Para compilar necesitarás Java y Maven instalados.</div>
      <div class="modal-foot"><button type="button" class="btn" data-close>Cancelar</button><button class="btn btn-primary">Descargar proyecto .zip</button></div>
    </form>`);
  document.getElementById('plugin-template-form').addEventListener('submit', async event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const headers = { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf };
    try {
      const response = await fetch('/api/plugin-projects/template', {
        method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify(values),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Error HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${values.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-plugin-template.zip`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      closeModal();
      toast('Plantilla Java descargada.');
    } catch (error) { toast(error.message, true); }
  });
}

async function choosePluginVersion(projectId, title) {
  try {
    const data = await api(`/api/plugins/${encodeURIComponent(projectId)}/versions?gameVersion=${encodeURIComponent(state.server.version)}`);
    if (!data.versions.length) return toast('No se encontraron versiones compatibles con el Minecraft de este servidor.', true);
    const options = data.versions.map((version, index) => {
      const file = (version.files || []).find(item => item.primary) || (version.files || [])[0];
      return file ? `<option value="${index}">${esc(version.name)} · ${esc(version.version_number)} (${esc(file.filename)})</option>` : '';
    }).join('');
    openModal(`Instalar ${title}`, `<label class="field">Versión compatible<select class="select" id="plugin-version">${options}</select></label><div class="modal-foot"><button class="btn" data-close>Cancelar</button><button class="btn btn-primary" id="confirm-plugin-install">Instalar plugin</button></div>`);
    document.getElementById('confirm-plugin-install').addEventListener('click', async () => {
      const index = Number(document.getElementById('plugin-version').value);
      const version = data.versions[index];
      const file = (version.files || []).find(item => item.primary) || (version.files || [])[0];
      if (!file) return toast('No hay archivo para esta versión.', true);
      try {
        await api(`/api/servers/${state.server.id}/plugins/install`, {
          method: 'POST', body: JSON.stringify({ url: file.url, fileName: file.filename }),
        });
        closeModal();
        toast('Plugin instalado en plugins/. Reinicia el servidor para activarlo.');
      } catch (error) { toast(error.message, true); }
    });
  } catch (error) { toast(error.message, true); }
}

async function renderAdmin() {
  const content = document.getElementById('content');
  content.innerHTML = '<div class="empty">Cargando administración…</div>';
  try {
    const data = await api('/api/admin/overview');
    state.settings = data.settings;
    setTheme(data.settings.theme, data.settings.accentColor, data.settings.buttonStyle, data.settings.backgroundStyle, data.settings.backgroundStart, data.settings.backgroundEnd);
    const mysqlStatus = await api('/api/admin/database/status');
    const maxRam = data.settings.maxRamMb;
    const maxDisk = data.settings.maxDiskMb;
    content.innerHTML = `
      ${pageHeading('Administración', 'Configura el nodo, las cuotas y las cuentas del panel.')}
      <div class="grid stat-grid">${statCard('RAM DEL NODO', `${(data.allocation.ramMb / 1024).toFixed(1)} GiB`, `de ${(maxRam / 1024).toFixed(1)} GiB asignables`, '▤')}${statCard('DISCO ASIGNADO', `${(data.allocation.diskMb / 1024).toFixed(1)} GiB`, `de ${(maxDisk / 1024).toFixed(1)} GiB configurados`, '▱')}${statCard('USUARIOS', data.users.length, 'Cuentas locales', '♙')}${statCard('SERVIDORES', data.servers.length, data.settings.nodeName, '◇')}</div>
      <div class="grid admin-grid">
        <section class="card"><div class="section-title"><div><h2>Configuración del nodo</h2><p>Las cuotas limitan los recursos nuevos asignables.</p></div><span class="badge">${esc(data.settings.platformLabel)}</span></div>
          <form id="settings-form">
            <label class="field">Nombre del nodo<input class="input" name="nodeName" maxlength="60" value="${esc(data.settings.nodeName)}"></label>
            <div class="form-grid"><label class="field">Límite RAM (MiB)<input class="input" type="number" min="${data.allocation.ramMb || 512}" name="maxRamMb" value="${maxRam}"></label><label class="field">Límite almacenamiento (MiB)<input class="input" type="number" min="${Math.max(1024, data.allocation.diskMb)}" name="maxDiskMb" value="${maxDisk}"></label></div>
            <label class="field">Color de estilo<select class="select" name="theme">${data.themes.map(theme => `<option ${theme === data.settings.theme ? 'selected' : ''}>${esc(theme)}</option>`).join('')}</select></label>
              <div class="form-grid">
                <label class="field">Color personalizado de botones<div class="color-control"><input type="color" name="accentColor" value="${esc(data.settings.accentColor || '#8657f5')}"><input class="input" id="accent-hex" value="${esc(data.settings.accentColor || '')}" placeholder="Usar color del tema" maxlength="7" aria-label="Código hexadecimal del color"></div></label>
                <label class="field">Estilo de botones<select class="select" name="buttonStyle">${['Gradient','Solid','Outline','Glassed'].map(style => `<option ${style === data.settings.buttonStyle ? 'selected' : ''}>${style}</option>`).join('')}</select></label>
              </div>
              <label class="field">Estilo de superficies<select class="select" name="backgroundStyle">${['Gradient','Glassed','Solid'].map(style => `<option ${style === data.settings.backgroundStyle ? 'selected' : ''}>${style}</option>`).join('')}</select></label>
              <div class="form-grid">
                <label class="field">Gradiente de fondo · inicio<input class="input" type="color" name="backgroundStart" value="${esc(data.settings.backgroundStart)}"></label>
                <label class="field">Gradiente de fondo · final<input class="input" type="color" name="backgroundEnd" value="${esc(data.settings.backgroundEnd)}"></label>
              </div>
              <div class="section-divider"></div>
              <label class="field">Anuncio para el panel<input class="input" name="announcement" maxlength="300" value="${esc(data.settings.announcement)}" placeholder="Mantenimiento este viernes..."></label>
              <div class="form-grid"><label class="field">Enlace de Discord<input class="input" type="url" name="discordUrl" value="${esc(data.settings.discordUrl)}" placeholder="https://discord.gg/..."></label>
              ${data.settings.firewallManaged ? `<label class="field">Perfil de Windows Firewall<select class="select" name="firewallProfile">${[['Any','Todos los perfiles'],['Private','Privado'],['Domain','Dominio'],['Public','Público']].map(([value,label]) => `<option value="${value}" ${value === data.settings.firewallProfile ? 'selected' : ''}>${label}</option>`).join('')}</select></label>` : '<div class="notice">La administración de firewall del sistema se configura fuera de NexoryPanel.</div>'}</div>
              <label class="field">URLs personalizadas (una por línea: etiqueta|https://...)<textarea class="textarea" name="customLinks" rows="3" maxlength="4000">${esc(data.settings.customLinks.map(link => `${link.label}|${link.url}`).join('\n'))}</textarea></label>
              ${toggleRow('enableRegister', 'Enable Register', 'Permite crear cuentas nuevas.', data.settings.enableRegister)}
              ${toggleRow('apiKeyEnabled', 'API key del dashboard', 'Habilita el endpoint de lectura /api/dashboard.', data.settings.apiKeyEnabled)}
              <div class="button-style-preview"><button type="button" class="btn btn-primary">Vista previa del botón</button><span class="muted tiny">El color y estilo se aplican al panel completo.</span></div>
              <button class="btn btn-primary mt">Guardar configuración</button>
          </form>
        </section>
        <section class="card"><div class="section-title"><div><h2>Identidad visual</h2><p>El icono PNG se muestra en el navegador y la navegación.</p></div>${data.settings.hasCustomIcon ? `<img class="server-icon-preview" src="/api/branding/icon?t=${Date.now()}" alt="Icono del panel">` : ''}</div>
          <form id="branding-icon-form" class="form-grid"><label class="field">Icono personalizado (PNG, hasta 512×512)<input class="input" type="file" name="icon" accept="image/png" required></label><div class="field form-end"><span></span><div class="row wrap"><button class="btn btn-primary">${icon('image', 15)} Subir icono</button>${data.settings.hasCustomIcon ? '<button type="button" class="btn btn-danger" id="reset-branding-icon">Restaurar icono original</button>' : ''}</div></div></form>
        </section>
        <section class="card"><div class="section-title"><div><h2>Base de datos MySQL local</h2><p>${mysqlStatus.installSupported ? 'MySQL Server 8.4 se instala de forma interactiva desde winget.' : 'Instala MySQL Server 8.4 con el gestor de paquetes de tu sistema y deja mysql disponible en PATH.'}</p></div><span class="badge">${mysqlStatus.installed ? 'Instalado' : mysqlStatus.installRunning ? 'Instalando' : 'No instalado'}</span></div>
          <p class="muted tiny">Las bases MySQL creadas desde un servidor aparecen en su sección Base de datos. ${mysqlStatus.installSupported ? 'El instalador puede solicitar permisos de Windows.' : ''}</p>${mysqlStatus.installSupported ? `<button id="install-mysql-admin" class="btn" ${mysqlStatus.installRunning ? 'disabled' : ''}>${icon('database', 15)} Abrir instalador de MySQL</button>` : '<a class="btn mt" href="https://dev.mysql.com/downloads/mysql/" target="_blank" rel="noreferrer">Descargas oficiales de MySQL ↗</a>'}
        </section>
        <section class="card"><div class="section-title"><div><h2>API para dashboard</h2><p>Las claves se muestran una sola vez; almacena un hash en la base de datos.</p></div><button id="new-api-key" class="btn btn-primary">＋ Crear key</button></div>
          <div id="api-key-output"></div>
          ${data.apiKeys.length ? `<div class="table-wrap mt"><table><thead><tr><th>Etiqueta</th><th>Creada</th><th></th></tr></thead><tbody>${data.apiKeys.map(key => `<tr><td>${esc(key.label)}</td><td>${esc(key.created_at)}</td><td><button class="btn btn-danger" data-delete-key="${esc(key.id)}">Eliminar</button></td></tr>`).join('')}</tbody></table></div>` : '<div class="empty"><span>No hay API keys.</span></div>'}
        </section>
        <section class="card"><div class="section-title"><div><h2>Usuarios</h2><p>Usuarios con acceso al panel local.</p></div><span class="badge">${data.users.length}</span></div>
          <div class="table-wrap"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Registro</th></tr></thead><tbody>${data.users.map(user => `<tr><td>${esc(user.username)}</td><td><span class="badge ${user.role === 'admin' ? 'badge-warning' : ''}">${esc(user.role)}</span></td><td>${esc(user.created_at)}</td></tr>`).join('')}</tbody></table></div>
        </section>
        <section class="card"><div class="section-title"><div><h2>Asignaciones de servidores</h2><p>Recursos reservados por instancia, no por uso actual.</p></div><button id="create-server-admin" class="btn">＋ Crear servidor</button></div>
          ${data.servers.length ? `<div class="table-wrap"><table><thead><tr><th>Servidor</th><th>Software</th><th>Usuario</th><th>RAM / disco</th></tr></thead><tbody>${data.servers.map(server => `<tr><td>${esc(server.name)}</td><td>${esc(server.software)} ${esc(server.version)}</td><td>${esc(server.owner_name)}</td><td>${server.ram_mb} / ${server.disk_mb} MiB</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty"><span>Aún no hay servidores</span></div>'}
        </section>
      </div>
      <div class="notice">NexoryPanel se enlaza por defecto a 127.0.0.1. No lo publiques directamente en Internet: aún no incluye TLS, recuperación de contraseñas ni autenticación de dos factores.</div>`;
    document.getElementById('settings-form').addEventListener('submit', saveSettings);
    const colorPicker = document.querySelector('input[name="accentColor"]');
    const hexColor = document.getElementById('accent-hex');
    colorPicker.addEventListener('input', () => {
      hexColor.value = colorPicker.value;
      document.body.style.setProperty('--accent', colorPicker.value);
    });
    document.querySelectorAll('input[name="backgroundStart"], input[name="backgroundEnd"]').forEach(input => input.addEventListener('input', () => {
      document.body.style.setProperty(input.name === 'backgroundStart' ? '--background-start' : '--background-end', input.value);
    }));
    hexColor.addEventListener('input', () => {
      const color = hexColor.value.trim();
      if (!color) {
        colorPicker.value = '#8657f5';
        document.body.style.removeProperty('--accent');
      } else if (/^#[\da-f]{6}$/i.test(color)) {
        colorPicker.value = color;
        document.body.style.setProperty('--accent', color);
      }
    });
    document.querySelector('select[name="theme"]').addEventListener('change', event => {
      document.body.dataset.theme = event.currentTarget.value;
    });
    document.querySelector('select[name="buttonStyle"]').addEventListener('change', event => {
      document.body.dataset.buttonStyle = event.currentTarget.value;
    });
    document.querySelector('select[name="backgroundStyle"]').addEventListener('change', event => {
      document.body.dataset.appearance = event.currentTarget.value;
    });
    document.getElementById('new-api-key').addEventListener('click', createApiKey);
    document.getElementById('branding-icon-form').addEventListener('submit', uploadBrandingIcon);
    document.getElementById('reset-branding-icon')?.addEventListener('click', resetBrandingIcon);
    document.getElementById('install-mysql-admin')?.addEventListener('click', installMysql);
    content.querySelectorAll('[data-delete-key]').forEach(button => button.addEventListener('click', () => removeApiKey(button.dataset.deleteKey)));
    document.getElementById('create-server-admin').addEventListener('click', openCreateServer);
  } catch (error) {
    content.innerHTML = `<div class="card empty"><strong>No se pudo cargar la administración</strong><span>${esc(error.message)}</span></div>`;
  }
}

function toggleRow(name, title, description, checked) {
  return `<div class="toggle-row"><div class="toggle-copy"><strong>${title}</strong><span>${description}</span></div><button type="button" class="switch ${checked ? 'on' : ''}" role="switch" aria-checked="${checked}" data-toggle="${name}"></button><input type="hidden" name="${name}" value="${checked}"></div>`;
}

async function saveSettings(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = Object.fromEntries(new FormData(form));
  values.enableRegister = values.enableRegister === 'true';
  values.apiKeyEnabled = values.apiKeyEnabled === 'true';
  values.maxRamMb = Number(values.maxRamMb);
  values.maxDiskMb = Number(values.maxDiskMb);
  values.accentColor = document.getElementById('accent-hex').value.trim();
  values.customLinks = values.customLinks.split('\n').map(line => {
    const splitAt = line.indexOf('|');
    return splitAt > 0 ? { label: line.slice(0, splitAt).trim(), url: line.slice(splitAt + 1).trim() } : null;
  }).filter(Boolean);
  try {
    await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify(values) });
    state.settings = { ...state.settings, ...values };
    setTheme(values.theme, values.accentColor, values.buttonStyle, values.backgroundStyle, values.backgroundStart, values.backgroundEnd);
    toast('Configuración guardada.');
    renderShell();
  } catch (error) { toast(error.message, true); }
}

async function uploadBrandingIcon(event) {
  event.preventDefault();
  try {
    await api('/api/admin/branding/icon', { method: 'POST', body: new FormData(event.currentTarget) });
    toast('Icono del panel actualizado.');
    renderShell();
  } catch (error) { toast(error.message, true); }
}

async function resetBrandingIcon() {
  if (!confirm('¿Restaurar el icono original de NexoryPanel?')) return;
  try { await api('/api/admin/branding/icon', { method: 'DELETE' }); toast('Icono original restaurado.'); renderShell(); }
  catch (error) { toast(error.message, true); }
}

async function installMysql() {
  if (!confirm('Se abrirá el instalador oficial de MySQL Server 8.4 en otra ventana. ¿Continuar?')) return;
  try { await api('/api/admin/database/install', { method: 'POST', body: '{}' }); toast('Instalador MySQL iniciado.'); renderAdmin(); }
  catch (error) { toast(error.message, true); }
}

async function createApiKey() {
  try {
    const result = await api('/api/admin/api-keys', { method: 'POST', body: JSON.stringify({ label: 'Dashboard local' }) });
    document.getElementById('api-key-output').innerHTML = `<div class="notice"><strong>Guarda esta clave ahora, no volverá a mostrarse:</strong><div class="row wrap mt"><code class="code-token">${esc(result.key)}</code><button class="btn" id="copy-api-key">Copiar</button></div><p>Endpoint de lectura: <span class="code-token">GET /api/dashboard</span> con <span class="code-token">Authorization: Bearer …</span></p></div>`;
    document.getElementById('copy-api-key').addEventListener('click', () => navigator.clipboard.writeText(result.key).then(() => toast('API key copiada.')).catch(() => toast('No se pudo copiar; selecciónala manualmente.', true)));
    toast('API key creada.');
  } catch (error) { toast(error.message, true); }
}

async function removeApiKey(keyId) {
  if (!confirm('¿Eliminar esta API key? Los clientes que la usan dejarán de funcionar.')) return;
  try {
    await api(`/api/admin/api-keys/${keyId}`, { method: 'DELETE' });
    toast('API key eliminada.');
    renderAdmin();
  } catch (error) { toast(error.message, true); }
}

function openModal(title, body) {
  modalRoot.innerHTML = `<div class="modal-backdrop" data-backdrop><section class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><div class="modal-head"><div><h2>${esc(title)}</h2></div><button class="modal-close" data-close aria-label="Cerrar">×</button></div>${body}</section></div>`;
  modalRoot.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', closeModal));
  modalRoot.querySelector('[data-backdrop]').addEventListener('click', event => {
    if (event.target === event.currentTarget) closeModal();
  });
}

function closeModal() {
  modalRoot.innerHTML = '';
}

async function openCreateServer() {
  try {
    const users = await api('/api/users');
    openModal('Crear servidor', `<p class="muted tiny">Asigna software y cuotas aisladas a una cuenta.</p>
      <form id="create-server-form">
        <div class="form-grid">
          <label class="field">Nombre<input class="input" name="name" required maxlength="48" placeholder="Survival"></label>
          <label class="field">Usuario<select class="select" name="ownerId" required>${users.map(user => `<option value="${esc(user.id)}">${esc(user.username)}</option>`).join('')}</select></label>
          <div class="field software-field"><span>Software</span><div id="create-software-choices" class="software-switcher" role="group" aria-label="Tipo de software">${softwareChoiceButtons('paper', 'data-create-software')}</div><input type="hidden" id="create-software" name="software" value="paper"></div>
          <label class="field">Versión<select class="select" id="create-version" name="version"><option value="">Cargando versiones…</option></select></label>
          <label class="field" id="create-build-wrap">Build<select class="select" id="create-build" name="build"><option value="">Selecciona versión</option></select></label>
          <label class="field">RAM (MiB)<input class="input" type="number" name="ramMb" value="2048" min="512" max="131072" required></label>
          <label class="field">Almacenamiento (MiB)<input class="input" type="number" name="diskMb" value="10240" min="1024" max="1048576" required></label>
          <label class="field">Puerto<input class="input" type="number" name="port" value="25565" min="1024" max="65535" required></label>
        </div><div class="notice">Las asignaciones se validan contra la capacidad configurada del nodo. La primera descarga se realiza después de crear la instancia, desde la pestaña Versiones.</div>
        <div class="modal-foot"><button type="button" class="btn" data-close>Cancelar</button><button class="btn btn-primary">Crear servidor</button></div>
      </form>`);
    const softwareSelect = document.getElementById('create-software');
    const versionSelect = document.getElementById('create-version');
    const buildSelect = document.getElementById('create-build');
    const buildWrap = document.getElementById('create-build-wrap');
    async function loadBuilds() {
      const software = softwareSelect.value;
      buildWrap.style.display = software === 'vanilla' ? 'none' : '';
      if (software === 'vanilla') {
        buildSelect.innerHTML = '<option value="">No aplica</option>';
        return;
      }
      if (!versionSelect.value) return;
      buildSelect.innerHTML = '<option>Cargando…</option>';
      try {
        const data = await api(`/api/software/${software}/versions/${encodeURIComponent(versionSelect.value)}/builds`);
        const builds = data.builds || [];
        buildSelect.innerHTML = builds.map(item => {
          const value = String(typeof item === 'object' ? item.id || item.build || '' : item);
          const label = typeof item === 'object' && item.label ? String(item.label) : value;
          return value ? `<option value="${esc(value)}">${esc(label)}</option>` : '';
        }).join('') || '<option value="">No hay builds</option>';
      } catch (error) {
        buildSelect.innerHTML = `<option value="">${esc(error.message)}</option>`;
      }
    }
    async function loadVersions() {
      versionSelect.innerHTML = '<option value="">Cargando…</option>';
      try {
        const data = await api(`/api/software/${softwareSelect.value}/versions`);
        versionSelect.innerHTML = (data.versions || []).map(item => {
          const value = versionId(item);
          return value ? `<option value="${esc(value)}">${esc(value)}</option>` : '';
        }).join('');
        await loadBuilds();
      } catch (error) {
        versionSelect.innerHTML = `<option value="">${esc(error.message)}</option>`;
        toast(error.message, true);
      }
    }
    document.querySelectorAll('#create-software-choices [data-create-software]').forEach(button => button.addEventListener('click', () => {
      softwareSelect.value = button.dataset.createSoftware;
      document.querySelectorAll('#create-software-choices [data-create-software]').forEach(option => {
        option.classList.toggle('active', option === button);
        option.setAttribute('aria-pressed', String(option === button));
      });
      loadVersions();
    }));
    versionSelect.addEventListener('change', loadBuilds);
    await loadVersions();
    document.getElementById('create-server-form').addEventListener('submit', async event => {
      event.preventDefault();
      const values = Object.fromEntries(new FormData(event.currentTarget));
      values.ramMb = Number(values.ramMb);
      values.diskMb = Number(values.diskMb);
      values.port = Number(values.port);
      try {
        await api('/api/servers', { method: 'POST', body: JSON.stringify(values) });
        closeModal();
        toast('Servidor creado. Ahora descarga el software en Versiones.');
        if (state.page === 'admin') renderAdmin();
        else renderPage();
      } catch (error) { toast(error.message, true); }
    });
  } catch (error) { toast(error.message, true); }
}

async function boot() {
  try {
    const result = await api('/api/bootstrap');
    state.csrf = result.csrfToken;
    state.user = result.user;
    state.settings = {
      theme: result.theme,
      accentColor: result.accentColor || '',
      buttonStyle: result.buttonStyle || 'Gradient',
      backgroundStyle: result.backgroundStyle || 'Gradient',
      backgroundStart: result.backgroundStart || '#151027',
      backgroundEnd: result.backgroundEnd || '#211644',
      announcement: result.announcement || '',
      discordUrl: result.discordUrl || '',
      customLinks: result.customLinks || [],
      nodeName: result.nodeName || 'Nexory Node',
      platformLabel: result.platformLabel || 'Windows',
    };
    setTheme(result.theme, state.settings.accentColor, state.settings.buttonStyle, state.settings.backgroundStyle, state.settings.backgroundStart, state.settings.backgroundEnd);
    if (!state.user) {
      authPage(result.setupRequired, result.registrationEnabled);
      return;
    }
    state.page = 'servers';
    renderShell();
  } catch (error) {
    appRoot.innerHTML = `<main class="auth-screen"><section class="auth-card"><div class="brand">${brandMark()}NexoryPanel</div><h1>No se pudo iniciar</h1><p class="sub">${esc(error.message)}</p><div class="notice">Ejecuta NexoryPanel con start.bat para iniciar el servidor local.</div></section></main>`;
  }
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-toggle]');
  if (!button) return;
  const input = button.parentElement.querySelector(`input[name="${button.dataset.toggle}"]`);
  const enabled = input.value !== 'true';
  input.value = String(enabled);
  button.classList.toggle('on', enabled);
  button.setAttribute('aria-checked', String(enabled));
});

document.addEventListener('keydown', event => {
  if (event.key === 'Escape') closeModal();
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    if (document.getElementById('editor-content')) {
      event.preventDefault();
      saveEditorContent();
    }
  }
});

window.addEventListener('beforeunload', event => {
  if (editorIsDirty()) {
    event.preventDefault();
    event.returnValue = '';
  }
});

boot();

const root = document.querySelector('#app');
const modal = document.querySelector('#modal');
const toastNode = document.querySelector('#toast');
const state = {token: sessionStorage.getItem('haven-token'), user: null, page: 'overview', apartment: 'all', search: '', data: null, loading: false, error: '', pending: new Set()};
const controllable = new Set(['light', 'fan', 'switch', 'smart_plug', 'air_conditioner']);
const paths = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-8H9v8H4a1 1 0 0 1-1-1Z"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  building: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h1m4 0h1M9 11h1m4 0h1M9 15h1m4 0h1m-4 6v-3h2v3"/>',
  bolt: '<path d="m13 2-9 12h7l-1 8 10-12h-7Z"/>',
  wallet: '<path d="M20 8V5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h15V8H5a1 1 0 0 1 0-3"/><path d="M20 12h-5v5h5m-3-2.5h.1"/>',
  users: '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-17a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 4v3"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/>',
  logout: '<path d="M9 4H4v16h5m5-12 4 4-4 4M8 12h12"/>',
  light: '<path d="M8 15a6 6 0 1 1 8 0l-1 3H9Zm1 6h6"/>',
  fan: '<circle cx="12" cy="12" r="2"/><path d="M12 10c-5-7 4-11 6-6 1 3-2 6-4 7m0 2c8-1 7 9 2 9-3 0-5-4-5-8m-1-2c-3 7-11 2-8-2 2-3 6-2 8 0"/>',
  switch: '<rect x="3" y="6" width="18" height="12" rx="6"/><circle cx="9" cy="12" r="3"/>',
  power: '<path d="M12 2v9m-5-6a9 9 0 1 0 10 0"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  alert: '<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3h.01"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  edit: '<path d="m15 4 5 5-11 11H4v-5Zm-2 2 5 5"/>',
  leaf: '<path d="M19 3C6 2 2 10 6 16s16 4 13-13ZM4 21 15 9"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2l-2 2m0 3h.01"/>',
};
const icon = (name, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.power}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const isAdmin = () => state.user?.role === 'admin';
const initials = name => (name || '').split(' ').map(x => x[0]).slice(0,2).join('').toUpperCase();
const money = (minor, currency = 'XAF') => {
  try { const digits = new Intl.NumberFormat('en', {style:'currency', currency}).resolvedOptions().maximumFractionDigits;
    return new Intl.NumberFormat('en', {style:'currency', currency, maximumFractionDigits:digits}).format(minor / 10 ** digits);
  } catch { return `${Number(minor).toLocaleString()} ${currency} minor units`; }
};
const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString('en', {month:'short', day:'numeric', year:'numeric'});
const periodLabel = value => new Date(`${value}-01T12:00:00`).toLocaleDateString('en', {month:'long', year:'numeric'});
const badge = (value, label = value) => `<span class="badge ${esc(value)}"><i></i>${esc(label)}</span>`;
const button = (label, action, extra = '', cls = 'secondary') => `<button class="button ${cls}" data-action="${action}" ${extra}>${label}</button>`;
const empty = (title, body, action = '') => `<div class="empty">${icon('leaf')}<h3>${esc(title)}</h3><p>${esc(body)}</p>${action}</div>`;
const find = (type, id) => state.data?.[type]?.find(x => x.id === Number(id));
const apartmentName = id => find('apartments', id)?.name || 'Previous apartment';
const tenantName = id => find('users', id)?.full_name || (state.user.id === id ? state.user.full_name : `Resident ${id}`);
const deviceName = id => find('devices', id)?.name || 'Unavailable device';
const deviceUrl = d => `/apartments/${d.apartment_id}/rooms/${d.room_id}/devices/${d.id}`;

let toastTimer;
function toast(message, error = false) {
  clearTimeout(toastTimer); toastNode.textContent = message;
  toastNode.className = `toast visible ${error ? 'error' : ''}`;
  toastTimer = setTimeout(() => { toastNode.className = 'toast'; }, 5000);
}
async function api(path, options = {}) {
  const requestToken = state.token;
  const response = await fetch(path, { ...options, headers: {'Content-Type':'application/json', ...(requestToken ? {Authorization:`Bearer ${requestToken}`} : {}), ...options.headers}});
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== '/users/login' && state.token === requestToken) {
      logout();
      toast('Your session has expired. Please sign in again.', true);
    }
    let message = data?.detail || `Request failed (${response.status}).`;
    if (Array.isArray(message)) message = message.map(x => `${x.loc.slice(1).join(' ')}: ${x.msg}`).join('; ');
    throw new Error(message);
  }
  return data;
}
const send = (path, method, data) => api(path, {method, ...(data === undefined ? {} : {body:JSON.stringify(data)})});
function logout() {
  sessionStorage.removeItem('haven-token'); state.token = null; state.user = null; state.data = null;
  state.page = 'overview'; state.apartment = 'all'; state.error = ''; state.search = ''; state.updated = null; state.loading = false;
  if (modal.open) modal.close(); render();
}
async function allRent() {
  const items = [];
  for (let offset = 0; ; offset += 200) {
    const page = await api(`/rent/?limit=200&offset=${offset}`); items.push(...page);
    if (page.length < 200) return items;
  }
}
async function loadData() {
  const token = state.token; state.loading = true; state.error = ''; render();
  try {
    const [summary, apartments, rent, users] = await Promise.all([
      api('/dashboard/summary'), api('/apartments/'), allRent(), isAdmin() ? api('/users/') : Promise.resolve([state.user]),
    ]);
    const rooms = (await Promise.all(apartments.map(a => api(`/apartments/${a.id}/rooms/`)))).flat();
    const [devices, rules] = await Promise.all([
      Promise.all(rooms.map(async r => (await api(`/apartments/${r.apartment_id}/rooms/${r.id}/devices/`)).map(d => ({...d, apartment_id:r.apartment_id, room_name:r.name})))),
      Promise.all(apartments.map(a => api(`/apartments/${a.id}/automations/`))),
    ]);
    if (state.token !== token) return;
    if (state.apartment !== 'all' && !apartments.some(a => String(a.id) === state.apartment)) state.apartment = 'all';
    state.data = {summary, apartments, rent, users, rooms, devices:devices.flat(), rules:rules.flat()};
    state.updated = new Date();
  } catch (error) { if (state.token === token) state.error = error.message; }
  finally { if (state.token === token) { state.loading = false; render(); } }
}
function loginView() {
  return `<main class="login-shell"><section class="login-story"><a class="brand" href="/dashboard">${icon('home')}<span>haven<span class="brand-caption">SMART APARTMENT</span></span></a><div class="login-copy"><span class="eyebrow light">A BETTER WAY TO FEEL AT HOME</span><h1>A little less managing.<br>A lot more living.</h1><p>Your apartments, everyday comforts, and the people who call them home. All in one place.</p></div><div class="house-scene" aria-hidden="true"><div class="scene-sun"></div><div class="scene-house"><div class="window one"></div><div class="window two"></div><div class="window three"></div><div class="window four"></div><div class="scene-door"></div></div><div class="scene-plant"></div><div class="scene-caption">Thoughtfully connected.</div></div><span class="story-foot">SMART SPACES. SIMPLE DAYS.</span></section><section class="login-panel"><div class="login-form-wrap"><span class="eyebrow">WELCOME HOME</span><h2>Make yourself at home.</h2><p class="muted">Sign in to your apartment dashboard.</p><form id="login-form"><label>Email address<input name="email" type="email" autocomplete="username" placeholder="you@example.com" required></label><label>Password<input name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required></label><p id="login-error" class="form-error" role="alert"></p><button class="button primary wide" type="submit">Sign in ${icon('arrow')}</button></form><div class="login-note">${icon('home')}<div><strong>One home. The right view.</strong><p>Admins manage the property. Residents see their own apartment and rent.</p></div></div><p class="login-bottom">Smart Apartment Management System</p></div></section></main>`;
}
function navItems() {
  return [['overview','grid','Overview'],['apartments','building',isAdmin() ? 'Apartments & devices' : 'My apartment'],['automations','bolt','Automations'],['rent','wallet','Rent & payments'],...(isAdmin() ? [['residents','users','Residents']] : [])];
}
function render() {
  if (!state.user) { root.innerHTML = loginView(); return; }
  const titles = {overview:'Overview',apartments:isAdmin()?'Apartments & devices':'My apartment',automations:'Automations',rent:'Rent & payments',residents:'Residents'};
  const date = new Date().toLocaleDateString('en', {weekday:'short', month:'short', day:'numeric'});
  root.innerHTML = `<div class="app-shell"><aside class="sidebar"><a class="brand" href="/dashboard">${icon('home')}<span>haven<span class="brand-caption">SMART APARTMENT</span></span></a><div class="property-label"><span class="property-icon">${icon('building')}</span><span><strong>My property</strong><small>${isAdmin() ? 'Property management' : 'Resident space'}</small></span></div><span class="nav-caption">YOUR WORKSPACE</span><nav aria-label="Main navigation">${navItems().map(([id,ic,label]) => `<button data-action="navigate" data-page="${id}" class="nav-item ${state.page===id?'active':''}" ${state.page===id?'aria-current="page"':''}>${icon(ic)}<span>${label}</span>${state.page===id?'<i class="nav-dot"></i>':''}</button>`).join('')}</nav><div class="sidebar-bottom"><div class="calm-note">${icon('leaf')}<p>Good spaces.<br>Better everyday living.</p></div><button class="nav-item" data-action="help">${icon('help')}<span>Quick guide</span></button><div class="account"><span class="avatar">${esc(initials(state.user.full_name))}</span><span><strong>${esc(state.user.full_name)}</strong><small>${isAdmin()?'Administrator':'Resident'}</small></span><button class="icon-button" aria-label="Sign out" title="Sign out" data-action="logout">${icon('logout')}</button></div></div></aside><div class="workspace"><header class="topbar"><div class="breadcrumbs">Workspace <span>/</span> <strong>${titles[state.page]}</strong></div><div class="topbar-right"><span class="today">${date}</span><span class="role-label">${isAdmin()?'Admin view':'Resident view'}</span><span class="avatar small">${esc(initials(state.user.full_name))}</span></div></header><main class="content" id="main"><div class="page-heading"><div><span class="eyebrow">${state.page==='overview'?'EVERYDAY, A LITTLE EASIER':'YOUR CONNECTED PROPERTY'}</span><h1>${state.page==='overview'?`Welcome back, ${esc(state.user.full_name.split(' ')[0])}.`:titles[state.page]}</h1><p>${({overview:'Here’s what’s happening at home today.',apartments:'A comfortable home starts with the little things.',automations:'Small routines that take care of themselves.',rent:'A clear picture of what’s paid and what’s due.',residents:'The people who make your property a community.'})[state.page]}</p></div><div class="heading-actions">${button(`${icon('refresh',state.loading?'spinning':'')} Refresh`,'refresh',state.loading?'disabled':'','secondary compact')}${pageAction()}</div></div>${state.error?`<div class="error-banner" role="alert">${icon('alert')}<span>${esc(state.error)} ${state.data?'The last loaded data is shown.':''}</span>${button('Try again','refresh','','text-button')}</div>`:''}${state.data?pageView():`<div class="loading-state" role="status">${state.error?'Unable to load your workspace.':`${icon('refresh','spinning')} Bringing everything together…`}</div>`}<footer class="page-footer"><span>Haven · Smart Apartment</span><span>${state.updated?`Updated ${state.updated.toLocaleTimeString('en',{hour:'2-digit',minute:'2-digit'})}`:''} <i></i> Device state is simulated</span></footer></main></div></div>`;
}
function pageAction() {
  if (!isAdmin() || !state.data) return '';
  const actions = {overview:['Add apartment','add-apartment'],apartments:['Add apartment','add-apartment'],automations:['Create routine','add-rule'],rent:['Add rent charge','add-rent'],residents:['Add resident','add-resident']};
  const [label, action] = actions[state.page]; return button(`${icon('plus')} ${label}`,action,'','primary');
}
function pageView() { return ({overview:overviewView,apartments:apartmentsView,automations:automationsView,rent:rentView,residents:residentsView})[state.page](); }
function stat(label, value, description, ic, accent = '') { return `<article class="stat-card ${accent}"><div class="stat-top"><span>${label}</span><span class="stat-icon">${icon(ic)}</span></div><strong class="stat-value">${value}</strong><span class="stat-description">${description}</span></article>`; }
function overviewView() {
  const {summary:s, apartments, devices, rent} = state.data;
  const balances = s.rent_balances;
  const balanceText = balances.length ? balances.map(b=>esc(money(b.outstanding_minor,b.currency))).join('<br>') : money(0);
  const percent = s.apartments ? Math.round(s.occupied_apartments/s.apartments*100) : 0;
  const overdue = rent.filter(r=>r.status==='overdue');
  const offline = devices.filter(d=>!d.is_online);
  const quick = devices.filter(d=>controllable.has(d.type)).slice(0,4);
  return `<section class="stats-grid" aria-label="Property summary">${stat(isAdmin()?'Occupied apartments':'Your apartments',isAdmin()?`${s.occupied_apartments}<small> / ${s.apartments}</small>`:s.apartments,isAdmin()?`${s.available_apartments} available to welcome someone`:'Your connected space','building')}${stat('Devices online',`${s.online_devices}<small> / ${s.devices}</small>`,`${s.powered_on_devices} currently switched on`,'power')}${stat('Outstanding rent',balanceText,overdue.length?`${overdue.length} overdue ${overdue.length===1?'charge':'charges'} need attention`:'No overdue charges','wallet','money-stat')}${stat('Active routines',s.enabled_rules,`${s.automation_rules} routines in your workspace`,'bolt')}</section><div class="overview-grid"><section class="panel apartment-snapshot"><div class="panel-heading"><div><h2>${isAdmin()?'Your apartments':'Your home'}</h2><p>A little overview of every space.</p></div>${button('View all '+icon('arrow'),'navigate','data-page="apartments"','text-button')}</div>${apartments.length?`<div class="table-wrap"><table><thead><tr><th>Apartment</th><th>Status</th><th>Devices online</th><th></th></tr></thead><tbody>${apartments.slice(0,6).map(a=>{const ds=devices.filter(d=>d.apartment_id===a.id);return `<tr><td><div class="table-home"><span class="home-thumb floor-${a.floor%3}">${icon('building')}</span><div><strong>${esc(a.name)}</strong><small>Floor ${a.floor}</small></div></div></td><td>${badge(a.status)}</td><td><span class="device-count">${ds.filter(d=>d.is_online).length}<span> / ${ds.length}</span></span></td><td><button class="icon-button" aria-label="Open ${esc(a.name)}" data-action="open-apartment" data-id="${a.id}">${icon('arrow')}</button></td></tr>`}).join('')}</tbody></table></div>`:empty('Room for something new',isAdmin()?'Add your first apartment to get started.':'Your administrator will assign your apartment here.')}</section><section class="occupancy-panel"><div><span class="eyebrow">ROOM TO BELONG</span><h2>${isAdmin()?'A place for everyone.':'Your space, connected.'}</h2><p>${isAdmin()?'Keep a thoughtful eye on your property.':'Your home’s comforts, always close at hand.'}</p></div><div class="occupancy-ring" style="--occupancy:${percent}%"><div><strong>${percent}<span>%</span></strong><small>occupancy</small></div></div><div class="occupancy-legend"><span><i class="occupied-dot"></i> Occupied <b>${s.occupied_apartments}</b></span><span><i class="available-dot"></i> Available <b>${s.available_apartments}</b></span><span><i class="maintenance-dot"></i> Maintenance <b>${s.maintenance_apartments}</b></span></div></section><section class="panel"><div class="panel-heading"><div><h2>Everyday comforts</h2><p>A few favorites, one touch away.</p></div><span class="mini-label">QUICK CONTROLS</span></div><div class="quick-grid">${quick.length?quick.map(d=>deviceCard(d,true)).join(''):empty('No devices yet','Devices will appear here once they’re added.')}</div></section><section class="panel attention-panel"><div class="panel-heading"><div><h2>A little attention</h2><p>The things worth checking in on.</p></div><span class="count-bubble">${offline.length + overdue.length}</span></div><div class="attention-list">${overdue.length?`<button class="attention-item" data-action="navigate" data-page="rent"><span class="attention-icon amber">${icon('wallet')}</span><span><strong>${overdue.length} overdue rent ${overdue.length===1?'charge':'charges'}</strong><small>Review balances and payment records</small></span>${icon('chevron')}</button>`:''}${offline.length?`<button class="attention-item" data-action="navigate" data-page="apartments"><span class="attention-icon pale">${icon('power')}</span><span><strong>${offline.length} ${offline.length===1?'device is':'devices are'} offline</strong><small>${esc(offline.map(d=>d.name).slice(0,2).join(', '))}</small></span>${icon('chevron')}</button>`:''}${!overdue.length&&!offline.length?`<div class="all-clear">${icon('check')}<h3>All looking good.</h3><p>Nothing needs your attention right now.</p></div>`:''}</div><div class="gentle-note">${icon('leaf')} Little things, taken care of.</div></section></div>`;
}
function deviceCard(d, compact = false) {
  const supported=controllable.has(d.type), disabled=!d.is_online||!d.is_enabled||!supported;
  const explanation=!supported?'Read-only device':!d.is_enabled?'Disabled by administrator':!d.is_online?'Device offline':`${d.power==='on'?'Turn off':'Turn on'} ${d.name}`;
  return `<article class="device-card ${compact?'compact-device':''} ${d.power==='on'?'powered':''}"><div class="device-top"><span class="device-icon">${icon(d.type)}</span><button role="switch" aria-checked="${d.power==='on'}" aria-label="${esc(d.name)} power" title="${esc(explanation)}" class="toggle ${d.power==='on'?'on':''}" data-action="toggle-device" data-id="${d.id}" ${disabled?'disabled':''}><span></span></button></div><h3>${esc(d.name)}</h3><p>${esc(compact?apartmentName(d.apartment_id):d.room_name)}</p><div class="device-bottom"><span class="connection ${d.is_online&&d.is_enabled?'connected':''}"><i></i>${!d.is_enabled?'Disabled':!d.is_online?'Offline':d.power==='on'?'On':'Off'}</span>${isAdmin()&&!compact?`<button class="icon-button tiny" aria-label="Edit ${esc(d.name)}" data-action="edit-device" data-id="${d.id}">${icon('edit')}</button>`:''}</div></article>`;
}
function apartmentFilter() { return `<label class="filter-label">Apartment<select id="apartment-filter"><option value="all">All apartments</option>${state.data.apartments.map(a=>`<option value="${a.id}" ${state.apartment===String(a.id)?'selected':''}>${esc(a.name)}</option>`).join('')}</select></label>`; }
function apartmentsView() {
  const {apartments,devices,rooms}=state.data;
  const list=apartments.filter(a=>state.apartment==='all'||String(a.id)===state.apartment);
  return `<div class="filter-bar">${apartmentFilter()}<span class="muted">${list.length} ${list.length===1?'apartment':'apartments'} · ${devices.filter(d=>state.apartment==='all'||String(d.apartment_id)===state.apartment).length} devices</span></div>${list.length?`<div class="apartment-sections">${list.map(a=>`<section class="panel apartment-detail"><div class="panel-heading"><div class="table-home"><span class="home-thumb floor-${a.floor%3}">${icon('building')}</span><div><h2>${esc(a.name)}</h2><p>Floor ${a.floor} · ${rooms.filter(r=>r.apartment_id===a.id).length} rooms</p></div></div><div class="inline-actions">${badge(a.status)}${isAdmin()?button(icon('edit')+' Edit','edit-apartment',`data-id="${a.id}"`,'secondary compact'):''}</div></div><div class="devices-grid">${devices.filter(d=>d.apartment_id===a.id).map(d=>deviceCard(d)).join('')||empty('A fresh start','Add a room and its devices to make this space connected.')}</div>${isAdmin()?`<div class="panel-bottom"><span class="muted">${rooms.filter(r=>r.apartment_id===a.id).map(r=>esc(r.name)).join(' · ')||'No rooms yet'}</span><div class="inline-actions">${button(icon('plus')+' Room','add-room',`data-id="${a.id}"`,'text-button')}${button(icon('plus')+' Device','add-device',`data-id="${a.id}"`,'secondary compact')}</div></div>`:''}</section>`).join('')}</div>`:empty('No apartment to show',isAdmin()?'Add an apartment to start building your property.':'Your administrator has not assigned you an apartment yet.')}`;
}
function automationsView() {
  const rules=state.data.rules.filter(r=>state.apartment==='all'||String(r.apartment_id)===state.apartment);
  return `<div class="filter-bar">${apartmentFilter()}<span class="muted">${rules.filter(r=>r.is_enabled).length} enabled routines</span></div><div class="info-strip">${icon('bolt')}<span>Routines respond to device controls. You can also run them once to apply their conditions now.</span></div>${rules.length?`<div class="rules-grid">${rules.map(r=>`<article class="panel rule-card"><div class="rule-heading"><span class="rule-icon">${icon('bolt')}</span>${badge(r.is_enabled?'enabled':'disabled')}</div><h2>${esc(r.name)}</h2><p class="muted">${esc(apartmentName(r.apartment_id))}</p><div class="rule-flow"><div><span class="flow-label">WHEN</span><strong>${esc(deviceName(r.source_device_id))}</strong><small>is switched ${esc(r.source_power)}</small></div>${icon('arrow')}<div><span class="flow-label">THEN</span><strong>${esc(deviceName(r.target_device_id))}</strong><small>switch ${esc(r.target_power)}</small></div></div><div class="rule-footer">${button('Run apartment routines','evaluate-rules',`data-id="${r.apartment_id}"`,'text-button')}${isAdmin()?`<div class="inline-actions"><button class="icon-button" aria-label="Edit ${esc(r.name)}" data-action="edit-rule" data-id="${r.id}">${icon('edit')}</button><button class="toggle ${r.is_enabled?'on':''}" role="switch" aria-label="${esc(r.name)} enabled" aria-checked="${r.is_enabled}" data-action="toggle-rule" data-id="${r.id}"><span></span></button></div>`:''}</div></article>`).join('')}</div>`:empty('Let the little things happen',isAdmin()?'Create a routine, like turning on the light when the welcome switch is on.':'Your administrator can create routines for your home.')}`;
}
function rentView() {
  const {rent,summary}=state.data;
  const filtered=rent.filter(r=>!state.search||`${tenantName(r.tenant_id)} ${r.period} ${r.status} ${apartmentName(r.apartment_id)}`.toLowerCase().includes(state.search.toLowerCase()));
  return `<div class="rent-summary">${summary.rent_balances.length?summary.rent_balances.map(b=>`<section class="balance-card"><span class="eyebrow">${esc(b.currency)} BALANCE</span><strong>${esc(money(b.outstanding_minor,b.currency))}</strong><span>${esc(money(b.overdue_minor,b.currency))} overdue</span></section>`).join(''):stat('Outstanding rent',money(0),'No charges yet','wallet')}<div class="rent-note">${icon('wallet')}<div><strong>Every payment, a clearer picture.</strong><p>Review monthly charges and recorded payments in one place.</p></div></div></div><section class="panel"><div class="panel-heading"><div><h2>${isAdmin()?'Rent ledger':'Your rent history'}</h2><p>${rent.length} total charges · amounts shown in their original currency</p></div><label class="search-field">${icon('search')}<input id="search" type="search" placeholder="Search rent records" aria-label="Search rent records" value="${esc(state.search)}"></label></div>${filtered.length?`<div class="table-wrap"><table><thead><tr>${isAdmin()?'<th>Resident</th>':''}<th>Period / apartment</th><th>Due</th><th>Charge</th><th>Paid</th><th>Balance</th><th>Status</th>${isAdmin()?'<th></th>':''}</tr></thead><tbody>${filtered.map(r=>`<tr>${isAdmin()?`<td><strong>${esc(tenantName(r.tenant_id))}</strong></td>`:''}<td><strong>${esc(periodLabel(r.period))}</strong><small>${esc(apartmentName(r.apartment_id))}</small></td><td>${dateLabel(r.due_date)}</td><td>${esc(money(r.amount_minor,r.currency))}</td><td>${esc(money(r.paid_amount_minor,r.currency))}</td><td><strong>${esc(money(r.balance_minor,r.currency))}</strong></td><td>${badge(r.status)}</td>${isAdmin()?`<td>${button(r.status==='paid'?'Edit payment':'Record payment','payment',`data-id="${r.id}"`,'secondary compact')}</td>`:''}</tr>`).join('')}</tbody></table></div>`:empty('No rent records found',rent.length?'Try a different search.':'Charges will appear here when your administrator adds them.')}</section>`;
}
function residentsView() {
  if (!isAdmin()) return '';
  const tenants=state.data.users.filter(u=>u.role==='tenant'&&(!state.search||`${u.full_name} ${u.email}`.toLowerCase().includes(state.search.toLowerCase())));
  return `<section class="panel"><div class="panel-heading"><div><h2>Your community</h2><p>Apartment assignments and account access.</p></div><label class="search-field">${icon('search')}<input id="search" type="search" aria-label="Search residents" placeholder="Search residents" value="${esc(state.search)}"></label></div>${tenants.length?`<div class="table-wrap"><table><thead><tr><th>Resident</th><th>Apartment</th><th>Account</th><th>Outstanding rent</th><th>Manage</th></tr></thead><tbody>${tenants.map(u=>{const sums={};state.data.rent.filter(r=>r.tenant_id===u.id).forEach(r=>{sums[r.currency]=(sums[r.currency]||0)+r.balance_minor});return `<tr><td><div class="table-home"><span class="avatar resident-avatar">${esc(initials(u.full_name))}</span><div><strong>${esc(u.full_name)}</strong><small>${esc(u.email)}</small></div></div></td><td>${u.apartment_id?esc(apartmentName(u.apartment_id)):'<span class="muted">Unassigned</span>'}</td><td>${badge(u.is_active?'active':'inactive')}</td><td>${Object.entries(sums).map(([c,v])=>esc(money(v,c))).join('<br>')||'—'}</td><td><div class="inline-actions">${button('Assignment','assign',`data-id="${u.id}"`,'secondary compact')}${button(u.is_active?'Deactivate':'Activate','user-status',`data-id="${u.id}"`,u.is_active?'text-button muted-button':'text-button')}</div></td></tr>`}).join('')}</tbody></table></div>`:empty('A community starts with someone','Add a resident, then assign their apartment.')}</section>`;
}

const input = (label,name,value='',type='text',extra='') => `<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const select = (label,name,options,value,extra='') => `<label>${label}<select name="${name}" ${extra}>${options.map(([v,t])=>`<option value="${esc(v)}" ${String(v)===String(value)?'selected':''}>${esc(t)}</option>`).join('')}</select></label>`;
const check = (label,name,checked) => `<label class="checkbox-label"><input name="${name}" type="checkbox" ${checked?'checked':''}>${label}</label>`;
function formDialog(title, body, onSubmit, {submit='Save changes', danger}={}) {
  modal.innerHTML=`<form id="action-form"><div class="modal-heading"><div><span class="eyebrow">YOUR PROPERTY, TAKEN CARE OF</span><h2 id="modal-title">${esc(title)}</h2></div><button type="button" class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close')}</button></div><div class="modal-body">${body}<p class="form-error" id="form-error" role="alert"></p></div><div class="modal-footer">${danger?`<button type="button" class="button danger" id="danger-action">Delete</button>`:''}<span class="spacer"></span><button type="button" class="button secondary" data-action="close-modal">Cancel</button><button type="submit" class="button primary">${submit}</button></div></form>`;
  modal.showModal();
  const form=modal.querySelector('form');
  form.addEventListener('submit', async event=>{event.preventDefault(); const submitButton=form.querySelector('[type=submit]'); if(submitButton.disabled)return;submitButton.disabled=true; const error=form.querySelector('#form-error'); error.textContent='';
    try { await onSubmit(new FormData(form)); modal.close(); await loadData(); }
    catch(e){error.textContent=e.message;} finally {submitButton.disabled=false;}
  });
  if(danger) modal.querySelector('#danger-action').addEventListener('click',async()=>{
    if(!confirm('Delete this record? This cannot be undone.'))return;
    try{await danger(); modal.close();toast('Record deleted.');await loadData();}catch(e){modal.querySelector('#form-error').textContent=e.message;}
  });
}
function ruleDialog(rule) {
  if(!state.data.apartments.length){toast('Add an apartment and two controllable devices first.',true);return;}
  const aid=rule?.apartment_id||(state.apartment==='all'?state.data.apartments[0].id:Number(state.apartment));
  const options=id=>state.data.devices.filter(d=>d.apartment_id===Number(id)&&controllable.has(d.type)).map(d=>[d.id,`${d.name} · ${d.room_name}`]);
  formDialog(rule?'Edit routine':'Create a routine',input('Routine name','name',rule?.name||'','text','required maxlength="100"')+select('Apartment','apartment_id',state.data.apartments.map(a=>[a.id,a.name]),aid,rule?'disabled':'')+`<div class="form-row">${select('When this device','source_device_id',options(aid),rule?.source_device_id,'required')}${select('Is switched','source_power',[['on','On'],['off','Off']],rule?.source_power||'on')}</div><div class="form-row">${select('Control this device','target_device_id',options(aid),rule?.target_device_id||options(aid)[1]?.[0],'required')}${select('Set power to','target_power',[['on','On'],['off','Off']],rule?.target_power||'on')}</div>`+check('Routine enabled','is_enabled',rule?.is_enabled??true),async f=>{
    const data={name:f.get('name'),source_device_id:Number(f.get('source_device_id')),source_power:f.get('source_power'),target_device_id:Number(f.get('target_device_id')),target_power:f.get('target_power'),is_enabled:f.has('is_enabled')};
    if(data.source_device_id===data.target_device_id)throw new Error('Choose two different devices.');
    await send(`/apartments/${rule?.apartment_id||f.get('apartment_id')}/automations/${rule?rule.id:''}`,rule?'PUT':'POST',data);toast(rule?'Routine updated.':'Your new routine is ready.');
  },{submit:rule?'Save routine':'Create routine',danger:rule?()=>send(`/apartments/${rule.apartment_id}/automations/${rule.id}`,'DELETE'):null});
  modal.querySelector('[name=apartment_id]').addEventListener('change',event=>{
    const opts=options(event.target.value); for(const name of ['source_device_id','target_device_id'])modal.querySelector(`[name=${name}]`).innerHTML=opts.map(([v,t])=>`<option value="${v}">${esc(t)}</option>`).join('');
    if(opts.length>1)modal.querySelector('[name=target_device_id]').value=opts[1][0];
  });
}
async function action(name, element) {
  const id=Number(element.dataset.id);
  if(name==='close-modal'){modal.close();return;}
  if(name==='logout'){logout();return;}
  if(name==='navigate'){state.page=element.dataset.page;state.search='';render();return;}
  if(name==='open-apartment'){state.apartment=String(id);state.page='apartments';render();return;}
  if(name==='refresh'){if(!state.loading)await loadData();return;}
  if(name==='help'){
    formDialog('A quick tour',`<div class="guide"><h3>1. Your everyday overview</h3><p>See apartment occupancy, devices, and rent balances at a glance.</p><h3>2. Try a little comfort</h3><p>In Apartments & devices, turn on a Welcome switch. Its routine also turns on the Pendant light.</p><h3>3. Keep the details in order</h3><p>${isAdmin()?'Record rent payments, create routines, or update resident assignments.':'Review your rent history and run the routines for your apartment.'}</p><p class="field-hint">Device changes update simulated state. They do not operate physical hardware.</p></div>`,async()=>{}, {submit:'Got it'});return;
  }
  if(name==='toggle-device') {const d=find('devices',id);await send(deviceUrl(d)+'/state','PUT',{power:d.power==='on'?'off':'on'});toast(`${d.name} switched ${d.power==='on'?'off':'on'}.`);await loadData();return;}
  if(name==='evaluate-rules'){const result=await send(`/apartments/${id}/automations/evaluate`,'POST');const changed=result.results.filter(r=>r.outcome==='applied').length;const unavailable=result.results.filter(r=>r.outcome==='unavailable').length;toast(`${changed} ${changed===1?'device updated':'devices updated'}.${unavailable?` ${unavailable} rules unavailable.`:''}`);await loadData();return;}
  if(!isAdmin())return;
  if(name==='add-apartment'||name==='edit-apartment'){
    const a=find('apartments',id);formDialog(a?'Edit apartment':'Add an apartment',input('Apartment name','name',a?.name||'','text','required maxlength="50"')+input('Floor','floor',a?.floor??1,'number','required min="0" max="100"')+select('Status','status',[['available','Available'],['occupied','Occupied'],['maintenance','Maintenance']],a?.status||'available'),async f=>{await send('/apartments/'+(a?a.id:''),a?'PATCH':'POST',{name:f.get('name'),floor:Number(f.get('floor')),status:f.get('status')});toast(a?'Apartment updated.':'Apartment added.');},{submit:a?'Save apartment':'Add apartment',danger:a?()=>send(`/apartments/${a.id}`,'DELETE'):null});return;
  }
  if(name==='add-room') {formDialog('Add a room',input('Room name','name','','text','required maxlength="100"')+select('Room type','type',[['living_room','Living room'],['bedroom','Bedroom'],['kitchen','Kitchen'],['bathroom','Bathroom'],['hallway','Hallway']],'living_room'),async f=>{await send(`/apartments/${id}/rooms/`,'POST',{name:f.get('name'),type:f.get('type')});toast('Room added.');},{submit:'Add room'});return;}
  if(name==='add-device'||name==='edit-device') {
    const d=name==='edit-device'?find('devices',id):null, aid=d?.apartment_id||id;
    const rooms=state.data.rooms.filter(r=>r.apartment_id===aid);
    if(!rooms.length){toast('Add a room to this apartment first.',true);return;}
    const types=[...new Set([...controllable,'camera','sensor',...(d?[d.type]:[])])].map(x=>[x,x.replaceAll('_',' ')]);
    formDialog(d?'Edit device':'Add a device',input('Device name','name',d?.name||'','text','required maxlength="100"')+select('Room','room_id',rooms.map(r=>[r.id,r.name]),d?.room_id||rooms[0].id,d?'disabled':'')+select('Device type','type',types,d?.type||'light')+check('Online','is_online',d?.is_online??true)+check('Enabled','is_enabled',d?.is_enabled??true),async f=>{await send(d?deviceUrl(d):`/apartments/${aid}/rooms/${f.get('room_id')}/devices/`,d?'PATCH':'POST',{name:f.get('name'),type:f.get('type'),is_online:f.has('is_online'),is_enabled:f.has('is_enabled')});toast(d?'Device updated.':'Device added.');},{submit:d?'Save device':'Add device',danger:d?()=>send(deviceUrl(d),'DELETE'):null});return;
  }
  if(name==='add-rule'||name==='edit-rule'){ruleDialog(find('rules',id));return;}
  if(name==='toggle-rule'){const r=find('rules',id);const {name,source_device_id,source_power,target_device_id,target_power}=r;await send(`/apartments/${r.apartment_id}/automations/${r.id}`,'PUT',{name,source_device_id,source_power,target_device_id,target_power,is_enabled:!r.is_enabled});toast(r.is_enabled?'Routine disabled.':'Routine enabled.');await loadData();return;}
  if(name==='add-rent'){
    const tenants=state.data.users.filter(u=>u.role==='tenant'&&u.is_active&&u.apartment_id);
    if(!tenants.length){toast('Assign an active resident to an apartment first.',true);return;}
    const today=new Date().toISOString().slice(0,10);
    formDialog('Add a rent charge',select('Resident','tenant_id',tenants.map(u=>[u.id,`${u.full_name} · ${apartmentName(u.apartment_id)}`]),tenants[0].id)+`<div class="form-row">${input('Month','period',today.slice(0,7),'month','required')}${input('Due date','due_date',today,'date','required')}</div><div class="form-row">${input('Charge (minor units)','amount_minor','','number','required min="1" max="2000000000" step="1"')}${select('Currency','currency',[['XAF','XAF · CFA franc'],['USD','USD · US dollar'],['EUR','EUR · Euro']],'XAF')}</div><p class="field-hint">XAF: 1 unit = 1 franc. USD/EUR: 100 units = 1 dollar/euro.</p>`,async f=>{await send('/rent/','POST',{tenant_id:Number(f.get('tenant_id')),period:f.get('period'),due_date:f.get('due_date'),amount_minor:Number(f.get('amount_minor')),currency:f.get('currency')});toast('Rent charge added.');},{submit:'Add charge'});return;
  }
  if(name==='payment') {const r=find('rent',id);formDialog('Record a payment',`<div class="payment-context"><strong>${esc(tenantName(r.tenant_id))}</strong><span>${periodLabel(r.period)} · ${esc(apartmentName(r.apartment_id))}</span><h3>${esc(money(r.amount_minor,r.currency))}</h3><small>Total charge</small></div>`+input(`Total paid so far (${esc(r.currency)} minor units)`,'paid_amount_minor',r.paid_amount_minor,'number',`required min="0" max="${r.amount_minor}" step="1"`)+`<p class="field-hint">Enter the cumulative amount paid, including previous payments. This records a payment; it does not transfer money.</p>`,async f=>{await send(`/rent/${r.id}/payment`,'PUT',{paid_amount_minor:Number(f.get('paid_amount_minor'))});toast('Payment record updated.');},{submit:'Save payment'});return;}
  if(name==='assign') {const u=find('users',id);formDialog('Apartment assignment',`<p class="modal-description">Choose a home for <strong>${esc(u.full_name)}</strong>.</p>`+select('Apartment','apartment_id',[['','Unassigned'],...state.data.apartments.filter(a=>a.status!=='maintenance'||a.id===u.apartment_id).map(a=>[a.id,a.name])],u.apartment_id||''),async f=>{const aid=f.get('apartment_id');if(aid)await send(`/users/${u.id}/apartment`,'PUT',{apartment_id:Number(aid)});else if(u.apartment_id)await send(`/users/${u.id}/apartment`,'DELETE');toast('Assignment updated.');});return;}
  if(name==='user-status'){const u=find('users',id);if(u.is_active&&!confirm(`Deactivate ${u.full_name}? They will lose access until reactivated. Their apartment assignment will remain.`))return;await send(`/users/${u.id}/status`,'PATCH',{is_active:!u.is_active});toast(u.is_active?'Resident account deactivated.':'Resident account activated.');await loadData();return;}
  if(name==='add-resident') {formDialog('Welcome a resident',input('Full name','full_name','','text','required minlength="2" maxlength="100"')+input('Email address','email','','email','required')+input('Initial password','password','','password','required minlength="8" maxlength="128" autocomplete="new-password"')+`<p class="field-hint">Share the initial password securely with the resident. Assign their apartment after creating their account.</p>`,async f=>{await send('/users/register','POST',{full_name:f.get('full_name'),email:f.get('email'),password:f.get('password')});toast('Resident created. Choose Assignment to add their apartment.');},{submit:'Add resident'});return;}
}
document.addEventListener('click',async event=>{
  const element=event.target.closest('[data-action]'); if(!element||element.disabled)return;
  const key=`${element.dataset.action}:${element.dataset.id||''}`;if(state.pending.has(key))return;
  state.pending.add(key);
  try{await action(element.dataset.action,element);}catch(error){toast(error.message,true);}finally{state.pending.delete(key);}
});
document.addEventListener('change',event=>{if(event.target.id==='apartment-filter'){state.apartment=event.target.value;render();}});
document.addEventListener('input',event=>{if(event.target.id==='search'){const pos=event.target.selectionStart;state.search=event.target.value;render();const field=document.querySelector('#search');field.focus();try{field.setSelectionRange(pos,pos);}catch{}}});
document.addEventListener('submit',async event=>{
  if(event.target.id!=='login-form')return;event.preventDefault();const form=event.target, button=form.querySelector('button');button.disabled=true;button.textContent='Signing in…';
  const values=new FormData(form);
  try{const login=await send('/users/login','POST',{email:values.get('email'),password:values.get('password')});state.token=login.access_token;sessionStorage.setItem('haven-token',state.token);state.user=await api('/users/me');await loadData();}
  catch(error){state.token=null;sessionStorage.removeItem('haven-token');const message=document.querySelector('#login-error');if(message)message.textContent=error.message;button.disabled=false;button.innerHTML=`Sign in ${icon('arrow')}`;}
});
async function start(){render();if(state.token){try{state.user=await api('/users/me');await loadData();}catch{logout();toast('Please sign in again.',true);}}}
start();

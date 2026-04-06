const API_BASE = "";

// ---------- Auth ----------
const authFormEl = document.getElementById("authForm");
const authInfoEl = document.getElementById("authInfo");
const authUsernameEl = document.getElementById("authUsername");
const authPasswordEl = document.getElementById("authPassword");
const authErrorEl = document.getElementById("authError");
const authUserDisplayEl = document.getElementById("authUserDisplay");
const loginBtn = document.getElementById("loginBtn");
const registerBtn = document.getElementById("registerBtn");
const logoutBtn = document.getElementById("logoutBtn");

function getToken() { return localStorage.getItem("ss_token"); }
function getUser() { return localStorage.getItem("ss_user"); }
function setAuth(token, username) {
  localStorage.setItem("ss_token", token);
  localStorage.setItem("ss_user", username);
}
function clearAuth() {
  localStorage.removeItem("ss_token");
  localStorage.removeItem("ss_user");
}
function authHeaders() {
  const t = getToken();
  return t ? { "Authorization": "Bearer " + t } : {};
}
function isLoggedIn() { return !!getToken(); }

function setAuthError(text) {
  authErrorEl.textContent = text || "";
}

function updateAuthUI() {
  const user = getUser();
  if (user) {
    authFormEl.style.display = "none";
    authInfoEl.style.display = "flex";
    authUserDisplayEl.textContent = user;
    tabFavoritesBtn.style.display = "";
    thStarEl.style.display = "";
    loadWatchlist();
  } else {
    authFormEl.style.display = "flex";
    authInfoEl.style.display = "none";
    tabFavoritesBtn.style.display = "none";
    thStarEl.style.display = "none";
    if (activeTab === "favorites") switchTab("all");
  }
  applySpreadsFilter();
}

async function authAction(endpoint) {
  setAuthError("");
  const username = authUsernameEl.value.trim();
  const password = authPasswordEl.value;
  if (!username || !password) { setAuthError("Введите имя пользователя и пароль"); return; }

  try {
    const res = await fetch(`${API_BASE}/api/auth/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) { setAuthError(data.detail || "Ошибка авторизации"); return; }
    setAuth(data.access_token, username);
    authUsernameEl.value = "";
    authPasswordEl.value = "";
    updateAuthUI();
  } catch (e) { setAuthError("Ошибка сети"); console.error(e); }
}

loginBtn.addEventListener("click", () => authAction("login"));
registerBtn.addEventListener("click", () => authAction("register"));
logoutBtn.addEventListener("click", () => { clearAuth(); updateAuthUI(); });
authPasswordEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); authAction("login"); }
});

// ---------- Watchlist (favorites) ----------
let watchlistSymbols = new Set();

async function loadWatchlist() {
  if (!isLoggedIn()) { watchlistSymbols.clear(); return; }
  try {
    const res = await fetch(`${API_BASE}/api/watchlist`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    watchlistSymbols = new Set((data.items || []).map(i => i.symbol));
    favCountEl.textContent = watchlistSymbols.size;
    applySpreadsFilter();
  } catch (e) { console.error(e); }
}

async function toggleWatchlist(symbol) {
  if (!isLoggedIn()) return;
  try {
    if (watchlistSymbols.has(symbol)) {
      await fetch(`${API_BASE}/api/watchlist/${encodeURIComponent(symbol)}`, {
        method: "DELETE", headers: authHeaders(),
      });
      watchlistSymbols.delete(symbol);
    } else {
      await fetch(`${API_BASE}/api/watchlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ symbol }),
      });
      watchlistSymbols.add(symbol);
    }
    favCountEl.textContent = watchlistSymbols.size;
    applySpreadsFilter();
  } catch (e) { console.error(e); }
}

// ---------- Arbitrage Calculator ----------
const arbHintEl = document.getElementById("arbHint");
const arbCalcEl = document.getElementById("arbCalc");
const arbSymbolEl = document.getElementById("arbSymbol");
const arbSpreadBadgeEl = document.getElementById("arbSpreadBadge");
const arbBuyExchangeEl = document.getElementById("arbBuyExchange");
const arbBuyPriceEl = document.getElementById("arbBuyPrice");
const arbSellExchangeEl = document.getElementById("arbSellExchange");
const arbSellPriceEl = document.getElementById("arbSellPrice");
const arbAmountEl = document.getElementById("arbAmount");
const arbResultsEl = document.getElementById("arbResults");
const arbTokensEl = document.getElementById("arbTokens");
const arbRevenueEl = document.getElementById("arbRevenue");
const arbProfitEl = document.getElementById("arbProfit");

let selectedSpread = null;

function selectSpread(row) {
  selectedSpread = row;
  arbHintEl.style.display = "none";
  arbCalcEl.style.display = "block";

  arbSymbolEl.textContent = row.symbol;
  arbSpreadBadgeEl.textContent = `${formatNumber(Number(row.spread_pct), 4)}%`;
  arbBuyExchangeEl.textContent = row.low_exchange;
  arbBuyPriceEl.textContent = `${formatNumber(Number(row.low_price), 8)} USDT`;
  arbSellExchangeEl.textContent = row.high_exchange;
  arbSellPriceEl.textContent = `${formatNumber(Number(row.high_price), 8)} USDT`;

  calculateArbitrage();

  // Highlight selected row
  document.querySelectorAll(".selected-row").forEach(el => el.classList.remove("selected-row"));
  const rows = spreadsBodyEl.querySelectorAll("tr");
  rows.forEach(tr => {
    if (tr.dataset.symbol === row.symbol) tr.classList.add("selected-row");
  });
}

function calculateArbitrage() {
  if (!selectedSpread) return;
  const amountRaw = arbAmountEl.value.trim().replace(",", ".");
  const amount = Number(amountRaw);

  if (!amountRaw || !Number.isFinite(amount) || amount <= 0) {
    arbResultsEl.style.display = "none";
    return;
  }

  const buyPrice = Number(selectedSpread.low_price);
  const sellPrice = Number(selectedSpread.high_price);
  const tokens = amount / buyPrice;
  const revenue = tokens * sellPrice;
  const profit = revenue - amount;

  arbResultsEl.style.display = "block";
  arbTokensEl.textContent = formatNumber(tokens, 6);
  arbRevenueEl.textContent = `${formatNumber(revenue, 2)} USDT`;
  arbProfitEl.textContent = `+${formatNumber(profit, 2)} USDT (${formatNumber((profit / amount) * 100, 4)}%)`;
}

arbAmountEl.addEventListener("input", calculateArbitrage);
arbAmountEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); calculateArbitrage(); }
});

// ---------- Converter ----------
const fromAssetEl = document.getElementById("fromAsset");
const toAssetEl = document.getElementById("toAsset");
const amountEl = document.getElementById("amount");
const swapBtn = document.getElementById("swapBtn");
const convertBtn = document.getElementById("convertBtn");
const pairRateEl = document.getElementById("pairRate");
const convertResultEl = document.getElementById("convertResult");
const convertErrorEl = document.getElementById("convertError");

let converterRates = { base: "USD", rates: {} };

function getAssetRate(asset) { return converterRates?.rates?.[asset]; }

function formatNumber(value, digits = 6) {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: digits }).format(value);
}

function setConverterError(text) { convertErrorEl.textContent = text || ""; }

function fillAssetSelectors(assets) {
  fromAssetEl.innerHTML = "";
  toAssetEl.innerHTML = "";
  for (const asset of assets) {
    fromAssetEl.appendChild(new Option(asset, asset));
    toAssetEl.appendChild(new Option(asset, asset));
  }
  if (assets.includes("USD")) fromAssetEl.value = "USD";
  if (assets.includes("RUB")) toAssetEl.value = "RUB";
  if (fromAssetEl.value === toAssetEl.value && assets.length > 1) toAssetEl.value = assets[1];
}

function updatePairRateLabel() {
  const from = fromAssetEl.value, to = toAssetEl.value;
  const rFrom = getAssetRate(from), rTo = getAssetRate(to);
  if (!from || !to || typeof rFrom !== "number" || typeof rTo !== "number" || rFrom <= 0) {
    pairRateEl.textContent = "Курс: недоступен"; return null;
  }
  const rate = rTo / rFrom;
  pairRateEl.textContent = `Курс: 1 ${from} = ${formatNumber(rate, 8)} ${to}`;
  return rate;
}

function convertNow() {
  setConverterError("");
  const from = fromAssetEl.value, to = toAssetEl.value;
  const amountRaw = amountEl.value.trim().replace(",", ".");
  const amount = Number(amountRaw);
  const rFrom = getAssetRate(from), rTo = getAssetRate(to);

  if (!amountRaw) { setConverterError("Введите сумму"); convertResultEl.textContent = "Результат: —"; return; }
  if (!Number.isFinite(amount)) { setConverterError("Сумма должна быть числом"); convertResultEl.textContent = "Результат: —"; return; }
  if (amount <= 0) { setConverterError("Сумма должна быть больше 0"); convertResultEl.textContent = "Результат: —"; return; }
  if (typeof rFrom !== "number" || typeof rTo !== "number" || rFrom <= 0) { setConverterError("Курс для выбранной пары недоступен"); convertResultEl.textContent = "Результат: —"; return; }

  const result = (amount / rFrom) * rTo;
  convertResultEl.textContent = `Результат: ${formatNumber(result, 2)} ${to}`;
  updatePairRateLabel();
}

async function loadConverterRates() {
  const res = await fetch(`${API_BASE}/api/converter/rates`);
  if (!res.ok) throw new Error(`Failed to load rates: ${res.status}`);
  converterRates = await res.json();
  const assets = Object.keys(converterRates.rates || {}).sort();
  fillAssetSelectors(assets);
  updatePairRateLabel();
}

function preventSameCurrency(changedEl, otherEl, assets) {
  if (changedEl.value === otherEl.value && assets.length > 1) {
    const alt = assets.find(a => a !== changedEl.value);
    if (alt) otherEl.value = alt;
  }
}

swapBtn.addEventListener("click", () => {
  const a = fromAssetEl.value; fromAssetEl.value = toAssetEl.value; toAssetEl.value = a;
  updatePairRateLabel(); convertNow();
});
convertBtn.addEventListener("click", convertNow);
fromAssetEl.addEventListener("change", () => { preventSameCurrency(fromAssetEl, toAssetEl, Object.keys(converterRates.rates || {}).sort()); updatePairRateLabel(); convertNow(); });
toAssetEl.addEventListener("change", () => { preventSameCurrency(toAssetEl, fromAssetEl, Object.keys(converterRates.rates || {}).sort()); updatePairRateLabel(); convertNow(); });
amountEl.addEventListener("input", () => { updatePairRateLabel(); convertNow(); });
amountEl.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); convertNow(); } });

// ---------- Spreads ----------
const spreadsBodyEl = document.getElementById("spreadsBody");
const refreshSpreadsBtn = document.getElementById("refreshSpreadsBtn");
const symbolFilterEl = document.getElementById("symbolFilter");
const exchChkEls = Array.from(document.querySelectorAll(".exchChk"));
const sortSpreadsBtn = document.getElementById("sortSpreadsBtn");
const thStarEl = document.getElementById("thStar");
const tabFavoritesBtn = document.getElementById("tabFavorites");
const favCountEl = document.getElementById("favCount");

let sortDesc = true;
let activeTab = "all";
let spreadsData = [];

function getSelectedExchanges() {
  return exchChkEls.filter(chk => chk.checked).map(chk => chk.value);
}

function renderSpreadsTable(rows) {
  const loggedIn = isLoggedIn();
  const cols = loggedIn ? 8 : 7;

  if (!rows.length) {
    spreadsBodyEl.innerHTML = `<tr><td colspan="${cols}" class="muted">Нет данных для отображения</td></tr>`;
    return;
  }

  spreadsBodyEl.innerHTML = rows
    .map((r) => {
      const isFav = watchlistSymbols.has(r.symbol);
      const starCell = loggedIn
        ? `<td class="col-star"><button class="star-btn ${isFav ? 'active' : ''}" onclick="toggleWatchlist('${r.symbol}')" title="${isFav ? 'Убрать из избранного' : 'Добавить в избранное'}">${isFav ? '★' : '☆'}</button></td>`
        : '';
      const selected = selectedSpread && selectedSpread.symbol === r.symbol ? ' selected-row' : '';
      return `
      <tr class="fade-in clickable-row${selected}" data-symbol="${r.symbol}" onclick="onSpreadRowClick(this, '${r.symbol}')">
        ${starCell}
        <td>${r.symbol}</td>
        <td>${r.low_exchange}</td>
        <td>${formatNumber(Number(r.low_price), 8)}</td>
        <td>${r.high_exchange}</td>
        <td>${formatNumber(Number(r.high_price), 8)}</td>
        <td>${formatNumber(Number(r.spread_abs), 8)}</td>
        <td class="badge-up">${formatNumber(Number(r.spread_pct), 4)}%</td>
      </tr>`;
    })
    .join("");
}

function onSpreadRowClick(trEl, symbol) {
  const row = spreadsData.find(r => r.symbol === symbol);
  if (row) selectSpread(row);
}

function applySpreadsFilter() {
  const q = symbolFilterEl.value.trim().toUpperCase();
  let rows = spreadsData;

  if (activeTab === "favorites") {
    rows = rows.filter(r => watchlistSymbols.has(r.symbol));
  }

  if (q) {
    rows = rows.filter((r) => String(r.symbol || "").toUpperCase().includes(q));
  }

  rows = rows.slice().sort((a, b) => {
    const av = Number(a.spread_pct) || 0;
    const bv = Number(b.spread_pct) || 0;
    return sortDesc ? (bv - av) : (av - bv);
  });

  renderSpreadsTable(rows);
}

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  applySpreadsFilter();
}

// Tab clicks
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

async function loadSpreads() {
  refreshSpreadsBtn.disabled = true;
  refreshSpreadsBtn.textContent = "Обновление...";
  try {
    const selected = getSelectedExchanges();
    const exchParam = selected.length ? `&exchanges=${encodeURIComponent(selected.join(","))}` : "";
    const res = await fetch(`${API_BASE}/api/spreads?limit=100${exchParam}`);
    if (!res.ok) throw new Error(`Failed to load spreads: ${res.status}`);
    const data = await res.json();
    spreadsData = Array.isArray(data.records) ? data.records : [];
    applySpreadsFilter();
  } catch (e) {
    const cols = isLoggedIn() ? 8 : 7;
    spreadsBodyEl.innerHTML = `<tr><td colspan="${cols}" class="muted">Ошибка загрузки спредов</td></tr>`;
    console.error(e);
  } finally {
    refreshSpreadsBtn.disabled = false;
    refreshSpreadsBtn.textContent = "Обновить";
  }
}

refreshSpreadsBtn.addEventListener("click", loadSpreads);
symbolFilterEl.addEventListener("input", applySpreadsFilter);
exchChkEls.forEach(chk => chk.addEventListener("change", loadSpreads));
sortSpreadsBtn.addEventListener("click", () => {
  sortDesc = !sortDesc;
  sortSpreadsBtn.textContent = `Сортировка: Спред % ${sortDesc ? "↓" : "↑"}`;
  applySpreadsFilter();
});

// ---------- Init ----------
async function init() {
  updateAuthUI();

  try { await loadConverterRates(); }
  catch (e) { console.error(e); setConverterError("Не удалось загрузить локальные котировки"); }

  await loadSpreads();
  setTimeout(loadSpreads, 2000);
  setInterval(loadSpreads, 5000);
}

init();

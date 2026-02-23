const API_BASE = ""; // backend раздает и frontend, и API с одного хоста

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

function getAssetRate(asset) {
  return converterRates?.rates?.[asset];
}

function formatNumber(value, digits = 6) {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: digits,
  }).format(value);
}

function setConverterError(text) {
  convertErrorEl.textContent = text || "";
}

function fillAssetSelectors(assets) {
  fromAssetEl.innerHTML = "";
  toAssetEl.innerHTML = "";

  for (const asset of assets) {
    const opt1 = document.createElement("option");
    opt1.value = asset;
    opt1.textContent = asset;
    fromAssetEl.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = asset;
    opt2.textContent = asset;
    toAssetEl.appendChild(opt2);
  }

  // дефолты
  if (assets.includes("USD")) fromAssetEl.value = "USD";
  if (assets.includes("RUB")) toAssetEl.value = "RUB";
  if (fromAssetEl.value === toAssetEl.value && assets.length > 1) {
    toAssetEl.value = assets[1];
  }
}

function updatePairRateLabel() {
  const from = fromAssetEl.value;
  const to = toAssetEl.value;
  const rFrom = getAssetRate(from);
  const rTo = getAssetRate(to);

  if (!from || !to || typeof rFrom !== "number" || typeof rTo !== "number" || rFrom <= 0) {
    pairRateEl.textContent = "Курс: недоступен";
    return null;
  }

  // rates относительно base (USD). Конвертация from -> to:
  // amount_in_usd = amount / rFrom
  // amount_to = amount_in_usd * rTo
  const rate = rTo / rFrom; // сколько TO за 1 FROM
  pairRateEl.textContent = `Курс: 1 ${from} = ${formatNumber(rate, 8)} ${to}`;
  return rate;
}

function convertNow() {
  setConverterError("");

  const from = fromAssetEl.value;
  const to = toAssetEl.value;
  const amountRaw = amountEl.value.trim().replace(",", ".");
  const amount = Number(amountRaw);

  const rFrom = getAssetRate(from);
  const rTo = getAssetRate(to);

  if (!amountRaw) {
    setConverterError("Введите сумму");
    convertResultEl.textContent = "Результат: —";
    return;
  }

  if (!Number.isFinite(amount)) {
    setConverterError("Сумма должна быть числом");
    convertResultEl.textContent = "Результат: —";
    return;
  }

  if (amount <= 0) {
    setConverterError("Сумма должна быть больше 0");
    convertResultEl.textContent = "Результат: —";
    return;
  }

  if (typeof rFrom !== "number" || typeof rTo !== "number" || rFrom <= 0) {
    setConverterError("Курс для выбранной пары недоступен");
    convertResultEl.textContent = "Результат: —";
    return;
  }

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

swapBtn.addEventListener("click", () => {
  const a = fromAssetEl.value;
  fromAssetEl.value = toAssetEl.value;
  toAssetEl.value = a;
  updatePairRateLabel();
  convertNow();
});

convertBtn.addEventListener("click", convertNow);
fromAssetEl.addEventListener("change", () => {
  updatePairRateLabel();
  convertNow();
});
toAssetEl.addEventListener("change", () => {
  updatePairRateLabel();
  convertNow();
});
amountEl.addEventListener("input", () => {
  updatePairRateLabel();
  convertNow();
});

// ---------- Spreads ----------
const spreadsBodyEl = document.getElementById("spreadsBody");
const refreshSpreadsBtn = document.getElementById("refreshSpreadsBtn");
const symbolFilterEl = document.getElementById("symbolFilter");

let spreadsData = [];

function renderSpreadsTable(rows) {
  if (!rows.length) {
    spreadsBodyEl.innerHTML = `<tr><td colspan="7" class="muted">Нет данных для отображения</td></tr>`;
    return;
  }

  spreadsBodyEl.innerHTML = rows
    .map(
      (r) => `
      <tr>
        <td>${r.symbol}</td>
        <td>${r.low_exchange}</td>
        <td>${formatNumber(Number(r.low_price), 8)}</td>
        <td>${r.high_exchange}</td>
        <td>${formatNumber(Number(r.high_price), 8)}</td>
        <td>${formatNumber(Number(r.spread_abs), 8)}</td>
        <td class="badge-up">${formatNumber(Number(r.spread_pct), 4)}%</td>
      </tr>
    `
    )
    .join("");
}

function applySpreadsFilter() {
  const q = symbolFilterEl.value.trim().toUpperCase();
  if (!q) {
    renderSpreadsTable(spreadsData);
    return;
  }
  const filtered = spreadsData.filter((r) => String(r.symbol || "").toUpperCase().includes(q));
  renderSpreadsTable(filtered);
}

async function loadSpreads() {
  spreadsBodyEl.innerHTML = `<tr><td colspan="7" class="muted">Загрузка...</td></tr>`;
  try {
    const res = await fetch(`${API_BASE}/api/spreads?limit=100`);
    if (!res.ok) throw new Error(`Failed to load spreads: ${res.status}`);
    const data = await res.json();
    spreadsData = Array.isArray(data.records) ? data.records : [];
    applySpreadsFilter();
  } catch (e) {
    spreadsBodyEl.innerHTML = `<tr><td colspan="7" class="muted">Ошибка загрузки спредов</td></tr>`;
    console.error(e);
  }
}

refreshSpreadsBtn.addEventListener("click", loadSpreads);
symbolFilterEl.addEventListener("input", applySpreadsFilter);

// ---------- Init ----------
async function init() {
  try {
    await loadConverterRates();
  } catch (e) {
    console.error(e);
    setConverterError("Не удалось загрузить локальные котировки");
  }

  // Спреды могут появиться не сразу, т.к. поллеру нужно время заполнить PRICES
  await loadSpreads();
  setTimeout(loadSpreads, 2000);
  setInterval(loadSpreads, 5000);
}

init();
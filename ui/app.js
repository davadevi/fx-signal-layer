const currencies = {
  KGS: {
    flag: "🇰🇬", country: "Кыргызстан", unit: "сом", plural: "сомов", rate: 0.99203,
    change: 4.16, precision: 4, series: [0.952405, 0.965849, 0.963774, 0.982894, 0.978853, 0.987756, 0.99203]
  },
  AMD: {
    flag: "🇦🇲", country: "Армения", unit: "драм", plural: "драмов", rate: 0.238162,
    change: 4.48, precision: 4, series: [0.227948, 0.231661, 0.231188, 0.235833, 0.23496, 0.237, 0.238162]
  },
  KZT: {
    flag: "🇰🇿", country: "Казахстан", unit: "тенге", plural: "тенге", rate: 0.187651,
    change: 2.94, precision: 4, series: [0.182297, 0.184422, 0.183829, 0.187317, 0.185163, 0.185854, 0.187651]
  },
  TJS: {
    flag: "🇹🇯", country: "Таджикистан", unit: "сомони", plural: "сомони", rate: 9.38073,
    change: 4.21, precision: 4, series: [9.00214, 9.12922, 9.11265, 9.29284, 9.25493, 9.33084, 9.38073]
  },
  UZS: {
    flag: "🇺🇿", country: "Узбекистан", unit: "сум", plural: "сумов", rate: 0.00733921,
    change: 4.45, precision: 6, series: [0.0070264, 0.00717098, 0.00715557, 0.00726965, 0.00725354, 0.0073076, 0.00733921]
  }
};

const state = {
  screen: "home",
  previousScreen: "home",
  currency: "KGS",
  alerts: new Set(["KGS"]),
  amount: 12000
};

const topLevelScreens = new Set(["home", "payments", "history", "profile"]);
const screenEls = [...document.querySelectorAll("[data-screen]")];
const navButtons = [...document.querySelectorAll(".bottom-nav [data-nav]")];
const app = document.getElementById("app");

function formatNumber(value, maxDigits = 2) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDigits
  }).format(value);
}

function formatRate(value, digits) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);
}

function navigate(screen, remember = true) {
  const next = screenEls.find((el) => el.dataset.screen === screen);
  const current = screenEls.find((el) => el.classList.contains("is-active"));
  if (!next || next === current) return;

  if (remember && current) state.previousScreen = current.dataset.screen;
  current?.classList.add("is-leaving");
  current?.classList.remove("is-active");
  next.classList.add("is-active");
  next.scrollTop = 0;
  requestAnimationFrame(() => next.classList.remove("is-leaving"));
  setTimeout(() => current?.classList.remove("is-leaving"), 280);

  state.screen = screen;
  const navScreen = topLevelScreens.has(screen) ? screen : "";
  navButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.nav === navScreen));
}

function drawPath(series, width, height, padding = 10) {
  const min = Math.min(...series);
  const max = Math.max(...series);
  const spread = max - min || 1;
  return series.map((value, index) => {
    const x = padding + index * ((width - padding * 2) / (series.length - 1));
    const y = padding + (max - value) * ((height - padding * 2) / spread);
    return [x, y];
  });
}

function pathData(points) {
  return points.map(([x, y], index) => `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");
}

function renderCurrencyChips() {
  const holder = document.getElementById("currency-scroller");
  holder.innerHTML = Object.entries(currencies).map(([code, item]) => `
    <button class="currency-chip ${code === state.currency ? "is-selected" : ""}" data-currency="${code}" role="tab" aria-selected="${code === state.currency}">
      <span>${item.flag}</span><b>${code}</b>
    </button>`).join("");
}

function renderCurrency() {
  const code = state.currency;
  const item = currencies[code];
  renderCurrencyChips();

  document.getElementById("rate-pair").textContent = `1 ${code} в рублях`;
  document.getElementById("rate-current").textContent = formatRate(item.rate, item.precision);
  const rateChange = document.getElementById("rate-change");
  rateChange.textContent = `↑ ${formatNumber(item.change, 1)}% за 5 публикаций`;
  rateChange.className = "rate-change is-up";
  document.getElementById("observation-title").textContent = `${capitalize(item.unit)} вырос к рублю`;
  document.getElementById("observation-copy").textContent = `За последние 5 публикаций один ${item.unit} стал стоить на ${formatNumber(item.change, 1)}% больше.`;
  document.getElementById("alert-currency-code").textContent = code;

  const configured = state.alerts.has(code);
  document.getElementById("alert-toggle").checked = configured;
  document.getElementById("alert-button-label").textContent = configured ? "Сигнал настроен" : "Настроить сигнал";

  const points = drawPath(item.series, 340, 154, 9);
  const line = pathData(points);
  document.getElementById("rate-chart-line").setAttribute("d", line);
  document.getElementById("rate-chart-area").setAttribute("d", `${line}L331 174L9 174Z`);
  document.getElementById("rate-chart-points").innerHTML = points.map(([x, y], i) =>
    `<circle class="chart-point" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${i === points.length - 1 ? 4 : 2.5}"/>`
  ).join("");

  updateTransfer();
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function parseAmount(value) {
  const normalized = String(value).replace(/\s/g, "").replace(",", ".").replace(/[^\d.]/g, "");
  return Number(normalized) || 0;
}

function updateTransfer() {
  const item = currencies[state.currency];
  const executionRate = item.rate * 1.012;
  const receive = state.amount / executionRate;
  const receiveDigits = state.currency === "UZS" || receive >= 10000 ? 0 : 2;

  document.getElementById("transfer-flag").textContent = item.flag;
  document.getElementById("transfer-country").textContent = item.country;
  document.getElementById("receive-currency-name").textContent = item.plural;
  document.getElementById("receive-code").textContent = state.currency;
  document.getElementById("receive-amount").textContent = formatNumber(receive, receiveDigits);
  document.getElementById("execution-rate").textContent = `1 ${state.currency} = ${formatRate(executionRate, item.precision)} ₽`;
  document.getElementById("confirm-receive").textContent = formatNumber(receive, receiveDigits);
  document.getElementById("confirm-code").textContent = state.currency;
  document.getElementById("confirm-send").textContent = `${formatNumber(state.amount, 0)} ₽`;
  document.getElementById("success-amount").textContent = `${formatNumber(receive, receiveDigits)} ${state.currency}`;
}

function openSheet(id) {
  const sheet = document.getElementById(id);
  const backdrop = document.getElementById("sheet-backdrop");
  backdrop.hidden = false;
  sheet.hidden = false;
  requestAnimationFrame(() => {
    backdrop.classList.add("is-visible");
    sheet.classList.add("is-visible");
  });
}

function closeSheets() {
  const backdrop = document.getElementById("sheet-backdrop");
  const openSheets = [...document.querySelectorAll(".bottom-sheet.is-visible")];
  backdrop.classList.remove("is-visible");
  openSheets.forEach((sheet) => sheet.classList.remove("is-visible"));
  setTimeout(() => {
    backdrop.hidden = true;
    openSheets.forEach((sheet) => { sheet.hidden = true; });
  }, 280);
}

document.addEventListener("click", (event) => {
  const nav = event.target.closest("[data-nav]");
  if (nav) navigate(nav.dataset.nav);

  const back = event.target.closest("[data-back]");
  if (back) navigate(topLevelScreens.has(state.previousScreen) ? state.previousScreen : "home", false);

  const chip = event.target.closest("[data-currency]");
  if (chip) {
    state.currency = chip.dataset.currency;
    renderCurrency();
  }

  if (event.target.closest("[data-open-alert]")) openSheet("alert-sheet");
  if (event.target.closest("[data-close-sheet]") || event.target.id === "sheet-backdrop") closeSheets();

  const amountButton = event.target.closest("[data-amount]");
  if (amountButton) {
    state.amount = Number(amountButton.dataset.amount);
    document.getElementById("send-amount").value = formatNumber(state.amount, 0);
    updateTransfer();
  }
});

document.querySelector(".fx-hero").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") navigate("rates");
});

document.getElementById("send-amount").addEventListener("input", (event) => {
  state.amount = parseAmount(event.target.value);
  updateTransfer();
});

document.getElementById("send-amount").addEventListener("blur", (event) => {
  event.target.value = formatNumber(state.amount, 0);
});

document.querySelector("[data-save-alert]").addEventListener("click", () => {
  const enabled = document.getElementById("alert-toggle").checked;
  if (enabled) state.alerts.add(state.currency); else state.alerts.delete(state.currency);
  document.getElementById("alert-button-label").textContent = enabled ? "Сигнал настроен" : "Настроить сигнал";
  document.getElementById("profile-alert-status").textContent = state.alerts.size ? `Включены для ${[...state.alerts].join(", ")}` : "Выключены";
  closeSheets();
});

document.getElementById("continue-transfer").addEventListener("click", () => {
  if (state.amount <= 0) {
    document.getElementById("send-amount").focus();
    return;
  }
  openSheet("confirm-sheet");
});

document.getElementById("confirm-transfer").addEventListener("click", () => {
  closeSheets();
  setTimeout(() => {
    const overlay = document.getElementById("success-overlay");
    overlay.hidden = false;
  }, 170);
});

document.getElementById("success-close").addEventListener("click", () => {
  document.getElementById("success-overlay").hidden = true;
  navigate("home", false);
});

function updateClock() {
  document.getElementById("status-time").textContent = new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit", minute: "2-digit"
  }).format(new Date());
}

renderCurrency();
updateClock();
setInterval(updateClock, 30000);

const initialScreen = window.location.hash.replace("#", "");
if (["home", "payments", "history", "profile", "rates", "transfer"].includes(initialScreen)) {
  navigate(initialScreen, false);
}

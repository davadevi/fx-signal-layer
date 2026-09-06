const currencyData = {
  KGS: { flag: "🇰🇬", country: "Кыргызстан", unit: "сом", genitive: "сома", rate: 0.99203, digits: 4, movement: 4.2 },
  AMD: { flag: "🇦🇲", country: "Армения", unit: "драм", genitive: "драма", rate: 0.238162, digits: 4, movement: 4.5 },
  KZT: { flag: "🇰🇿", country: "Казахстан", unit: "тенге", genitive: "тенге", rate: 0.187651, digits: 4, movement: 2.9 },
  TJS: { flag: "🇹🇯", country: "Таджикистан", unit: "сомони", genitive: "сомони", rate: 9.38073, digits: 4, movement: 4.2 },
  UZS: { flag: "🇺🇿", country: "Узбекистан", unit: "сум", genitive: "сума", rate: 0.00733921, digits: 6, movement: 4.5 }
};

const state = {
  currency: "KGS",
  scenario: "favorable",
  rate: currencyData.KGS.rate,
  delta: 2.1,
  events: []
};

const $ = (id) => document.getElementById(id);

function formatNumber(value, digits = 1) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);
}

function parseNumber(value) {
  return Number(String(value).replace(/\s/g, "").replace(",", ".").replace(/[^\d.-]/g, "")) || 0;
}

function selectedCurrency() {
  return currencyData[state.currency];
}

function messageCopy() {
  const item = selectedCurrency();
  const rate = formatNumber(state.rate, item.digits);
  const delta = formatNumber(Math.abs(state.delta), 1);

  if (state.scenario === "movement") {
    return {
      title: `Курс ${state.currency} заметно изменился`,
      body: `За последние 5 публикаций ${item.unit} вырос к рублю на ${delta}%. Посмотрите актуальный курс перевода в приложении.`,
      observationTitle: `${capitalize(item.unit)} вырос к рублю`,
      observationCopy: `За последние 5 публикаций один ${item.unit} стал стоить на ${delta}% больше.`,
      deltaText: `↑ ${delta}% за 5 публикаций`,
      up: true
    };
  }

  if (state.scenario === "neutral") {
    return {
      title: "Пуш не формируется",
      body: `По ${state.currency} нет наблюдения, которое прошло продуктовые фильтры. Пользователь не получает сообщение.`,
      observationTitle: "Нет подтверждённого наблюдения",
      observationCopy: "Система продолжает следить за курсом и сохраняет молчание.",
      deltaText: "Без клиентского сигнала",
      up: false
    };
  }

  return {
    title: `Справочный курс ${state.currency} снизился`,
    body: `Сейчас 1 ${state.currency} = ${rate} ₽ — на ${delta}% ниже среднего за 30 дней. Актуальный курс перевода — в приложении.`,
    observationTitle: "Ниже среднего",
    observationCopy: `Справочный курс ${item.genitive} сейчас на ${delta}% ниже среднего уровня за 30 дней.`,
    deltaText: `↓ ${delta}% к среднему за 30 дней`,
    up: false
  };
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function renderCurrencyTabs() {
  $("currency-tabs").innerHTML = Object.entries(currencyData).map(([code, item]) => `
    <button class="currency-tab ${code === state.currency ? "is-selected" : ""}" data-currency="${code}" role="tab" aria-selected="${code === state.currency}">
      <span>${item.flag}</span><b>${code}</b>
    </button>`).join("");
}

function chartForScenario() {
  if (state.scenario === "movement") {
    return {
      line: "M0 104L50 98L100 103L150 79L200 66L250 51L300 28",
      area: "M0 104L50 98L100 103L150 79L200 66L250 51L300 28L300 130L0 130Z"
    };
  }
  if (state.scenario === "neutral") {
    return {
      line: "M0 67L50 63L100 69L150 65L200 68L250 64L300 66",
      area: "M0 67L50 63L100 69L150 65L200 68L250 64L300 66L300 130L0 130Z"
    };
  }
  return {
    line: "M0 35L50 43L100 39L150 64L200 70L250 91L300 104",
    area: "M0 35L50 43L100 39L150 64L200 70L250 91L300 104L300 130L0 130Z"
  };
}

function render() {
  const item = selectedCurrency();
  const copy = messageCopy();
  renderCurrencyTabs();

  $("preview-title").textContent = copy.title;
  $("preview-body").textContent = copy.body;
  $("copy-length").textContent = `${copy.title.length + copy.body.length} / 180`;
  $("push-title").textContent = copy.title;
  $("push-body").textContent = copy.body;
  $("rate-input").value = formatNumber(state.rate, item.digits);
  $("delta-input").value = formatNumber(Math.abs(state.delta), 1);
  $("delta-label").textContent = state.scenario === "movement" ? "Рост за 5 публикаций" : "Ниже среднего на";
  $("delta-input").disabled = state.scenario === "neutral";
  $("rate-input").disabled = state.scenario === "neutral";

  $("deep-flag").textContent = item.flag;
  $("deep-code").textContent = state.currency;
  $("deep-country").textContent = item.country;
  $("deep-rate").textContent = formatNumber(state.rate, item.digits);
  $("deep-delta").textContent = copy.deltaText;
  $("deep-delta").classList.toggle("is-up", copy.up);
  $("deep-observation-title").textContent = copy.observationTitle;
  $("deep-observation-copy").textContent = copy.observationCopy;

  const chart = chartForScenario();
  $("deep-line").setAttribute("d", chart.line);
  $("deep-area").setAttribute("d", chart.area);
  document.querySelectorAll(".scenario-card").forEach((card) => {
    card.classList.toggle("is-selected", card.querySelector("input").value === state.scenario);
  });
}

function minutesOf(time) {
  const [hours, minutes] = time.split(":").map(Number);
  return hours * 60 + minutes;
}

function outcome() {
  if (state.scenario === "neutral") {
    return { type: "blocked", icon: "×", title: "Система промолчала", copy: "Нет квалифицирующего наблюдения — коммуникация не создаётся." };
  }
  if (Number($("sent-count").value) >= 2) {
    return { type: "blocked", icon: "×", title: "Пуш подавлен лимитом", copy: "Клиент уже получил два уведомления за последние 7 дней." };
  }
  const now = minutesOf($("time-input").value);
  const quiet = $("quiet-hours").checked && (now >= 22 * 60 || now < 9 * 60);
  if (quiet) {
    return { type: "queued", icon: "◷", title: "Отложено до 09:00", copy: "Событие попало в тихие часы. Пуш не показывается на экране сейчас." };
  }
  return { type: "sent", icon: "✓", title: "Пуш доставлен", copy: "Лимиты соблюдены, уведомление появилось на экране телефона." };
}

function renderPhoneOutcome(result) {
  const card = $("push-card");
  const waiting = $("waiting-state");
  $("deeplink-screen").hidden = true;
  $("lock-screen").hidden = false;
  waiting.className = "waiting-state";

  if (result.type === "sent") {
    waiting.hidden = true;
    card.hidden = false;
    card.style.animation = "none";
    requestAnimationFrame(() => { card.style.animation = ""; });
    return;
  }

  card.hidden = true;
  waiting.hidden = false;
  waiting.classList.add(result.type === "queued" ? "is-queued" : "is-error");
  waiting.innerHTML = `<span>${result.icon}</span><p>${result.title}<br><small>${result.copy}</small></p>`;
}

function renderResult(result) {
  const holder = $("delivery-result");
  holder.hidden = false;
  holder.className = `delivery-result is-${result.type}`;
  $("result-icon").textContent = result.icon;
  $("result-title").textContent = result.title;
  $("result-copy").textContent = result.copy;
}

function addEvent(result) {
  const copy = messageCopy();
  const event = {
    time: $("time-input").value,
    code: state.currency,
    title: copy.title,
    type: result.type,
    label: result.type === "sent" ? "доставлен" : result.type === "queued" ? "отложен" : "подавлен"
  };
  state.events.unshift(event);
  $("event-count").textContent = `${state.events.length} ${state.events.length === 1 ? "событие" : state.events.length < 5 ? "события" : "событий"}`;
  $("event-list").innerHTML = state.events.map((item) => `
    <article class="event-item">
      <time>${item.time}</time>
      <div><strong>${item.code} · ${item.title}</strong><small>Проверка коммуникационной политики</small></div>
      <span class="event-state ${item.type}">${item.label}</span>
    </article>`).join("");
}

function runSimulation() {
  const time = $("time-input").value;
  $("phone-status-time").textContent = time;
  $("app-status-time").textContent = time;
  $("lock-time").textContent = time;
  const result = outcome();
  renderResult(result);
  renderPhoneOutcome(result);
  addEvent(result);
}

function resetSimulation() {
  state.events = [];
  $("event-count").textContent = "0 событий";
  $("event-list").innerHTML = '<p class="empty-log">Здесь появятся результаты запусков</p>';
  $("delivery-result").hidden = true;
  $("push-card").hidden = true;
  $("deeplink-screen").hidden = true;
  $("lock-screen").hidden = false;
  const waiting = $("waiting-state");
  waiting.hidden = false;
  waiting.className = "waiting-state";
  waiting.innerHTML = "<span>↑</span><p>Настройте сценарий<br>и запустите симуляцию</p>";
}

document.addEventListener("click", (event) => {
  const currency = event.target.closest("[data-currency]");
  if (currency) {
    state.currency = currency.dataset.currency;
    const item = selectedCurrency();
    state.rate = item.rate;
    state.delta = state.scenario === "movement" ? item.movement : 2.1;
    render();
  }
});

document.querySelectorAll('input[name="scenario"]').forEach((input) => {
  input.addEventListener("change", () => {
    state.scenario = input.value;
    state.delta = state.scenario === "movement" ? selectedCurrency().movement : 2.1;
    render();
  });
});

$("rate-input").addEventListener("input", (event) => {
  state.rate = parseNumber(event.target.value);
  renderCopyOnly();
});

$("delta-input").addEventListener("input", (event) => {
  state.delta = parseNumber(event.target.value);
  renderCopyOnly();
});

function renderCopyOnly() {
  const copy = messageCopy();
  $("preview-title").textContent = copy.title;
  $("preview-body").textContent = copy.body;
  $("push-title").textContent = copy.title;
  $("push-body").textContent = copy.body;
  $("deep-rate").textContent = formatNumber(state.rate, selectedCurrency().digits);
  $("deep-delta").textContent = copy.deltaText;
  $("deep-observation-copy").textContent = copy.observationCopy;
  $("copy-length").textContent = `${copy.title.length + copy.body.length} / 180`;
}

$("run-simulation").addEventListener("click", runSimulation);
$("reset-simulation").addEventListener("click", resetSimulation);
$("push-card").addEventListener("click", () => {
  $("lock-screen").hidden = true;
  $("deeplink-screen").hidden = false;
});
$("back-to-lock").addEventListener("click", () => {
  $("deeplink-screen").hidden = true;
  $("lock-screen").hidden = false;
});

render();

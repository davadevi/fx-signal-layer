const currencyMeta = {
  KGS: { flag: "🇰🇬", country: "Кыргызстан", unit: "сом", genitive: "сома", digits: 4 },
  AMD: { flag: "🇦🇲", country: "Армения", unit: "драм", genitive: "драма", digits: 4 },
  KZT: { flag: "🇰🇿", country: "Казахстан", unit: "тенге", genitive: "тенге", digits: 4 },
  TJS: { flag: "🇹🇯", country: "Таджикистан", unit: "сомони", genitive: "сомони", digits: 4 },
  UZS: { flag: "🇺🇿", country: "Узбекистан", unit: "сум", genitive: "сума", digits: 6 }
};

const state = {
  data: null,
  currency: "KGS",
  points: [],
  periodSignals: [],
  index: 0,
  playing: false,
  timer: null
};

const $ = (id) => document.getElementById(id);
const canvas = $("timeline-chart");
const context = canvas.getContext("2d");
const dayMs = 24 * 60 * 60 * 1000;

function formatRate(value, digits = currencyMeta[state.currency].digits) {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);
}

function parseDate(date) {
  return new Date(`${date}T12:00:00`);
}

function formatDate(date, style = "long") {
  const value = parseDate(date);
  if (style === "short") {
    return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(value).replace(".", "");
  }
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(value);
}

function formatPhoneDate(date) {
  const value = parseDate(date);
  return new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" }).format(value);
}

function computeSignals(series) {
  const signals = [];
  let lastSent = null;
  for (let index = 29; index < series.length; index += 1) {
    const window = series.slice(index - 29, index + 1);
    const mean = window.reduce((sum, item) => sum + item[1], 0) / window.length;
    const deviation = (series[index][1] / mean - 1) * 100;
    const date = parseDate(series[index][0]);
    const cooldownPassed = !lastSent || (date - lastSent) / dayMs >= 7;
    if (deviation <= -1 && cooldownPassed) {
      signals.push({ date: series[index][0], rate: series[index][1], deviation, rollingMean: mean });
      lastSent = date;
    }
  }
  return signals;
}

function renderCurrencyPills() {
  $("timeline-currencies").innerHTML = Object.entries(currencyMeta).map(([code, item]) => `
    <button class="currency-pill ${code === state.currency ? "is-selected" : ""}" data-currency="${code}" role="tab" aria-selected="${code === state.currency}">
      <span>${item.flag}</span><b>${code}</b>
    </button>`).join("");
}

function applyPeriod() {
  if (!state.data) return;
  let start = $("start-date").value;
  let end = $("end-date").value;
  if (start > end) {
    [start, end] = [end, start];
    $("start-date").value = start;
    $("end-date").value = end;
  }

  const fullSeries = state.data.series[state.currency];
  state.points = fullSeries.filter(([date]) => date >= start && date <= end);
  const signals = computeSignals(fullSeries);
  const indexByDate = new Map(state.points.map((point, index) => [point[0], index]));
  state.periodSignals = signals
    .filter((signal) => indexByDate.has(signal.date))
    .map((signal) => ({ ...signal, index: indexByDate.get(signal.date) }));
  state.index = 0;
  stopPlayback();
  renderCurrencyPills();
  renderStaticLabels();
  updateFrame(false);
}

function renderStaticLabels() {
  const meta = currencyMeta[state.currency];
  $("chart-code").textContent = state.currency;
  $("phone-currency").textContent = `${state.currency} · ${meta.country}`;
  $("timeline-scrubber").max = Math.max(0, state.points.length - 1);
  $("timeline-scrubber").value = 0;
  if (!state.points.length) {
    $("current-rate").textContent = "—";
    $("current-date").textContent = "В выбранном периоде нет наблюдений";
    $("point-progress").textContent = "0 / 0 дат";
  }
}

function seenSignals() {
  return state.periodSignals.filter((signal) => signal.index <= state.index);
}

function updateFrame(animateNotification = true) {
  if (!state.points.length) {
    drawEmptyChart();
    renderEvents([]);
    renderPhoneNotifications([], false);
    return;
  }

  const [date, rate] = state.points[state.index];
  const progress = state.points.length <= 1 ? 1 : state.index / (state.points.length - 1);
  const change = (rate / state.points[0][1] - 1) * 100;
  const signals = seenSignals();
  const isNewSignal = animateNotification && signals.some((signal) => signal.index === state.index);

  $("current-rate").textContent = formatRate(rate);
  $("current-date").textContent = formatDate(date);
  $("period-change").textContent = `${change >= 0 ? "+" : ""}${formatRate(change, 2)}%`;
  $("period-change").className = change >= 0 ? "is-negative" : "is-positive";
  $("push-count").textContent = signals.length;
  $("timeline-scrubber").value = state.index;
  $("progress-label").textContent = `${Math.round(progress * 100)}%`;
  $("point-progress").textContent = `${state.index + 1} / ${state.points.length} дат`;
  $("phone-weekday").textContent = formatPhoneDate(date);
  $("phone-day-counter").textContent = `День ${Math.round((parseDate(date) - parseDate(state.points[0][0])) / dayMs) + 1}`;
  $("phone-progress-bar").style.width = `${progress * 100}%`;
  $("phone-caption-status").textContent = state.playing ? `Воспроизведение · ${formatDate(date, "short")}` : `Пауза · ${formatDate(date, "short")}`;

  drawChart();
  renderEvents(signals);
  renderPhoneNotifications(signals, isNewSignal);
}

function chartGeometry() {
  const bounds = canvas.getBoundingClientRect();
  const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
  const width = Math.max(300, bounds.width);
  const height = Math.max(240, bounds.height);
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { width, height, left: 58, right: 14, top: 26, bottom: 34 };
}

function drawEmptyChart() {
  const g = chartGeometry();
  context.clearRect(0, 0, g.width, g.height);
  context.fillStyle = "#8a8a85";
  context.font = "11px Inter, Arial";
  context.textAlign = "center";
  context.fillText("Нет данных для выбранного периода", g.width / 2, g.height / 2);
}

function drawChart() {
  const g = chartGeometry();
  context.clearRect(0, 0, g.width, g.height);
  const values = state.points.map((point) => point[1]);
  let min = Math.min(...values);
  let max = Math.max(...values);
  const baseSpread = max - min || Math.abs(max) * .02 || 1;
  min -= baseSpread * .10;
  max += baseSpread * .10;
  const plotWidth = g.width - g.left - g.right;
  const plotHeight = g.height - g.top - g.bottom;
  const xAt = (index) => g.left + (state.points.length <= 1 ? 0 : index / (state.points.length - 1)) * plotWidth;
  const yAt = (value) => g.top + (max - value) / (max - min) * plotHeight;

  context.lineWidth = 1;
  context.font = "9px Inter, Arial";
  context.textAlign = "right";
  context.textBaseline = "middle";
  for (let tick = 0; tick < 4; tick += 1) {
    const ratio = tick / 3;
    const y = g.top + ratio * plotHeight;
    const value = max - ratio * (max - min);
    context.beginPath();
    context.setLineDash([3, 5]);
    context.strokeStyle = "#e8e8e5";
    context.moveTo(g.left, y);
    context.lineTo(g.width - g.right, y);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = "#999994";
    context.fillText(formatRate(value), g.left - 9, y);
  }

  const dateLabels = [0, Math.floor((state.points.length - 1) / 2), state.points.length - 1];
  context.textBaseline = "bottom";
  dateLabels.forEach((index, position) => {
    const alignments = ["left", "center", "right"];
    context.textAlign = alignments[position];
    context.fillStyle = "#999994";
    context.fillText(formatDate(state.points[index][0], "short"), xAt(index), g.height - 2);
  });

  const visible = state.points.slice(0, state.index + 1);
  if (visible.length) {
    const gradient = context.createLinearGradient(0, g.top, 0, g.top + plotHeight);
    gradient.addColorStop(0, "rgba(239,49,36,.18)");
    gradient.addColorStop(1, "rgba(239,49,36,0)");
    context.beginPath();
    visible.forEach((point, index) => {
      const x = xAt(index);
      const y = yAt(point[1]);
      if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    context.lineTo(xAt(state.index), g.top + plotHeight);
    context.lineTo(xAt(0), g.top + plotHeight);
    context.closePath();
    context.fillStyle = gradient;
    context.fill();

    context.beginPath();
    visible.forEach((point, index) => {
      const x = xAt(index);
      const y = yAt(point[1]);
      if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    context.lineWidth = 2.2;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.strokeStyle = "#171717";
    context.stroke();
  }

  seenSignals().forEach((signal, markerIndex) => {
    const x = xAt(signal.index);
    const y = yAt(signal.rate);
    context.beginPath();
    context.setLineDash([4, 4]);
    context.lineWidth = 1;
    context.strokeStyle = "rgba(239,49,36,.48)";
    context.moveTo(x, g.top + 18);
    context.lineTo(x, g.top + plotHeight);
    context.stroke();
    context.setLineDash([]);

    context.beginPath();
    context.arc(x, y, 5, 0, Math.PI * 2);
    context.fillStyle = "white";
    context.fill();
    context.lineWidth = 2.5;
    context.strokeStyle = "#ef3124";
    context.stroke();

    const labelY = g.top + (markerIndex % 2) * 18;
    context.beginPath();
    context.arc(x, labelY + 6, 7, 0, Math.PI * 2);
    context.fillStyle = "#ef3124";
    context.fill();
    context.fillStyle = "white";
    context.font = "bold 7px Inter, Arial";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText("!", x, labelY + 6.5);
  });

  const current = state.points[state.index];
  const currentX = xAt(state.index);
  const currentY = yAt(current[1]);
  context.beginPath();
  context.arc(currentX, currentY, 4, 0, Math.PI * 2);
  context.fillStyle = "#ef3124";
  context.fill();
  context.beginPath();
  context.arc(currentX, currentY, 8, 0, Math.PI * 2);
  context.strokeStyle = "rgba(239,49,36,.22)";
  context.lineWidth = 4;
  context.stroke();
}

function notificationCopy(signal) {
  const meta = currencyMeta[state.currency];
  const deviation = formatRate(Math.abs(signal.deviation), 1);
  return {
    title: `Справочный курс ${state.currency} ниже среднего`,
    body: `1 ${state.currency} = ${formatRate(signal.rate)} ₽ — на ${deviation}% ниже среднего за 30 публикаций. Актуальный курс перевода — в приложении.`,
    fact: `${capitalize(meta.unit)} на ${deviation}% ниже среднего`
  };
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function renderEvents(signals) {
  $("events-badge").textContent = `${signals.length} ${signals.length === 1 ? "событие" : signals.length < 5 ? "события" : "событий"}`;
  if (!signals.length) {
    $("events-table").innerHTML = '<div class="events-empty"><span>↗</span><p>Запустите воспроизведение — здесь появятся моменты отправки.</p></div>';
    return;
  }
  $("events-table").innerHTML = [...signals].reverse().map((signal) => {
    const copy = notificationCopy(signal);
    return `<article class="event-row"><time>${formatDate(signal.date, "short")}</time><span class="event-rate">${formatRate(signal.rate)} ₽</span><span>${copy.fact}</span><b>Отправлен</b></article>`;
  }).join("");
}

function renderPhoneNotifications(signals, animateLatest) {
  const holder = $("phone-notifications");
  $("phone-event-total").textContent = `${signals.length} ${signals.length === 1 ? "уведомление" : signals.length < 5 ? "уведомления" : "уведомлений"}`;
  if (!signals.length) {
    holder.innerHTML = '<div class="phone-empty" id="phone-empty"><span>🔔</span><p>Уведомления появятся<br>во время воспроизведения</p></div>';
    return;
  }

  holder.innerHTML = "";
  [...signals].reverse().slice(0, 2).forEach((signal, index) => {
    const copy = notificationCopy(signal);
    const node = $("phone-notification-template").content.firstElementChild.cloneNode(true);
    node.querySelector(".push-title").textContent = copy.title;
    node.querySelector(".push-copy").textContent = copy.body;
    node.querySelector("time").textContent = index === 0 ? "сейчас" : formatDate(signal.date, "short");
    if (!animateLatest || index > 0) node.style.animation = "none";
    holder.appendChild(node);
  });
}

function stopPlayback() {
  state.playing = false;
  clearTimeout(state.timer);
  state.timer = null;
  $("play-icon").textContent = "▶";
  $("play-label").textContent = state.index >= Math.max(0, state.points.length - 1) ? "Сначала" : "Запустить";
}

function playbackTick() {
  if (!state.playing) return;
  if (state.index >= state.points.length - 1) {
    stopPlayback();
    $("phone-caption-status").textContent = "Период завершён";
    return;
  }
  state.index += 1;
  updateFrame(true);
  state.timer = setTimeout(playbackTick, Number($("playback-speed").value));
}

function togglePlayback() {
  if (!state.points.length) return;
  if (state.playing) {
    stopPlayback();
    updateFrame(false);
    return;
  }
  if (state.index >= state.points.length - 1) state.index = 0;
  state.playing = true;
  $("play-icon").textContent = "Ⅱ";
  $("play-label").textContent = "Пауза";
  updateFrame(false);
  state.timer = setTimeout(playbackTick, Number($("playback-speed").value));
}

function resetPlayback() {
  stopPlayback();
  state.index = 0;
  updateFrame(false);
}

function stepPlayback() {
  stopPlayback();
  if (state.index < state.points.length - 1) state.index += 1;
  updateFrame(true);
}

async function loadData() {
  try {
    const response = await fetch("timeline-data.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    const min = state.data.start_date;
    const max = state.data.end_date;
    $("start-date").min = min;
    $("start-date").max = max;
    $("end-date").min = min;
    $("end-date").max = max;
    $("chart-loading").hidden = true;
    applyPeriod();
  } catch (error) {
    $("chart-loading").innerHTML = `<p>Не удалось загрузить timeline-data.json<br><small>${error.message}</small></p>`;
  }
}

document.addEventListener("click", (event) => {
  const currency = event.target.closest("[data-currency]");
  if (currency) {
    state.currency = currency.dataset.currency;
    applyPeriod();
  }
});

$("start-date").addEventListener("change", applyPeriod);
$("end-date").addEventListener("change", applyPeriod);
$("signal-example").addEventListener("click", () => {
  $("start-date").value = "2026-04-01";
  $("end-date").value = "2026-06-20";
  applyPeriod();
});
$("play-button").addEventListener("click", togglePlayback);
$("reset-playback").addEventListener("click", resetPlayback);
$("step-playback").addEventListener("click", stepPlayback);
$("timeline-scrubber").addEventListener("input", (event) => {
  stopPlayback();
  state.index = Number(event.target.value);
  updateFrame(false);
});
window.addEventListener("resize", () => requestAnimationFrame(() => state.points.length ? drawChart() : drawEmptyChart()));

renderCurrencyPills();
loadData();

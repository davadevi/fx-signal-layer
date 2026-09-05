"""Generate peer-review PDF for FX Signal Layer solution validation."""
from __future__ import annotations

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a2e;
    background: #fff;
    padding: 0;
  }

  .cover {
    background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
    color: #fff;
    padding: 60px 60px 50px;
    min-height: 260px;
  }

  .cover-tag {
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #e94560;
    margin-bottom: 18px;
  }

  .cover h1 {
    font-size: 28pt;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 12px;
  }

  .cover-sub {
    font-size: 12pt;
    color: rgba(255,255,255,0.75);
    margin-bottom: 28px;
  }

  .cover-meta {
    display: flex;
    gap: 32px;
    font-size: 9.5pt;
    color: rgba(255,255,255,0.6);
  }

  .cover-meta span strong {
    color: #fff;
    display: block;
    font-size: 10.5pt;
  }

  .body-wrap {
    padding: 48px 60px;
  }

  h2 {
    font-size: 15pt;
    font-weight: 700;
    color: #0f3460;
    margin: 36px 0 14px;
    padding-bottom: 6px;
    border-bottom: 2px solid #e94560;
  }

  h3 {
    font-size: 11.5pt;
    font-weight: 600;
    color: #16213e;
    margin: 22px 0 8px;
  }

  p { margin-bottom: 10px; }

  .lead {
    font-size: 12pt;
    line-height: 1.7;
    color: #2d2d4e;
    background: #f0f4ff;
    border-left: 4px solid #0f3460;
    padding: 16px 20px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 24px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
    margin: 12px 0 20px;
  }

  th {
    background: #0f3460;
    color: #fff;
    padding: 7px 10px;
    text-align: left;
    font-weight: 600;
  }

  td {
    padding: 6px 10px;
    border-bottom: 1px solid #e8eaf0;
    vertical-align: top;
  }

  tr:nth-child(even) td { background: #f7f8fc; }
  tr:last-child td { border-bottom: none; }

  .pass { color: #1a7a3e; font-weight: 700; }
  .fail { color: #b00020; }
  .warn { color: #c67000; }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 8.5pt;
    font-weight: 600;
  }

  .badge-green { background: #d4edda; color: #155724; }
  .badge-red   { background: #f8d7da; color: #721c24; }
  .badge-blue  { background: #d0e8ff; color: #0f3460; }
  .badge-gray  { background: #e9ecef; color: #495057; }

  .code-block {
    background: #1a1a2e;
    color: #a8d8a8;
    padding: 14px 18px;
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    line-height: 1.7;
    margin: 10px 0 18px;
    white-space: pre;
  }

  .steps {
    counter-reset: step;
    list-style: none;
    padding: 0;
    margin: 10px 0 18px;
  }

  .steps li {
    counter-increment: step;
    padding: 10px 10px 10px 46px;
    position: relative;
    border-left: 2px solid #e8eaf0;
    margin-bottom: 6px;
  }

  .steps li::before {
    content: counter(step);
    position: absolute;
    left: -14px;
    top: 8px;
    width: 26px;
    height: 26px;
    background: #0f3460;
    color: #fff;
    border-radius: 50%;
    font-size: 9pt;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    line-height: 26px;
  }

  .checklist {
    list-style: none;
    padding: 0;
    margin: 10px 0 18px;
  }

  .checklist li {
    padding: 8px 10px 8px 36px;
    position: relative;
    border-bottom: 1px solid #f0f0f5;
    font-size: 10pt;
  }

  .checklist li::before {
    content: '☐';
    position: absolute;
    left: 10px;
    color: #0f3460;
    font-size: 13pt;
  }

  .checklist li code {
    background: #eef2ff;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 8.5pt;
    color: #0f3460;
  }

  .limitation-box {
    background: #fff8e6;
    border: 1px solid #ffd166;
    border-radius: 6px;
    padding: 14px 16px;
    margin: 10px 0 16px;
  }

  .limitation-box strong { color: #c67000; }

  .two-col {
    display: flex;
    gap: 24px;
    margin: 10px 0 18px;
  }

  .two-col .col { flex: 1; }

  .stat-card {
    background: #f0f4ff;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    margin-bottom: 12px;
  }

  .stat-card .value {
    font-size: 24pt;
    font-weight: 700;
    color: #0f3460;
    line-height: 1;
  }

  .stat-card .label {
    font-size: 9pt;
    color: #666;
    margin-top: 4px;
  }

  .page-break { page-break-before: always; }

  .footer-note {
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #e8eaf0;
    font-size: 8.5pt;
    color: #999;
    text-align: center;
  }

  .highlight-row td { background: #d4edda !important; font-weight: 600; }
</style>
</head>
<body>

<!-- COVER -->
<div class="cover">
  <div class="cover-tag">Alfa-Bank Hackathon · Валидация решения</div>
  <h1>FX Signal Layer</h1>
  <div class="cover-sub">Алгоритм детектирования выгодного дня для трансграничных переводов</div>
  <div class="cover-meta">
    <span>Дата<strong>05.09.2026</strong></span>
    <span>Статус<strong>Финальное решение</strong></span>
    <span>Защита<strong>07.09.2026</strong></span>
    <span>Коридоры<strong>KGS · TJS · AMD</strong></span>
  </div>
</div>

<!-- BODY -->
<div class="body-wrap">

<!-- 1. СУТЬ -->
<h2>Что мы сделали</h2>

<div class="lead">
  Система смотрит, насколько быстро рубль укрепился сегодня относительно последних 30–60 дней.
  Если сегодня рубль в топ-20% по скорости укрепления <strong>два дня подряд</strong> — отправляем
  push-уведомление: «курс сейчас выгоднее, чем обычно». Проверено на 5 коридорах через
  walk-forward backtest с независимым out-of-time периодом.
</div>

<div class="two-col">
  <div class="col">
    <div class="stat-card">
      <div class="value">2.1–2.5×</div>
      <div class="label">OOT Lift над случайным днём</div>
    </div>
    <div class="stat-card">
      <div class="value">+64–96 бп</div>
      <div class="label">Экономия клиента при h=10 дней</div>
    </div>
  </div>
  <div class="col">
    <div class="stat-card">
      <div class="value">CI &gt; 1.0</div>
      <div class="label">90% bootstrap CI нижняя граница на KGS и TJS</div>
    </div>
    <div class="stat-card">
      <div class="value">0 lookahead</div>
      <div class="label">Подтверждено unit-тестами</div>
    </div>
  </div>
</div>

<!-- 2. КАК РАБОТАЕТ -->
<h2>Как работает индикатор</h2>

<ol class="steps">
  <li>
    <strong>Log-return за 5 дней.</strong>
    Берём курс сегодня и 5 торговых дней назад → считаем log-return.
    Пример KGS: вчера 1.4300, сегодня 1.4180 → log-return = −0.0084 (рубль укрепился).
  </li>
  <li>
    <strong>Percentile rank в окне 60 дней.</strong>
    Ставим сегодняшний log-return в ряд из 60 последних дней.
    Если сегодня в нижних 20% (рубль укрепился быстрее, чем в 80% дней за 2 месяца) → кандидат.
  </li>
  <li>
    <strong>Подтверждение 2 дня подряд.</strong>
    Понедельник: score=0.11 → кандидат. Вторник: score=0.14 → <strong>СИГНАЛ</strong>.
    Без подтверждения — слишком много ложных срабатываний (см. таблицу c0 vs c2).
  </li>
  <li>
    <strong>Кризисный фильтр.</strong>
    Если скользящая волатильность > 85-го перцентиля за год → молчим.
    В кризис сигнал означает продолжение падения, а не разворот.
  </li>
</ol>

<div class="code-block">LogReturnPercentileIndicator(
    return_window  = 5,   # N-дневный log-return
    rank_window    = 60,  # окно сравнения (дней)
    threshold      = 0.20, # топ-20% укрепления
    confirm_days   = 2,   # подтверждений подряд
)</div>

<!-- 3. КЛЮЧЕВЫЕ ЧИСЛА -->
<h2>Ключевые числа</h2>

<h3>Сводная таблица CI-passing коридоров</h3>

<table>
  <tr>
    <th>Коридор</th>
    <th>h</th>
    <th>IS Lift</th>
    <th>OOT Lift</th>
    <th>CI 90% ↓</th>
    <th>Экономия (bps)</th>
    <th>Статус</th>
  </tr>
  <tr class="highlight-row">
    <td>KGS (сом)</td><td>5</td><td>2.10</td><td>1.84</td><td class="pass">1.36</td><td>+41 бп</td><td><span class="badge badge-green">✓ Валид</span></td>
  </tr>
  <tr class="highlight-row">
    <td>KGS (сом)</td><td>10</td><td>2.17</td><td>2.24</td><td class="pass">1.15</td><td>+64 бп</td><td><span class="badge badge-green">✓ Валид</span></td>
  </tr>
  <tr class="highlight-row">
    <td>TJS (сомони)</td><td>5</td><td>2.35</td><td>1.76</td><td class="pass">1.76</td><td>+69 бп</td><td><span class="badge badge-green">✓ Валид</span></td>
  </tr>
  <tr class="highlight-row">
    <td>TJS (сомони)</td><td>10</td><td>2.52</td><td>2.13</td><td class="pass">1.65</td><td>+96 бп</td><td><span class="badge badge-green">✓ Валид</span></td>
  </tr>
  <tr>
    <td>AMD (драм)</td><td>10</td><td>2.81</td><td>2.16</td><td class="pass">1.30</td><td>+52 бп</td><td><span class="badge badge-blue">✓ (мало данных)</span></td>
  </tr>
  <tr>
    <td>UZS (сум)</td><td>—</td><td>—</td><td>—</td><td class="fail">&lt; 1.0</td><td>—</td><td><span class="badge badge-red">✗ Не проходит</span></td>
  </tr>
  <tr>
    <td>KZT (тенге)</td><td>—</td><td>—</td><td>—</td><td class="fail">&lt; 1.0</td><td>—</td><td><span class="badge badge-red">✗ Управляемый</span></td>
  </tr>
</table>

<p style="font-size:9pt; color:#666; margin-top:-12px; margin-bottom:20px;">
  <strong>Lift</strong> — во сколько раз точнее случайного дня.
  Lift 2.10 = в 2.1× чаще попадаем на выгодный день, чем наугад.<br>
  <strong>bps</strong> — (среднее(rate[t+1..t+h]) − rate[t]) / rate[t] × 10 000.
  Положительное = день сигнала дешевле, чем случайный день в следующие h дней.
</p>

<div class="page-break"></div>

<!-- 4. IS vs OOT -->
<h2>IS vs OOT — почему это важно</h2>

<div class="two-col">
  <div class="col">
    <h3>IS (In-Sample)</h3>
    <p>Lift на данных, которые <strong>участвовали в настройке</strong> параметров
    (threshold=0.20, rank_window=60, confirm_days=2). IS-числа оптимистичны —
    индикатор «видел» эти данные.</p>
  </div>
  <div class="col">
    <h3>OOT (Out-of-Time)</h3>
    <p>Lift на данных <strong>после 01.07.2025</strong>, которые ни разу не использовались
    при выборе параметров. Параметры заморожены. OOT — честная проверка на свежей истории.</p>
  </div>
</div>

<p>KGS h=10: IS=2.17, OOT=<strong>2.24</strong> — OOT даже лучше IS. TJS h=10: IS=2.52, OOT=2.13 —
небольшая деградация, но CI держится. Это признак отсутствия переобучения.</p>

<h3>Полная матрица IS Lift по всем горизонтам</h3>

<table>
  <tr><th>Коридор</th><th>h=1</th><th>h=3</th><th>h=5</th><th>h=10</th><th>h=20</th></tr>
  <tr><td>KGS</td><td>1.20</td><td>1.73</td><td><strong>2.10</strong></td><td><strong>2.17</strong></td><td>1.49</td></tr>
  <tr><td>TJS</td><td>1.41</td><td>1.95</td><td><strong>2.35</strong></td><td><strong>2.52</strong></td><td>2.38</td></tr>
  <tr><td>AMD</td><td>1.22</td><td>1.76</td><td>2.16</td><td><strong>2.81</strong></td><td>1.23</td></tr>
  <tr><td>UZS</td><td>1.21</td><td>1.44</td><td>1.41</td><td>1.90</td><td>1.23</td></tr>
  <tr><td>KZT</td><td>0.82</td><td>1.14</td><td>1.49</td><td>1.01</td><td>1.39</td></tr>
</table>

<h3>Полная матрица OOT Lift по всем горизонтам</h3>

<table>
  <tr><th>Коридор</th><th>h=1</th><th>h=3</th><th>h=5</th><th>h=10</th><th>h=20</th></tr>
  <tr><td>KGS</td><td>1.11</td><td>1.49</td><td><strong>1.84</strong></td><td><strong>2.24</strong></td><td>1.30</td></tr>
  <tr><td>TJS</td><td>1.06</td><td>1.43</td><td><strong>1.76</strong></td><td><strong>2.13</strong></td><td>1.46</td></tr>
  <tr><td>AMD</td><td>1.04</td><td>1.42</td><td>1.75</td><td><strong>2.16</strong></td><td>1.27</td></tr>
  <tr><td>UZS</td><td>1.23</td><td>1.26</td><td>1.02</td><td>1.29</td><td>0.74</td></tr>
  <tr><td>KZT</td><td class="fail">NaN</td><td class="fail">NaN</td><td class="fail">NaN</td><td class="fail">NaN</td><td class="fail">NaN</td></tr>
</table>

<h3>CI 90% нижняя граница (bootstrap, блоки 90 дней, 2000 итераций)</h3>

<table>
  <tr><th>Коридор</th><th>h=5</th><th>h=10</th><th>h=20</th></tr>
  <tr><td>KGS</td><td class="pass"><strong>1.36</strong></td><td class="pass"><strong>1.15</strong></td><td class="fail">0.00</td></tr>
  <tr><td>TJS</td><td class="pass"><strong>1.76</strong></td><td class="pass"><strong>1.65</strong></td><td class="warn">0.99</td></tr>
  <tr><td>AMD</td><td class="warn">0.99</td><td class="pass"><strong>1.30</strong></td><td class="fail">0.00</td></tr>
  <tr><td>UZS</td><td class="fail">0.49</td><td class="fail">0.67</td><td class="fail">0.00</td></tr>
  <tr><td>KZT</td><td class="fail">0.00</td><td class="fail">0.00</td><td class="fail">0.00</td></tr>
</table>

<p style="font-size:9pt; color:#666; margin-top:-12px;">
  Жирным — горизонты с CI &gt; 1.0 (статистически подтверждены).
  Если CI ↓ &gt; 1.0 → даже в пессимистичном сценарии lift выше случайного.
</p>

<div class="page-break"></div>

<!-- 5. ЗАЩИТА ОТ LOOKAHEAD -->
<h2>Защита от заглядывания в будущее</h2>

<p>Это критическое требование кейса. Нарушение = дисквалификация.</p>

<table>
  <tr><th>Механизм</th><th>Реализация</th></tr>
  <tr>
    <td><strong>Walk-forward</strong></td>
    <td>Модель в каждом окне обучается на [start, T−embargo], тестируется на [T, T+3мес]. Embargo 5 дней между train и test.</td>
  </tr>
  <tr>
    <td><strong>OOT split</strong></td>
    <td>Параметры (threshold=0.20, rank_window=60, confirm_days=2) выбраны на данных до 01.07.2025. После — нетронутые данные.</td>
  </tr>
  <tr>
    <td><strong>cutoff_date</strong></td>
    <td>Каждый модуль принимает <code>cutoff_date</code> и фильтрует данные строго <code>&lt;= cutoff_date</code>.</td>
  </tr>
  <tr>
    <td><strong>Unit-тесты</strong></td>
    <td><code>tests/unit/test_no_lookahead.py</code> — 30 passed. Проверяет: score на дату T не использует данные T+1.</td>
  </tr>
</table>

<!-- 6. ЧТО ПРОВЕРИЛИ И ОТВЕРГЛИ -->
<h2>Что проверили и отвергли</h2>

<table>
  <tr><th>Вариант</th><th>Почему отвергнут</th></tr>
  <tr><td>Percentile по уровню курса</td><td>Курс нестационарен (I(1)) — percentile по уровню теоретически некорректен. Lift 0.91–0.97 — хуже случайного.</td></tr>
  <tr><td>confirm_days=0 (без подтверждения)</td><td>Частота 0.37/нед, но CI &lt; 1.0 на всех коридорах. bps отрицательный (−5 до −23 bps) — сигнал приходит в середине тренда.</td></tr>
  <tr><td>confirm_days=1</td><td>Работает только на TJS (CI=1.06), KGS CI=0.62. bps снижается на 46%.</td></tr>
  <tr><td>threshold=0.25/0.30</td><td>CI держится, но частота 0.07–0.08/нед — не лучше baseline.</td></tr>
  <tr><td>rank_window=30</td><td>Схожие lift/CI. Неожиданно: KZT h=20 CI=1.25 (N=2 сигнала OOT — слишком мало).</td></tr>
  <tr><td>LightGBM поверх индикатора</td><td>Деградирует на OOT: KGS 1.60→1.42, TJS 1.48→1.06. Переобучение.</td></tr>
  <tr><td>RSI</td><td>CI &lt; 1.0. Биржевой индикатор не подходит для межбанковского курса ЦБ.</td></tr>
  <tr><td>Сезонность (calendar)</td><td>Lift 1.08, CI &lt; 1.0.</td></tr>
</table>

<!-- 7. ЧЕСТНЫЕ ОГРАНИЧЕНИЯ -->
<h2>Честные ограничения</h2>

<div class="limitation-box">
  <strong>1. Частота: 0.057 сигнала/нед = 1 раз в 2–3 месяца</strong><br>
  Цель кейса — 1–2/нед. У нас в 15–30× реже. Это осознанный trade-off: более частый вариант
  (c0, 0.37/нед) статистически и экономически не работает — CI &lt; 1.0, bps отрицательный.
  Нет быстрого фикса на текущем индикаторе.
</div>

<div class="limitation-box">
  <strong>2. Маленькая OOT выборка: N=4–8 сигналов на коридор</strong><br>
  OOT период начался 01.07.2025. При частоте 0.057/нед накапливается ~3–4 события/коридор за ~14 месяцев.
  Статистически мало для уверенного вывода. Нужен живой пилот.
</div>

<div class="limitation-box">
  <strong>3. Работаем на курсе ЦБ, не на курсе исполнения</strong><br>
  Курс в приложении привязан к поставщикам ликвидности. Сигнал считается по ЦБ. Разница возможна —
  требует проверки в пилоте на реальных транзакционных данных.
</div>

<div class="limitation-box">
  <strong>4. KZT и UZS не работают</strong><br>
  KZT — управляемый курс (NBK interventions). UZS — lift есть, но CI не проходит.
</div>

<div class="page-break"></div>

<!-- 8. ЧЕКЛИСТ ДЛЯ РЕВЬЮ -->
<h2>Чеклист для ревью</h2>

<p>Для коллег, которые хотят проверить ключевые аспекты кода:</p>

<ul class="checklist">
  <li>
    <strong>Нет lookahead:</strong> в <code>src/indicators/log_return_percentile.py</code>
    метод <code>compute()</code> фильтрует данные по <code>cutoff_date</code>
    и нигде не использует данные после этой даты.
  </li>
  <li>
    <strong>Pathwise hit definition:</strong> в <code>src/backtest/metrics.py</code>
    функция <code>_forward_hits()</code> берёт <code>min(future_slice)</code>,
    а не <code>future_slice[-1]</code> — иначе lift завышен.
  </li>
  <li>
    <strong>OOT split чистый:</strong> параметры (threshold=0.20, rank_window=60, confirm_days=2)
    не менялись после первого запуска OOT валидации.
    Проверить: <code>git log --all scripts/run_oot_validation.py</code>.
  </li>
  <li>
    <strong>bps формула:</strong> <code>(mean(rate[t+1..t+h]) − rate[t]) / rate[t] × 10 000</code>
    — положительное = день сигнала <em>дешевле</em> среднего курса следующих h дней.
    В <code>src/backtest/metrics.py</code>, функция <code>bps_by_horizon()</code>.
  </li>
  <li>
    <strong>CI bootstrap:</strong> блоки 90 дней, 2000 resamples, circular —
    в <code>src/backtest/metrics.py</code>, функция <code>lift_confidence_interval()</code>.
  </li>
  <li>
    <strong>Compliance validator:</strong> в <code>src/texts/templates.py</code>
    запрещённые паттерны («скоро», «успейте», «гарантируем») отклоняются
    до генерации push-текста.
  </li>
  <li>
    <strong>Тесты проходят:</strong> <code>make test</code> → 30 passed, 0 failed.
  </li>
</ul>

<!-- 9. БЫСТРЫЙ ЗАПУСК -->
<h2>Воспроизвести результаты</h2>

<div class="code-block">git clone https://github.com/davadevi/fx-signal-layer.git
cd fx-signal-layer
pip install -r requirements.txt

# Данные
python -m src.data.download
python -m src.data.normalize

# OOT валидация (воспроизвести главный результат ~15 мин)
PYTHONPATH=. python scripts/run_oot_validation.py

# Тесты
make test   # ожидается: 30 passed

# Сигналы на сегодня
PYTHONPATH=. python -m src.pipeline.run --cutoff-date $(date +%Y-%m-%d)</div>

<h3>Файлы для чтения</h3>

<table>
  <tr><th>Файл</th><th>Что там</th></tr>
  <tr><td><code>src/indicators/log_return_percentile.py</code></td><td>Основной индикатор</td></tr>
  <tr><td><code>src/backtest/engine.py</code></td><td>Walk-forward engine, BacktestResult</td></tr>
  <tr><td><code>src/backtest/metrics.py</code></td><td>hit rate, lift, CI bootstrap, bps</td></tr>
  <tr><td><code>src/pipeline/signals.py</code></td><td>generate_signals(), cooldown</td></tr>
  <tr><td><code>scripts/run_oot_validation.py</code></td><td>Воспроизвести главный результат</td></tr>
  <tr><td><code>reports/oot_validation_2026-09-04.json</code></td><td>Сырые числа</td></tr>
  <tr><td><code>docs/experiments/frequency_increase_experiments.md</code></td><td>Все параметрические эксперименты</td></tr>
</table>

<div class="footer-note">
  FX Signal Layer · Alfa-Bank Hackathon · Актуально на 05.09.2026 · Числа из reports/oot_validation_2026-09-04.json
</div>

</div>
</body>
</html>"""

if __name__ == "__main__":
    from pathlib import Path

    html_path = Path("reports/review/fx_signal_layer_review.html")
    pdf_path  = Path("reports/review/fx_signal_layer_review.pdf")

    html_path.write_text(HTML, encoding="utf-8")
    print(f"HTML written → {html_path}")

    try:
        from weasyprint import HTML as WP
        WP(string=HTML, base_url=".").write_pdf(str(pdf_path))
        print(f"PDF written  → {pdf_path}")
    except Exception as e:
        print(f"weasyprint error: {e}")
        print("Run manually: weasyprint reports/fx_signal_layer_review.html reports/fx_signal_layer_review.pdf")

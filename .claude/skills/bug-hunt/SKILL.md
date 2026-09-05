---
name: bug-hunt
description: Систематический поиск багов через параллельные Explore-агенты с обязательной верификацией каждого утверждения перед фиксом. Использовать когда пользователь просит "найти баги", "проверить код на ошибки", "сделать аудит".
---

# Bug-hunt: систематический поиск багов

## Когда применять

- Пользователь говорит «найди баги», «проверь код», «сделай аудит», «доведи до идеала».
- После большого добавления функционала перед коммитом.
- Перед сдачей спринта.

## Что НЕ делать

❌ **Не доверять агентам слепо.** Они склонны к false positives (40-60% ложных срабатываний по опыту gig-platform). Всегда читай конкретные строки кода перед исправлением.

❌ Не запускать одного агента — нужно ≥2 для разных аспектов.

❌ Не фиксить всё подряд — сортируй по severity, фикси только реальное.

## Алгоритм

### Шаг 1. Параллельная разведка (3 агента максимум)

Запусти **в одном сообщении** 2-3 `Explore`-агента с разными фокусами. Примеры комбинаций:

| Цель | Агент 1 | Агент 2 | Агент 3 |
|---|---|---|---|
| Бэкенд-аудит | сервисы + API | Celery + модели | middleware + deps |
| Полный аудит | бэкенд-сервисы | frontend-компоненты | поиск мёртвого кода |
| Security-focus | авторизация в endpoints | crypto / JWT / hashing | SQL-инъекции / path traversal |

**Шаблон промпта для агента:**

```
Audit these files for REAL bugs (not style nitpicks):
1. file/path/A.py
2. file/path/B.py
...

Look for:
- Authorization bypass (user A reading/modifying user B's data)
- Race conditions in concurrent operations
- Wrong HTTP status codes
- Missing null checks that would cause 500
- Unused imports or dead code blocks
- Schema mismatch between Pydantic and SQLAlchemy

Report each as: file:line — description — severity (critical/high/medium/low).
Be conservative — only flag actual bugs, not style preferences.
Reject any false positive thoughts before reporting.
```

### Шаг 2. Верификация (КРИТИЧЕСКИЙ ШАГ)

Для **каждого** утверждения агента:

1. Прочитай конкретные строки файла (`Read` с `offset`/`limit`).
2. Проверь контекст вокруг — часто баг кажется реальным, но обернут в try/except или есть проверка выше.
3. Запусти `grep` чтобы подтвердить отсутствие связи.

**Категории false positives (по опыту):**
- "Missing `setLoading(false)`" — обычно есть `finally` блок
- "Missing commit" — обычно commit в caller
- "Hydration mismatch с Date.now()" — обычно отрабатывает Skeleton до hydrate
- "Dead `.catch` блок на Promise.allSettled" — обычно ловит ошибку из другого await выше
- "Missing authorization" — обычно проверяется в Depends(get_current_X)

### Шаг 3. Классификация

Раздели подтверждённые баги на:
- 🔴 **Critical** — security, потеря данных, double-spend
- 🟠 **High** — функционал сломан в основном сценарии
- 🟡 **Medium** — функционал сломан в редком сценарии, или плохой UX
- 🟢 **Low** — chore (unused import, magic number)

### Шаг 4. Презентация результата

Покажи таблицу:

```markdown
| # | Файл:строка | Проблема | Severity | Реальный? |
|---|---|---|---|---|
| 1 | file.py:42 | описание | 🔴 | ✅ |
| 2 | other.py:88 | описание | 🟡 | ❌ false positive |
```

И отдельно секцию **«Отклонены как false positives»** с пояснениями — это показывает что ты не безразлично передал слова агента, а проверил.

### Шаг 5. Фикс (по одному, отдельными коммитами)

Для каждого подтверждённого бага:
1. Fix в коде
2. Добавь regression test (если возможно)
3. Прогон тестов
4. Commit отдельно с описанием в формате:
   ```
   fix: <subsystem>: <one-line problem statement>
   
   <2-3 sentences explaining what was wrong and how it's fixed>
   <Mention test impact: "Tests: N PASS (was M)">
   ```

## Примечание по эффективности

~50% утверждений агентов — false positives. Без верификации высок риск "починить" рабочий код. Всегда читай строки кода перед фиксом.

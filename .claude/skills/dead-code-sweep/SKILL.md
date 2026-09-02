---
name: dead-code-sweep
description: Безопасный поиск и удаление неиспользуемого кода (файлы, функции, импорты) через git grep с обязательной верификацией. Использовать когда просят "почистить код", "удалить мёртвое", "найти неиспользуемое".
---

# Dead-code sweep: безопасное удаление мёртвого кода

## Когда применять

- «Почисти кодовую базу»
- «Удали то что не используется»
- «Найди неиспользуемые файлы»
- Подготовка к крупному рефакторингу

## Критическое правило

⚠️ **НИКОГДА не удаляй файл/функцию без проверки `git grep` хотя бы по двум вариантам имени.** Файл может импортироваться:
- Под другим именем (alias)
- Через строку (e.g., Celery `task_name="..."`)
- В тестах
- В CI/YAML/JSON
- В Alembic migrations

## Категории мёртвого кода

### 1. Полностью неимпортируемые файлы

**Команда:**
```bash
# Backend: для каждого подозрительного файла
git grep -l "from app.path.module\|import app.path.module" -- 'backend/**/*.py'

# Frontend: для компонента
git grep -l "ComponentName" -- 'frontend/src/**/*.tsx' 'frontend/src/**/*.ts' | grep -v "ComponentName.tsx"
```

Если grep вернул **пустой результат** (или только сам файл) — это мёртвый файл.

**Дополнительные проверки:**
```bash
# Проверь Celery task names (могут вызываться через строку)
grep -r "task_name\|name=\"" backend/app/tasks/

# Проверь Alembic referenced
grep -r "filename" backend/alembic/

# Проверь package.json scripts
grep -r "ComponentName" package.json tsconfig.json
```

### 2. Неиспользуемые импорты

**Команда:**
```bash
# Найти потенциально unused import
grep -n "^from\|^import" backend/app/services/X.py
# Для каждого импорта проверить usage в файле:
grep -c "ImportedName" backend/app/services/X.py  # > 1 = используется
```

Или используй `ruff`:
```bash
cd backend && uv run ruff check app/ --select F401
```

### 3. Дублирующиеся файлы (одинаковая функциональность)

```bash
# Найди файлы с похожими именами
ls tests/test_*rate*.py
# Сравни wc -l и содержимое
diff tests/test_rate_limiting.py tests/test_rate_limiting_enforcement.py
```

Часто бывает: один файл — реальные тесты, другой — пустышка или дубликат имени.

### 4. Stale TODO / NotImplementedError

```bash
grep -rn "TODO\|FIXME\|NotImplementedError\|raise NotImplemented" backend/app/ frontend/src/
```

Для каждого:
- Проверь связан ли с открытым багом/спринтом в `docs/`
- Если функционал РЕАЛИЗОВАН где-то ещё — удали stub целиком
- Если до сих пор актуально — перенеси в issue tracker

### 5. Junk-файлы в репозитории

```bash
# Найди типичный мусор
find . -name ".DS_Store" -o -name "*.tsbuildinfo" -o -name "celerybeat-schedule.db" -o -name "*.pyc" 2>/dev/null | grep -v node_modules | grep -v .venv

# Проверь gitignore
cat .gitignore | grep -E "tsbuildinfo|celerybeat|DS_Store"
```

Если найден мусор не в .gitignore — добавь паттерн.

## Алгоритм

1. **Прогнать тесты** (baseline): `pytest tests/ -q` → запомнить число PASS.
2. **Найти кандидатов** по 5 категориям выше.
3. **Верифицировать каждого**: `git grep` минимум 2-мя вариантами имени.
4. **Удалить** небольшими батчами (1 категория за раз).
5. **Прогнать тесты** после каждого батча — должно совпадать с baseline.
6. **Коммит** с детальным описанием:
   ```
   chore: remove dead code
   
   Deleted (verified via git grep — zero references):
   - path/to/file1.py — описание зачем был
   - path/to/file2.tsx
   
   Tests: N PASS (unchanged from baseline)
   ```

## Пример из реальной сессии

В gig-platform 2026-05-20 этот процесс удалил:
- `backend/app/integrations/moi_nalog_client.py` — stub, никогда не вызывался
- 3 React компонента: `AvailabilityCalendar`, `ReferralWidget`, `StatsCard`
- `backend/tests/test_rate_limiting.py` — дубликат, тесты ничего не проверяли (реальные в `test_rate_limiting_enforcement.py`)
- 4 неиспользуемых импорта

Тесты после: 263 PASS (минус 3 из удалённого дубликата) — ничего не сломано.

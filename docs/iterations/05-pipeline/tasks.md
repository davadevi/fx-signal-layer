# Iteration 05: Signal Pipeline

## Tasks
- [ ] Комбинирование индикаторов: взвешенное голосование по надёжности
- [ ] Cooldown: не слать если был сигнал < N дней назад
- [ ] Приоритизация при конкурирующих коридорах (лимит глобальный на клиента)
- [ ] Тексты пушей: шаблоны (indicator_type, direction) → push_text
- [ ] Чеклист запрещённых формулировок
- [ ] `make signals DATE=2025-01-15` → таблица сигналов
- [ ] `python -m src.pipeline.run --cutoff-date DATE` — CLI

.PHONY: setup data test lint backtest signals report clean

# Setup
setup:
	pip install -r requirements.txt
	pre-commit install
	@echo "Setup complete."

# Data
data:
	python -m src.data.download
	python -m src.data.normalize
	@echo "Data ready in data/processed/"

# Tests
test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# Linting
lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/ notebooks/
	ruff check --fix src/ tests/

# Backtest
backtest:
	python -m src.backtest.runner --all-corridors --all-indicators
	@echo "Results saved to reports/"

backtest-corridor:
	@test -n "$(CORRIDOR)" || (echo "Usage: make backtest-corridor CORRIDOR=RUB_TJS"; exit 1)
	python -m src.backtest.runner --corridor $(CORRIDOR) --all-indicators

# Signals (production-like run)
signals:
	@test -n "$(DATE)" || (echo "Usage: make signals DATE=2025-01-15"; exit 1)
	python -m src.pipeline.run --cutoff-date $(DATE)

signals-today:
	python -m src.pipeline.run --cutoff-date $$(date +%Y-%m-%d)

# Reports
report:
	python -m src.backtest.report --output reports/summary.html
	@echo "Report: reports/summary.html"

# Clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

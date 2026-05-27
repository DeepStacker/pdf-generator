.PHONY: test lint typecheck clean

PYTHON := python3
PACKAGE := audit_engine

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

typecheck:
	$(PYTHON) -m mypy src/$(PACKAGE)

run:
	PYTHONPATH=src $(PYTHON) -m $(PACKAGE)

build:
	bash scripts/BUILD_FOR_MAC_LINUX.sh

clean:
	rm -rf build/ dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

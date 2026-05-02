.PHONY: help install test test-fast test-cov test-watch lint clean dev

help:
	@echo "Targets:"
	@echo "  install     Install backend test dependencies in a local venv"
	@echo "  test        Run full backend test suite with coverage"
	@echo "  test-fast   Run tests without coverage (quicker)"
	@echo "  test-cov    Run tests and open HTML coverage report"
	@echo "  test-watch  Re-run tests on every file change (requires pytest-watch)"
	@echo "  dev         Start the full stack via docker compose"
	@echo "  clean       Remove caches, .pyc, coverage artifacts"

install:
	cd backend && python3 -m venv .venv && \
		.venv/bin/pip install --quiet --upgrade pip && \
		.venv/bin/pip install --quiet -r requirements.txt

test: install
	cd backend && .venv/bin/pytest

test-fast: install
	cd backend && .venv/bin/pytest --no-cov -q

test-cov: test
	@echo "Coverage HTML report: backend/htmlcov/index.html"

dev:
	docker compose up --build

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name "htmlcov" -prune -exec rm -rf {} +
	rm -f backend/.coverage backend/_test.db

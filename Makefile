.PHONY: help dev install test test-cov lint format check type-check security pre-commit clean build watch ci

# Default target
help:
	@echo "Echo AI Chatbot - Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make dev         Install package with development dependencies"
	@echo "  make install     Install package in editable mode (production only)"
	@echo "  make pre-commit  Install pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run tests with pytest"
	@echo "  make test-cov    Run tests with coverage report (target: 50%%+)"
	@echo "  make test-html   Run tests and generate HTML coverage report"
	@echo ""
	@echo "Linting & Formatting (ruff):"
	@echo "  make lint        Run ruff linter"
	@echo "  make format      Format code with ruff"
	@echo "  make check       Check formatting and lint without modifying"
	@echo ""
	@echo "Type Checking:"
	@echo "  make type-check  Run mypy type checker"
	@echo ""
	@echo "Security:"
	@echo "  make security    Run bandit security scanner"
	@echo ""
	@echo "Development:"
	@echo "  make clean       Remove build artifacts and caches"
	@echo "  make build       Build distribution packages"
	@echo "  make watch       Watch for file changes and re-run tests"
	@echo ""
	@echo "Quality Gate (CI):"
	@echo "  make ci          Run full CI pipeline (format -> lint -> type-check -> test -> security)"

# Install development dependencies
dev:
	pip install -e ".[dev]"

# Install package (production only)
install:
	pip install -e .

# Install pre-commit hooks
pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed"

# Run tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --cov=src/echo --cov-report=term-missing --cov-fail-under=50

# Run tests with HTML coverage report
test-html:
	python -m pytest tests/ -v --cov=src/echo --cov-report=html --cov-report=term-missing
	@echo "HTML coverage report generated in htmlcov/"
	@echo "Open: htmlcov/index.html"

# Run ruff linter
lint:
	python -m ruff check src/echo/ tests/

# Format code with ruff
format:
	python -m ruff check src/echo/ tests/ --fix
	python -m ruff format src/echo/ tests/

# Check formatting and lint without modifying
check:
	python -m ruff check src/echo/ tests/
	python -m ruff format src/echo/ tests/ --check
	@echo "Ruff check passed"

# Run type checker
type-check:
	python -m mypy src/echo/ --config-file pyproject.toml

# Run security scanner
security:
	python -m bandit -c pyproject.toml -r src/echo/
	@echo "Bandit security scan passed"

# Run pre-commit hooks on all files
pre-commit-all:
	pre-commit run --all-files

# Full CI pipeline
ci: format lint type-check test-cov security
	@echo ""
	@echo "========================================="
	@echo "  CI Pipeline Passed [OK]"
	@echo "========================================="

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	@echo "Cleaned"

# Build distribution packages
build:
	python -m build

# Watch for file changes and re-run tests
watch:
	python -m watchdog.watchmedo shell-command \
		--patterns="*.py" \
		--recursive \
		--command="python -m pytest tests/ -q" \
		src/echo/ tests/

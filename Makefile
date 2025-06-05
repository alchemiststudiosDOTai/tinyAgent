.PHONY: lint format install-lint fix fix-unsafe lint-stats clean test

install-lint:
	pip install -e ".[lint]"

format:
	black src tests
	isort src tests

lint: 
	@echo "Running linters..."
	ruff check src tests
	black --check src tests  
	isort --check-only src tests
	@echo "Linting complete!"1

fix:
	ruff check --fix src tests
	black src tests
	isort src tests

fix-unsafe:
	ruff check --fix --unsafe-fixes src tests
	black src tests
	isort src tests

lint-stats:
	@echo "=== Linting Statistics ==="
	-@ruff check src tests --statistics || true

lint-detailed:
	@echo "=== Detailed Lint Report ==="
	@ruff check src tests --select=B904,E402,F821,F401

lint-errors:
	@echo "=== Specific Linting Errors ==="
	-@ruff check src tests || true

fix-bare-except:
	@echo "=== Fixing bare except clauses ==="
	@find src tests -name "*.py" -exec sed -i 's/except:/except Exception:/g' {} +
	@echo "Fixed bare except clauses"

fix-imports:
	@echo "=== Fixing import order ==="
	isort src tests

fix-type-comparisons:
	@echo "=== Fixing type comparisons (== to is) ==="
	@find src tests -name "*.py" -exec sed -i 's/if param\.annotation == int:/if param.annotation is int:/g' {} +
	@find src tests -name "*.py" -exec sed -i 's/elif param\.annotation == float:/elif param.annotation is float:/g' {} +
	@find src tests -name "*.py" -exec sed -i 's/elif param\.annotation == str:/elif param.annotation is str:/g' {} +
	@find src tests -name "*.py" -exec sed -i 's/if param\.annotation == bool:/if param.annotation is bool:/g' {} +
	@echo "Fixed type comparisons"

fix-unused-imports:
	@echo "=== Removing unused imports ==="
	@ruff check --select F401 --fix src tests
	@echo "Fixed unused imports"

fix-exception-chaining:
	@echo "=== Fixing exception chaining ==="
	@python scripts/fix_exception_chaining.py
	@echo "Fixed exception chaining"

fix-all: fix-bare-except fix-type-comparisons fix-unused-imports fix-unsafe fix-imports
	@echo "=== Applied all automatic fixes ==="
	@make lint-stats

check: format lint

# Summary target to help understand what to do
help:
	@echo "Available make targets:"
	@echo "  make install-lint   - Install linting dependencies"
	@echo "  make format        - Auto-format code with black and isort"
	@echo "  make lint          - Check for linting issues"
	@echo "  make lint-stats    - Show linting error statistics"
	@echo "  make lint-errors   - Show specific linting errors"
	@echo "  make fix           - Auto-fix safe linting issues"
	@echo "  make fix-unsafe    - Auto-fix more issues (use with caution)"
	@echo "  make fix-bare-except - Fix bare except clauses"
	@echo "  make fix-imports   - Fix import ordering"
	@echo "  make check         - Format and lint code"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make test          - Run tests"
	@echo "  make test-fast     - Run tests with fail fast"
	@echo ""
	@echo "Current linting status:"
	@make lint-stats

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info

test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -x --tb=short 
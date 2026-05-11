.PHONY: help env-create env-update install install-dev lint format type-check test clean

help:
	@echo "TDX Tool Development Environment"
	@echo ""
	@echo "Available commands:"
	@echo "  make env-create      Create conda environment from environment.yml"
	@echo "  make env-update      Update conda environment"
	@echo "  make env-remove      Remove conda environment"
	@echo "  make install         Install package and dependencies in editable mode"
	@echo "  make install-dev     Install package with development dependencies"
	@echo "  make lint            Run ruff linter"
	@echo "  make format          Format code with ruff"
	@echo "  make type-check      Run mypy type checker"
	@echo "  make test            Run pytest"
	@echo "  make test-verbose    Run pytest with verbose output"
	@echo "  make clean           Remove build artifacts and cache files"

# Conda environment management
env-create:
	conda env create -f environment.yml

env-update:
	conda env update -f environment.yml --prune

env-remove:
	conda remove --name tdx-dev --all

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Code quality
lint:
	ruff check src/ tests/ || true

format:
	ruff format src/ tests/

type-check:
	mypy src/tdx_tool/

# Testing
test:
	pytest

test-verbose:
	pytest -v

# Cleanup
clean:
	rm -rf build/ dist/ .eggs/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/

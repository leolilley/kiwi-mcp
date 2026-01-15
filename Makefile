.PHONY: install test lint format clean dev

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check kiwi_mcp tests

format:
	ruff format kiwi_mcp tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache build dist *.egg-info

dev: install-dev
	@echo "Development environment ready"

check:
	python -m pip check

version:
	@python -c "from kiwi_mcp import __version__; print(__version__)"

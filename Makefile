# Makefile for bUE-lake_tests project

.PHONY: install test test-verbose coverage clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install test dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  coverage     - Run tests with coverage report"
	@echo "  clean        - Clean up generated files"

# Install test dependencies
install:
	pip install -r setup/requirements_test.txt

# Run tests
test:
	python -m pytest tests/ -v

# Run tests with verbose output
test-verbose:
	python -m pytest tests/ -v -s

# Run tests with coverage
coverage:
	python -m pytest tests/ -v --cov=ota --cov-report=html --cov-report=term-missing

# Clean up generated files
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

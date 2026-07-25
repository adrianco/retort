PYTHON ?= python3

.PHONY: install test demo serve clean

install:              ## Install the package and the test dependencies
	$(PYTHON) -m pip install -e ".[dev]"

test:                 ## Run the test suite
	$(PYTHON) -m pytest

demo:                 ## Answer the sample questions from the specification
	$(PYTHON) -m brazilian_soccer.demo

serve:                ## Run the MCP server over stdio
	$(PYTHON) -m brazilian_soccer.server

clean:
	rm -rf .pytest_cache build dist *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

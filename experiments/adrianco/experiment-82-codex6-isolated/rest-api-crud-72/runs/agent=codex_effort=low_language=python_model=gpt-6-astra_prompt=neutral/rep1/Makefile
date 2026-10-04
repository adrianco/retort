PYTHON ?= python3
VENV ?= .venv

.PHONY: setup test run
setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r requirements.txt

test: setup
	$(VENV)/bin/python -m compileall -q app.py test_app.py
	$(VENV)/bin/python -m unittest discover -v

run: setup
	$(VENV)/bin/python app.py

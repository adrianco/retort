"""
================================================================================
Module: tests.conftest
Project: Brazilian Soccer MCP Server - test suite
--------------------------------------------------------------------------------
CONTEXT
  Shared pytest fixtures and the common BDD "Given" step for the whole suite.

  The datasets are loaded exactly once per test session (module-scoped cached
  singleton in data_loader) and exposed via the `data` fixture; the `context`
  fixture is a per-scenario scratchpad the When/Then steps read and write so
  BDD scenarios can pass state between steps.
================================================================================
"""

import pytest
from pytest_bdd import given

from brazilian_soccer_mcp.data_loader import get_data


@pytest.fixture(scope="session")
def data():
    """Load all datasets once for the entire test session."""
    return get_data()


@pytest.fixture
def context():
    """Per-scenario mutable scratchpad shared across BDD steps."""
    return {}


@given("the soccer data is loaded")
def _soccer_data_loaded(data, context):
    context["data"] = data
    assert len(data.matches) > 0
    assert len(data.players) > 0

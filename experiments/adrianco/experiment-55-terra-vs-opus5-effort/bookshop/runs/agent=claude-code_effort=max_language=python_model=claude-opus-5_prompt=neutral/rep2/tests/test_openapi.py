"""The served OpenAPI document must describe the routes that actually exist."""

from __future__ import annotations

import re

IGNORED_RULES = {"/", "/openapi.json", "/static/<path:filename>"}


def _documented(spec):
    return {
        (path, method.upper())
        for path, operations in spec["paths"].items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }


def _implemented(app):
    routes = set()
    for rule in app.url_map.iter_rules():
        if rule.rule in IGNORED_RULES:
            continue
        # /books/<int:book_id> -> /books/{book_id}
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            routes.add((path, method))
    return routes


def test_spec_is_served(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.get_json()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "Book Collection API"


def test_spec_matches_the_implemented_routes(app, client):
    spec = client.get("/openapi.json").get_json()

    assert _documented(spec) == _implemented(app)


def test_no_schema_declares_an_empty_required_list(client):
    """OpenAPI 3.0 gives ``required`` a minItems of 1, so ``[]`` is invalid."""
    spec = client.get("/openapi.json").get_json()

    for name, schema in spec["components"]["schemas"].items():
        assert schema.get("required", ["x"]) != [], name


def test_every_operation_declares_a_success_response(client):
    spec = client.get("/openapi.json").get_json()

    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            if method == "parameters":
                continue
            codes = set(operation["responses"])
            assert codes & {"200", "201", "204"}, f"{method.upper()} {path}"


def test_every_schema_reference_resolves(client):
    spec = client.get("/openapi.json").get_json()
    defined = {f"#/components/schemas/{name}" for name in spec["components"]["schemas"]}

    referenced = set()

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                referenced.add(node["$ref"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(spec["paths"])
    assert referenced <= defined

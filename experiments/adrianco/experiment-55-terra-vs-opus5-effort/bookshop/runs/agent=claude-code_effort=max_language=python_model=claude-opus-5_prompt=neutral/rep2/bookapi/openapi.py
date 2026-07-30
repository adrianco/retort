"""A hand-written OpenAPI 3.0 description, served at ``GET /openapi.json``.

Keeping it in one place means the README, the tests and any generated client
all agree on what the service promises.
"""

from __future__ import annotations

from typing import Any

from .validation import (
    MAX_AUTHOR_LENGTH,
    MAX_ISBN_LENGTH,
    MAX_LIMIT,
    MAX_TITLE_LENGTH,
    MIN_YEAR,
    SORTABLE_FIELDS,
    max_year,
)


def _year_schema(upper: int) -> dict[str, Any]:
    """The bounds ``_clean_year`` enforces.  ``upper`` moves with the calendar."""
    return {
        "type": "integer",
        "nullable": True,
        "minimum": MIN_YEAR,
        "maximum": upper,
        "example": 1958,
    }


def _book_schema(upper: int) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["id", "title", "author", "created_at", "updated_at"],
        "properties": {
            "id": {"type": "integer", "readOnly": True, "example": 1},
            "title": {
                "type": "string",
                "maxLength": MAX_TITLE_LENGTH,
                "example": "Things Fall Apart",
            },
            "author": {
                "type": "string",
                "maxLength": MAX_AUTHOR_LENGTH,
                "example": "Chinua Achebe",
            },
            "year": _year_schema(upper),
            "isbn": {
                "type": "string",
                "nullable": True,
                "maxLength": MAX_ISBN_LENGTH,
                "example": "978-0-385-47454-2",
            },
            "created_at": {"type": "string", "format": "date-time", "readOnly": True},
            "updated_at": {"type": "string", "format": "date-time", "readOnly": True},
        },
    }


def _write_schema(upper: int) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["title", "author"],
        "properties": {
            key: value
            for key, value in _book_schema(upper)["properties"].items()
            if key in ("title", "author", "year", "isbn")
        },
    }


def _patch_schema(upper: int) -> dict[str, Any]:
    """Same properties as BookWrite but nothing is mandatory.

    ``required`` is dropped rather than set to ``[]``, which OpenAPI 3.0 rejects
    (it gives the array a ``minItems`` of 1).
    """
    return {
        key: value for key, value in _write_schema(upper).items() if key != "required"
    }

_ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["error", "code"],
    "properties": {
        "error": {"type": "string", "example": "Request validation failed."},
        "code": {"type": "string", "example": "validation_error"},
        "details": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "example": {"title": "this field is required"},
        },
    },
}


def _error(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/Error"}
            }
        },
    }


def _book_response(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Book"}}
        },
    }


def _body(schema_name: str) -> dict[str, Any]:
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


_ID_PARAM = {
    "name": "book_id",
    "in": "path",
    "required": True,
    "schema": {"type": "integer"},
    "description": "Identifier of the book.",
}


def build_spec(version: str) -> dict[str, Any]:
    """Return the OpenAPI document describing this service."""
    upper_year = max_year()
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Book Collection API",
            "version": version,
            "description": "CRUD service for a personal book collection.",
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Service and database health.",
                    "operationId": "health",
                    "responses": {
                        "200": {"description": "The service and database are up."},
                        "503": {"description": "The database is unreachable."},
                    },
                }
            },
            "/books": {
                "get": {
                    "summary": "List books.",
                    "operationId": "listBooks",
                    "parameters": [
                        {
                            "name": "author",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Whole author name; case-insensitive "
                            "for ASCII letters only.",
                        },
                        {
                            "name": "title",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Title substring; case-insensitive "
                            "for ASCII letters only.",
                        },
                        {
                            # Same bounds as the request body: the filter reuses
                            # the field validator, so out-of-range years are 400s.
                            "name": "year",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": MIN_YEAR,
                                "maximum": upper_year,
                            },
                            "description": "Exact publication year.",
                        },
                        {
                            "name": "sort",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": [
                                    prefix + field
                                    for field in SORTABLE_FIELDS
                                    for prefix in ("", "-")
                                ],
                            },
                            "description": "Sort column; '-' prefix sorts descending.",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": MAX_LIMIT,
                            },
                            "description": "Page size. Omit to return every match.",
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 0},
                            "description": "Number of matches to skip.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Matching books; X-Total-Count holds the "
                            "unpaginated total.",
                            "headers": {
                                "X-Total-Count": {
                                    "schema": {"type": "integer"},
                                    "description": "Total matches ignoring paging.",
                                }
                            },
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/Book"
                                        },
                                    }
                                }
                            },
                        },
                        "400": _error("Invalid query parameters."),
                    },
                },
                "post": {
                    "summary": "Create a book.",
                    "operationId": "createBook",
                    "requestBody": _body("BookWrite"),
                    "responses": {
                        "201": _book_response("The created book."),
                        "400": _error("Invalid request body."),
                    },
                },
            },
            "/books/{book_id}": {
                "parameters": [_ID_PARAM],
                "get": {
                    "summary": "Fetch one book.",
                    "operationId": "getBook",
                    "responses": {
                        "200": _book_response("The requested book."),
                        "404": _error("No such book."),
                    },
                },
                "put": {
                    "summary": "Replace a book.",
                    "operationId": "replaceBook",
                    "description": "Omitted optional fields are cleared.",
                    "requestBody": _body("BookWrite"),
                    "responses": {
                        "200": _book_response("The updated book."),
                        "400": _error("Invalid request body."),
                        "404": _error("No such book."),
                    },
                },
                "patch": {
                    "summary": "Partially update a book.",
                    "operationId": "patchBook",
                    "requestBody": _body("BookPatch"),
                    "responses": {
                        "200": _book_response("The updated book."),
                        "400": _error("Invalid request body."),
                        "404": _error("No such book."),
                    },
                },
                "delete": {
                    "summary": "Delete a book.",
                    "operationId": "deleteBook",
                    "responses": {
                        "204": {"description": "The book was deleted."},
                        "404": _error("No such book."),
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "Book": _book_schema(upper_year),
                "BookWrite": _write_schema(upper_year),
                "BookPatch": _patch_schema(upper_year),
                "Error": _ERROR_SCHEMA,
            }
        },
    }

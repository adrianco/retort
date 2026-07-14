# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `app.py:health_check` |
| POST | /books | `201 Book \| 400 \| 500` | `app.py:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.py:get_books` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404 \| 500` | `app.py:update_book` |
| DELETE | /books/{id} | `200 {message} \| 404 \| 500` | `app.py:delete_book` |

## Data schema

`book` table (SQLAlchemy model `Book`): id (int, pk), title (str, not null),
author (str, not null), year (int, not null), isbn (str, unique, nullable),
created_at (datetime), updated_at (datetime, onupdate).

## Library API

`app` (Flask app), `db` (SQLAlchemy), `Book` (model) — imported directly by `test_app.py`.

## CLI commands

(none) — `python app.py` starts the dev server on `0.0.0.0:5000`.

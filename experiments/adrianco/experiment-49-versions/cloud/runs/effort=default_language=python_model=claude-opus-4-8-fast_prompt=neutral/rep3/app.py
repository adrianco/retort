"""Book collection REST API built with Flask and SQLite."""

from flask import Flask, g, jsonify, request

from database import get_connection, init_db


def _row_to_book(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate_book(data):
    """Return (payload, error_message). title and author are required."""
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    title = data.get("title")
    author = data.get("author")

    if not isinstance(title, str) or not title.strip():
        return None, "'title' is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return None, "'author' is required and must be a non-empty string"

    year = data.get("year")
    if year is not None and not isinstance(year, int):
        return None, "'year' must be an integer"

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "'isbn' must be a string"

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn,
    }, None


def create_app(db_path: str = "books.db") -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    init_db(db_path)

    def get_db():
        if "db" not in g:
            g.db = get_connection(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        payload, error = _validate_book(data)
        if error:
            return jsonify(error=error), 400

        conn = get_db()
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload["year"], payload["isbn"]),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(_row_to_book(row)), 201

    @app.get("/books")
    def list_books():
        conn = get_db()
        author = request.args.get("author")
        if author is not None:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify(error="Book not found"), 404
        return jsonify(_row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify(error="Book not found"), 404

        data = request.get_json(silent=True)
        payload, error = _validate_book(data)
        if error:
            return jsonify(error=error), 400

        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (payload["title"], payload["author"], payload["year"], payload["isbn"], book_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(_row_to_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        conn = get_db()
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify(error="Book not found"), 404
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

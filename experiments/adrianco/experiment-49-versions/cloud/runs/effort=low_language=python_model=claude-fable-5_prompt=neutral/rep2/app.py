import sqlite3

from flask import Flask, g, jsonify, request

DATABASE = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(database=DATABASE):
    app = Flask(__name__)
    app.config["DATABASE"] = database

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute(SCHEMA)
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def book_dict(row):
        return dict(row)

    def validate(data, partial=False):
        errors = {}
        if data is None or not isinstance(data, dict):
            return {"body": "JSON object required"}
        for field in ("title", "author"):
            if field in data or not partial:
                value = data.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors[field] = f"{field} is required and must be a non-empty string"
        if "year" in data and data["year"] is not None and not isinstance(data["year"], int):
            errors["year"] = "year must be an integer"
        if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
            errors["isbn"] = "isbn must be a string"
        return errors

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        errors = validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(book_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute("SELECT * FROM books WHERE author = ?", (author,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
        return jsonify([book_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        data = request.get_json(silent=True)
        errors = validate(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        updated = {**book_dict(row), **{k: data[k] for k in ("title", "author", "year", "isbn") if k in data}}
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (updated["title"], updated["author"], updated["year"], updated["isbn"], book_id),
        )
        db.commit()
        return jsonify(updated)

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

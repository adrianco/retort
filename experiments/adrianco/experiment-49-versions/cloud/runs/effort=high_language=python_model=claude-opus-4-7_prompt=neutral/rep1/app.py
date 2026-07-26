import os
import sqlite3
from flask import Flask, g, jsonify, request


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get("DATABASE", "books.db")

    def get_db():
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = sqlite3.connect(app.config["DATABASE"])
            db.row_factory = sqlite3.Row
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )
                """
            )
            db.commit()
        return db

    @app.teardown_appcontext
    def close_db(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    def row_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_book_payload(data, partial=False):
        if not isinstance(data, dict):
            return "Request body must be a JSON object"
        if not partial:
            if not data.get("title") or not isinstance(data.get("title"), str) or not data["title"].strip():
                return "'title' is required and must be a non-empty string"
            if not data.get("author") or not isinstance(data.get("author"), str) or not data["author"].strip():
                return "'author' is required and must be a non-empty string"
        else:
            if "title" in data and (not isinstance(data["title"], str) or not data["title"].strip()):
                return "'title' must be a non-empty string"
            if "author" in data and (not isinstance(data["author"], str) or not data["author"].strip()):
                return "'author' must be a non-empty string"
        if "year" in data and data["year"] is not None and not isinstance(data["year"], int):
            return "'year' must be an integer"
        if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
            return "'isbn' must be a string"
        return None

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        error = validate_book_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                data["title"].strip(),
                data["author"].strip(),
                data.get("year"),
                data.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True)
        error = validate_book_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        updated = {
            "title": data["title"].strip() if "title" in data else row["title"],
            "author": data["author"].strip() if "author" in data else row["author"],
            "year": data["year"] if "year" in data else row["year"],
            "isbn": data["isbn"] if "isbn" in data else row["isbn"],
        }
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (updated["title"], updated["author"], updated["year"], updated["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

import os
import sqlite3

from flask import Flask, g, jsonify, request


DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get("DATABASE_URL", DEFAULT_DB)

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            conn = sqlite3.connect(app.config["DATABASE"])
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db() -> None:
        with app.app_context():
            db = get_db()
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

    init_db()

    def row_to_book(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_book_payload(data, *, partial: bool = False):
        if not isinstance(data, dict):
            return None, ("Request body must be a JSON object", 400)

        errors = []

        if not partial or "title" in data:
            title = data.get("title")
            if not isinstance(title, str) or not title.strip():
                errors.append("'title' is required and must be a non-empty string")

        if not partial or "author" in data:
            author = data.get("author")
            if not isinstance(author, str) or not author.strip():
                errors.append("'author' is required and must be a non-empty string")

        if "year" in data and data["year"] is not None:
            year = data["year"]
            if not isinstance(year, int) or isinstance(year, bool):
                errors.append("'year' must be an integer")

        if "isbn" in data and data["isbn"] is not None:
            isbn = data["isbn"]
            if not isinstance(isbn, str):
                errors.append("'isbn' must be a string")

        if errors:
            return None, ({"errors": errors}, 400)

        cleaned = {}
        if "title" in data:
            cleaned["title"] = data["title"].strip()
        if "author" in data:
            cleaned["author"] = data["author"].strip()
        if "year" in data:
            cleaned["year"] = data["year"]
        if "isbn" in data:
            cleaned["isbn"] = data["isbn"]

        return cleaned, None

    @app.route("/health", methods=["GET"])
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
            return jsonify({"status": "ok"}), 200
        except sqlite3.Error as exc:
            return jsonify({"status": "error", "detail": str(exc)}), 500

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        cleaned, err = validate_book_payload(data, partial=False)
        if err is not None:
            body, status = err
            if isinstance(body, str):
                return jsonify({"error": body}), status
            return jsonify(body), status

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
            ),
        )
        db.commit()
        new_id = cur.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
        return jsonify(row_to_book(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id: int):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(row_to_book(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id: int):
        data = request.get_json(silent=True)
        cleaned, err = validate_book_payload(data, partial=True)
        if err is not None:
            body, status = err
            if isinstance(body, str):
                return jsonify({"error": body}), status
            return jsonify(body), status

        if not cleaned:
            return jsonify({"error": "No fields provided"}), 400

        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404

        merged = {
            "title": cleaned["title"] if "title" in cleaned else existing["title"],
            "author": cleaned["author"] if "author" in cleaned else existing["author"],
            "year": cleaned["year"] if "year" in cleaned else existing["year"],
            "isbn": cleaned["isbn"] if "isbn" in cleaned else existing["isbn"],
        }

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id: int):
        db = get_db()
        existing = db.execute(
            "SELECT id FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return ("", 204)

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

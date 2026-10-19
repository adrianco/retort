import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")
    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    year = data.get("year")
    isbn = data.get("isbn")

    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return jsonify({"error": "year must be an integer"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (str(title).strip(), str(author).strip(), year, isbn),
    )
    db.commit()
    book_id = cur.lastrowid

    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(_book_dict(book)), 201


@app.route("/books", methods=["GET"])
def list_books():
    db = get_db()
    author = request.args.get("author")
    if author:
        rows = db.execute("SELECT * FROM books WHERE author = ?", (author,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()
    return jsonify([_book_dict(r) for r in rows]), 200


@app.route("/books/<int:id>", methods=["GET"])
def get_book(id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(_book_dict(book)), 200


@app.route("/books/<int:id>", methods=["PUT"])
def update_book(id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])
    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    year = data.get("year", book["year"])
    isbn = data.get("isbn", book["isbn"])

    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return jsonify({"error": "year must be an integer"}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (str(title).strip(), str(author).strip(), year, isbn, id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()
    return jsonify(_book_dict(updated)), 200


@app.route("/books/<int:id>", methods=["DELETE"])
def delete_book(id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (id,))
    db.commit()
    return "", 204


def _book_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

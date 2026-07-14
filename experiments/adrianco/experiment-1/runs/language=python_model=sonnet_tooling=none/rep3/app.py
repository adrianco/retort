import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.environ.get("DATABASE", "books.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
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
    db.close()


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/books")
def create_book():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    if not author:
        return jsonify({"error": "author is required"}), 400

    year = data.get("year")
    isbn = data.get("isbn")

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn),
    )
    db.commit()
    book_id = cur.lastrowid
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(book_to_dict(row)), 201


@app.get("/books")
def list_books():
    author_filter = request.args.get("author")
    db = get_db()
    if author_filter:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?", (f"%{author_filter}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()
    return jsonify([book_to_dict(r) for r in rows])


@app.get("/books/<int:book_id>")
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book_to_dict(row))


@app.put("/books/<int:book_id>")
def update_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", row["title"])
    author = data.get("author", row["author"])
    year = data.get("year", row["year"])
    isbn = data.get("isbn", row["isbn"])

    if not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    db.execute(
        "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
        (title, author, year, isbn, book_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(book_to_dict(updated))


@app.delete("/books/<int:book_id>")
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

from flask import Flask, request, jsonify, abort
import sqlite3
import json

app = Flask(__name__)
DATABASE = 'books.db'

# Initialize database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        ''')
        conn.commit()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({"error": "Title and author are required"}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data.get('title'), data.get('author'), data.get('year'), data.get('isbn'))
        )
        book_id = cursor.lastrowid
        conn.commit()

    return jsonify({"id": book_id, **data}), 201

@app.route('/books', methods=['GET'])
def list_books():
    author = request.args.get('author')
    query = "SELECT * FROM books"
    params = []

    if author:
        query += " WHERE author = ?"
        params.append(author)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        books = cursor.fetchall()

    return jsonify([
        {"id": book[0], "title": book[1], "author": book[2], "year": book[3], "isbn": book[4]}
        for book in books
    ]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()

    if book is None:
        abort(404)

    return jsonify({
        "id": book[0], 
        "title": book[1], 
        "author": book[2], 
        "year": book[3], 
        "isbn": book[4]
    }), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({"error": "Title and author are required"}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data.get('title'), data.get('author'), data.get('year'), data.get('isbn'), book_id)
        )
        if cursor.rowcount == 0:
            abort(404)
        conn.commit()

    return '', 204

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            abort(404)
        conn.commit()

    return '', 204

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

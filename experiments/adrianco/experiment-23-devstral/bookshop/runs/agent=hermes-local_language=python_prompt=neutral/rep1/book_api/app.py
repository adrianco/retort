from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

DATABASE = 'books.db'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        ''')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('author'):
        return jsonify({'error': 'Title and author are required'}), 400
    
    with get_db() as db:
        cursor = db.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (data.get('title'), data.get('author'), data.get('year'), data.get('isbn'))
        )
        db.commit()
        book_id = cursor.lastrowid
    
    return jsonify({'id': book_id, **data}), 201

@app.route('/books', methods=['GET'])
def list_books():
    author = request.args.get('author')
    
    query = "SELECT * FROM books"
    params = []
    
    if author:
        query += " WHERE author = ?"
        params.append(author)
    
    with get_db() as db:
        cursor = db.execute(query, params)
        books = [dict(row) for row in cursor.fetchall()]
    
    return jsonify(books), 200

@app.route('/books/<int:id>', methods=['GET'])
def get_book(id):
    with get_db() as db:
        cursor = db.execute('SELECT * FROM books WHERE id = ?', (id,))
        book = cursor.fetchone()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(dict(book)), 200

@app.route('/books/<int:id>', methods=['PUT'])
def update_book(id):
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('author'):
        return jsonify({'error': 'Title and author are required'}), 400
    
    with get_db() as db:
        cursor = db.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (data.get('title'), data.get('author'), data.get('year'), data.get('isbn'), id)
        )
        db.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Book not found'}), 404
    
    return jsonify({'id': id, **data}), 200

@app.route('/books/<int:id>', methods=['DELETE'])
def delete_book(id):
    with get_db() as db:
        cursor = db.execute('DELETE FROM books WHERE id = ?', (id,))
        db.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Book not found'}), 404
    
    return '', 204

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

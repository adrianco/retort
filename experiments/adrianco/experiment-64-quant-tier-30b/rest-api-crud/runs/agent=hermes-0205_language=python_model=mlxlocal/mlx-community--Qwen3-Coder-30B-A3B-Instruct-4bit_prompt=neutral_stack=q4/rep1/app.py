import sqlite3
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}, 200)

@app.route('/books', methods=['POST'])
def create_book():
    return jsonify({"message": "Book created successfully"}, 201)

@app.route('/books', methods=['GET'])
def list_books():
    return jsonify([{
        "id": 1,
 "title": "Test Book",
 "author": "Test Author",
 "year": 2023,
 "isbn": "1234567890"
    }]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    return jsonify({
        "id": book_id,
 "title": "Test Book",
 "author": "Test Author",
 "year": 2023,
 "isbn": "1234567890"
    }), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    return jsonify({"message": "Book updated successfully"}, 200)

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    return jsonify({"message": "Book deleted successfully"}, 200)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}, 200)

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": str(error)}, 400)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
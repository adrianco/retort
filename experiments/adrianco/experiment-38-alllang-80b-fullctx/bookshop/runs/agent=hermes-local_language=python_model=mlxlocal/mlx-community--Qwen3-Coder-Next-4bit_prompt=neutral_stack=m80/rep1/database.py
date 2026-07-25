import sqlite3
import os

DATABASE_PATH = os.environ.get("DATABASE_PATH", "books.db")


def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with the books table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_book_by_id(book_id: int):
    """Get a book by its ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "year": row[3],
            "isbn": row[4]
        }
    return None


def create_book(title: str, author: str, year: int = None, isbn: str = None):
    """Create a new book"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn)
    )
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return get_book_by_id(book_id)


def update_book(book_id: int, title: str = None, author: str = None, 
                year: int = None, isbn: str = None):
    """Update an existing book"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current values
    cursor.execute("SELECT title, author, year, isbn FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    # Use new values or keep existing
    new_title = title if title is not None else row[0]
    new_author = author if author is not None else row[1]
    new_year = year if year is not None else row[2]
    new_isbn = isbn if isbn is not None else row[3]
    
    cursor.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (new_title, new_author, new_year, new_isbn, book_id)
    )
    conn.commit()
    conn.close()
    
    return get_book_by_id(book_id)


def delete_book(book_id: int):
    """Delete a book"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0


def list_books(author: str = None):
    """List all books, optionally filtered by author"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if author:
        cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE author = ?", (author,))
    else:
        cursor.execute("SELECT id, title, author, year, isbn FROM books")
    
    rows = cursor.fetchall()
    conn.close()
    
    books = []
    for row in rows:
        books.append({
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "year": row[3],
            "isbn": row[4]
        })
    
    return books

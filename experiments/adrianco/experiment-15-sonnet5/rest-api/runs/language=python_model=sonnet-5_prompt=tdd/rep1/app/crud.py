from app import database


def create_book(book):
    conn = database.get_connection()
    cursor = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn),
    )
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    return book_id


def update_book(book_id, book):
    conn = database.get_connection()
    cursor = conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (book.title, book.author, book.year, book.isbn, book_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def delete_book(book_id):
    conn = database.get_connection()
    cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_book(book_id):
    conn = database.get_connection()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_books(author=None):
    conn = database.get_connection()
    if author is not None:
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ?", (author,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return [dict(row) for row in rows]

use crate::models::Book;
use crate::DbPool;
use rusqlite::params;

pub fn init_db(pool: &DbPool) -> rusqlite::Result<()> {
    let conn = pool.get().expect("Failed to get connection");
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )?;
    Ok(())
}

pub fn insert_book(pool: &DbPool, book: &Book) -> rusqlite::Result<()> {
    let conn = pool.get().expect("Failed to get connection");
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(())
}

pub fn get_all_books(pool: &DbPool, author_filter: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let conn = pool.get().expect("Failed to get connection");
    let (query, filter) = match author_filter {
        Some(a) => (
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?1",
            format!("%{}%", a),
        ),
        None => (
            "SELECT id, title, author, year, isbn FROM books",
            String::new(),
        ),
    };

    let mut stmt = conn.prepare(query)?;
    let rows = if author_filter.is_some() {
        stmt.query_map(params![filter], row_to_book)?
            .collect::<rusqlite::Result<Vec<Book>>>()?
    } else {
        stmt.query_map([], row_to_book)?
            .collect::<rusqlite::Result<Vec<Book>>>()?
    };
    Ok(rows)
}

pub fn get_book_by_id(pool: &DbPool, id: &str) -> rusqlite::Result<Option<Book>> {
    let conn = pool.get().expect("Failed to get connection");
    let mut stmt =
        conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query_map(params![id], row_to_book)?;
    Ok(rows.next().transpose()?)
}

pub fn update_book_in_db(pool: &DbPool, book: &Book) -> rusqlite::Result<usize> {
    let conn = pool.get().expect("Failed to get connection");
    let count = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, book.id],
    )?;
    Ok(count)
}

pub fn delete_book_from_db(pool: &DbPool, id: &str) -> rusqlite::Result<usize> {
    let conn = pool.get().expect("Failed to get connection");
    let count = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(count)
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

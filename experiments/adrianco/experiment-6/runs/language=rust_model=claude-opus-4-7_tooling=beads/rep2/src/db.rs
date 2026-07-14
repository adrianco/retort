use std::sync::{Arc, Mutex};

use rusqlite::{params, Connection, OptionalExtension};

use crate::error::AppError;
use crate::models::Book;

pub type Db = Arc<Mutex<Connection>>;

pub fn open(path: &str) -> Result<Db, AppError> {
    let conn = Connection::open(path)?;
    init_schema(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn open_in_memory() -> Result<Db, AppError> {
    let conn = Connection::open_in_memory()?;
    init_schema(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

fn init_schema(conn: &Connection) -> Result<(), AppError> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(())
}

fn lock(db: &Db) -> Result<std::sync::MutexGuard<'_, Connection>, AppError> {
    db.lock()
        .map_err(|e| AppError::Internal(format!("mutex poisoned: {e}")))
}

pub fn insert(db: &Db, book: &Book) -> Result<(), AppError> {
    let conn = lock(db)?;
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(())
}

pub fn list(db: &Db, author: Option<&str>) -> Result<Vec<Book>, AppError> {
    let conn = lock(db)?;
    let mut books = Vec::new();
    match author {
        Some(a) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY title",
            )?;
            for row in stmt.query_map(params![a], row_to_book)? {
                books.push(row?);
            }
        }
        None => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books ORDER BY title",
            )?;
            for row in stmt.query_map([], row_to_book)? {
                books.push(row?);
            }
        }
    }
    Ok(books)
}

pub fn get(db: &Db, id: &str) -> Result<Option<Book>, AppError> {
    let conn = lock(db)?;
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .optional()?;
    Ok(book)
}

pub fn update(db: &Db, book: &Book) -> Result<bool, AppError> {
    let conn = lock(db)?;
    let n = conn.execute(
        "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(n > 0)
}

pub fn delete(db: &Db, id: &str) -> Result<bool, AppError> {
    let conn = lock(db)?;
    let n = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(n > 0)
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

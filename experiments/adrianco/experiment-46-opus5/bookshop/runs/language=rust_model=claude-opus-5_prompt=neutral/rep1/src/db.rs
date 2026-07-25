use rusqlite::{Connection, OptionalExtension, Row, params};

use crate::error::ApiError;
use crate::models::{Book, ValidBook};

/// Create the schema if it is not there yet. Safe to call on every start-up.
pub fn init_schema(conn: &Connection) -> Result<(), ApiError> {
    conn.execute_batch(
        "PRAGMA foreign_keys = ON;
         CREATE TABLE IF NOT EXISTS books (
             id     INTEGER PRIMARY KEY AUTOINCREMENT,
             title  TEXT    NOT NULL,
             author TEXT    NOT NULL,
             year   INTEGER,
             isbn   TEXT
         );
         CREATE INDEX IF NOT EXISTS books_author_idx ON books (author COLLATE NOCASE);",
    )?;
    Ok(())
}

fn row_to_book(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get("id")?,
        title: row.get("title")?,
        author: row.get("author")?,
        year: row.get("year")?,
        isbn: row.get("isbn")?,
    })
}

pub fn insert(conn: &Connection, book: &ValidBook) -> Result<Book, ApiError> {
    let id = conn.query_row(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4) RETURNING id",
        params![book.title, book.author, book.year, book.isbn],
        |row| row.get::<_, i64>(0),
    )?;

    Ok(Book {
        id,
        title: book.title.clone(),
        author: book.author.clone(),
        year: book.year,
        isbn: book.isbn.clone(),
    })
}

/// List books, newest first. `author` filters on an exact but case-insensitive
/// match so `?author=frank herbert` finds "Frank Herbert".
pub fn list(conn: &Connection, author: Option<&str>) -> Result<Vec<Book>, ApiError> {
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books
         WHERE ?1 IS NULL OR author = ?1 COLLATE NOCASE
         ORDER BY id DESC",
    )?;
    let books = stmt
        .query_map(params![author.map(str::trim)], row_to_book)?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    Ok(books)
}

pub fn get(conn: &Connection, id: i64) -> Result<Option<Book>, ApiError> {
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .optional()?;
    Ok(book)
}

/// Replace a book wholesale. Returns `None` when no row has that id.
pub fn update(conn: &Connection, id: i64, book: &ValidBook) -> Result<Option<Book>, ApiError> {
    let affected = conn.execute(
        "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
        params![id, book.title, book.author, book.year, book.isbn],
    )?;

    if affected == 0 {
        return Ok(None);
    }

    Ok(Some(Book {
        id,
        title: book.title.clone(),
        author: book.author.clone(),
        year: book.year,
        isbn: book.isbn.clone(),
    }))
}

/// Returns whether a row was actually removed, so the handler can 404.
pub fn delete(conn: &Connection, id: i64) -> Result<bool, ApiError> {
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(affected > 0)
}

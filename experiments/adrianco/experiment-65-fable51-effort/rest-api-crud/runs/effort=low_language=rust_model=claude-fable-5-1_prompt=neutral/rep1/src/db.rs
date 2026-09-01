//! SQLite persistence for books.

use rusqlite::{params, Connection, OptionalExtension, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Open a connection (use ":memory:" for an in-memory database) and create the schema.
pub fn open(path: &str) -> Result<Connection> {
    let conn = Connection::open(path)?;
    init(&conn)?;
    Ok(conn)
}

pub fn init(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )
}

pub fn insert(
    conn: &Connection,
    title: &str,
    author: &str,
    year: Option<i64>,
    isbn: Option<&str>,
) -> Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, year, isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: title.to_string(),
        author: author.to_string(),
        year,
        isbn: isbn.map(str::to_string),
    })
}

fn row_to_book(row: &rusqlite::Row<'_>) -> Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

pub fn list(conn: &Connection, author: Option<&str>) -> Result<Vec<Book>> {
    match author {
        Some(a) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map(params![a], row_to_book)?.collect();
            rows
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?.collect();
            rows
        }
    }
}

pub fn get(conn: &Connection, id: i64) -> Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}

/// Update a book; returns Ok(None) if no such id.
pub fn update(
    conn: &Connection,
    id: i64,
    title: &str,
    author: &str,
    year: Option<i64>,
    isbn: Option<&str>,
) -> Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;
    if changed == 0 {
        return Ok(None);
    }
    get(conn, id)
}

/// Delete a book; returns true if a row was removed.
pub fn delete(conn: &Connection, id: i64) -> Result<bool> {
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(changed > 0)
}

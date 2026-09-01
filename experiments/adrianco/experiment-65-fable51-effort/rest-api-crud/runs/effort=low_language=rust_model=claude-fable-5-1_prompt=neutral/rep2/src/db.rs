use rusqlite::{params, Connection, OptionalExtension, Result};

use crate::models::{Book, ValidBook};

/// Open a connection (file path or ":memory:") and ensure the schema exists.
pub fn open(path: &str) -> Result<Connection> {
    let conn = Connection::open(path)?;
    init_schema(&conn)?;
    Ok(conn)
}

/// Open an in-memory database with the schema applied.
pub fn open_in_memory() -> Result<Connection> {
    let conn = Connection::open_in_memory()?;
    init_schema(&conn)?;
    Ok(conn)
}

pub fn init_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
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

pub fn insert(conn: &Connection, b: &ValidBook) -> Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![b.title, b.author, b.year, b.isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: b.title.clone(),
        author: b.author.clone(),
        year: b.year,
        isbn: b.isbn.clone(),
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

/// Returns `Ok(None)` if no row with that id exists.
pub fn update(conn: &Connection, id: i64, b: &ValidBook) -> Result<Option<Book>> {
    let n = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![b.title, b.author, b.year, b.isbn, id],
    )?;
    if n == 0 {
        return Ok(None);
    }
    Ok(Some(Book {
        id,
        title: b.title.clone(),
        author: b.author.clone(),
        year: b.year,
        isbn: b.isbn.clone(),
    }))
}

/// Returns `true` if a row was deleted.
pub fn delete(conn: &Connection, id: i64) -> Result<bool> {
    let n = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(n > 0)
}

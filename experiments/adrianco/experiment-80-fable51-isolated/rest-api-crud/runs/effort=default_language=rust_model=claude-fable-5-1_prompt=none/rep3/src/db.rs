use rusqlite::{params, Connection, OptionalExtension, Row};
use serde::Serialize;

#[derive(Debug, Serialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Validated book fields, ready to be written.
#[derive(Debug)]
pub struct BookFields {
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

const COLUMNS: &str = "id, title, author, year, isbn";

/// Opens (or creates) the database at `path` and ensures the schema exists.
pub fn open(path: &str) -> rusqlite::Result<Connection> {
    init(Connection::open(path)?)
}

/// Opens a fresh in-memory database, used by tests.
pub fn open_in_memory() -> rusqlite::Result<Connection> {
    init(Connection::open_in_memory()?)
}

fn init(conn: Connection) -> rusqlite::Result<Connection> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);",
    )?;
    Ok(conn)
}

fn from_row(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

pub fn insert(conn: &Connection, f: &BookFields) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![f.title, f.author, f.year, f.isbn],
    )?;
    Ok(Book {
        id: conn.last_insert_rowid(),
        title: f.title.clone(),
        author: f.author.clone(),
        year: f.year,
        isbn: f.isbn.clone(),
    })
}

/// Lists books ordered by id; `author` filters by case-insensitive exact match.
pub fn list(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    match author {
        Some(author) => conn
            .prepare(&format!(
                "SELECT {COLUMNS} FROM books WHERE author = ?1 COLLATE NOCASE ORDER BY id"
            ))?
            .query_map([author], from_row)?
            .collect(),
        None => conn
            .prepare(&format!("SELECT {COLUMNS} FROM books ORDER BY id"))?
            .query_map([], from_row)?
            .collect(),
    }
}

pub fn get(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        &format!("SELECT {COLUMNS} FROM books WHERE id = ?1"),
        [id],
        from_row,
    )
    .optional()
}

/// Replaces the book's fields. Returns `None` if no such book exists.
pub fn update(conn: &Connection, id: i64, f: &BookFields) -> rusqlite::Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![f.title, f.author, f.year, f.isbn, id],
    )?;
    Ok((changed > 0).then(|| Book {
        id,
        title: f.title.clone(),
        author: f.author.clone(),
        year: f.year,
        isbn: f.isbn.clone(),
    }))
}

/// Returns whether a book was deleted.
pub fn delete(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    Ok(conn.execute("DELETE FROM books WHERE id = ?1", [id])? > 0)
}

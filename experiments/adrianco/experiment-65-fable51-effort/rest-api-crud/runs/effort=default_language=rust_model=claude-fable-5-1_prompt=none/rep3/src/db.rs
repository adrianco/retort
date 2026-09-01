//! SQLite persistence layer.

use std::sync::{Arc, Mutex};

use rusqlite::{params, Connection, OptionalExtension};

use crate::models::{Book, ValidBook};

/// Thread-safe handle to the SQLite database shared across request handlers.
#[derive(Clone)]
pub struct Db {
    conn: Arc<Mutex<Connection>>,
}

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
";

impl Db {
    /// Open (or create) the database at `path` and ensure the schema exists.
    /// Use `":memory:"` for an ephemeral in-memory database.
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA foreign_keys = ON;")?;
        conn.execute_batch(SCHEMA)?;
        Ok(Db {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    /// Open a fresh in-memory database (convenient for tests).
    pub fn in_memory() -> rusqlite::Result<Self> {
        Self::open(":memory:")
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, Connection> {
        // A poisoned mutex only happens if a previous holder panicked; the
        // connection itself is still usable, so recover the guard.
        self.conn.lock().unwrap_or_else(|e| e.into_inner())
    }

    pub fn insert(&self, book: &ValidBook) -> rusqlite::Result<Book> {
        let conn = self.lock();
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            params![book.title, book.author, book.year, book.isbn],
        )?;
        let id = conn.last_insert_rowid();
        Ok(Book {
            id,
            title: book.title.clone(),
            author: book.author.clone(),
            year: book.year,
            isbn: book.isbn.clone(),
        })
    }

    pub fn list(&self, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
        let conn = self.lock();
        let mut books = Vec::new();
        match author {
            Some(a) => {
                let mut stmt = conn.prepare(
                    "SELECT id, title, author, year, isbn FROM books \
                     WHERE author = ?1 COLLATE NOCASE ORDER BY id",
                )?;
                let rows = stmt.query_map(params![a], row_to_book)?;
                for r in rows {
                    books.push(r?);
                }
            }
            None => {
                let mut stmt =
                    conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
                let rows = stmt.query_map([], row_to_book)?;
                for r in rows {
                    books.push(r?);
                }
            }
        }
        Ok(books)
    }

    pub fn get(&self, id: i64) -> rusqlite::Result<Option<Book>> {
        let conn = self.lock();
        conn.query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            params![id],
            row_to_book,
        )
        .optional()
    }

    /// Replace all fields of the book with `id`. Returns `None` if it doesn't exist.
    pub fn update(&self, id: i64, book: &ValidBook) -> rusqlite::Result<Option<Book>> {
        let conn = self.lock();
        let changed = conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![book.title, book.author, book.year, book.isbn, id],
        )?;
        if changed == 0 {
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

    /// Delete the book with `id`. Returns `true` if a row was removed.
    pub fn delete(&self, id: i64) -> rusqlite::Result<bool> {
        let conn = self.lock();
        let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        Ok(changed > 0)
    }

    /// Cheap liveness probe used by the health endpoint.
    pub fn ping(&self) -> rusqlite::Result<()> {
        let conn = self.lock();
        conn.query_row("SELECT 1", [], |_| Ok(()))
    }
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

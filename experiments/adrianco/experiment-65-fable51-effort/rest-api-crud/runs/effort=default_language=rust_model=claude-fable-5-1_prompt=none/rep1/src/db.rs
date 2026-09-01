//! SQLite persistence layer.

use std::sync::{Arc, Mutex};

use rusqlite::{params, Connection, OptionalExtension, Row};

use crate::error::ApiError;
use crate::models::{Book, ValidBook};

/// Thread-safe handle to the SQLite database.
#[derive(Clone)]
pub struct Db {
    conn: Arc<Mutex<Connection>>,
}

impl Db {
    /// Open (or create) a database at `path`. Use `":memory:"` for an in-memory DB.
    pub fn open(path: &str) -> Result<Self, ApiError> {
        let conn = Connection::open(path)?;
        let db = Db {
            conn: Arc::new(Mutex::new(conn)),
        };
        db.migrate()?;
        Ok(db)
    }

    /// Open a fresh in-memory database (used by tests).
    pub fn in_memory() -> Result<Self, ApiError> {
        Self::open(":memory:")
    }

    fn migrate(&self) -> Result<(), ApiError> {
        let conn = self.lock()?;
        conn.execute_batch(
            "PRAGMA foreign_keys = ON;
             CREATE TABLE IF NOT EXISTS books (
                 id     INTEGER PRIMARY KEY AUTOINCREMENT,
                 title  TEXT NOT NULL,
                 author TEXT NOT NULL,
                 year   INTEGER,
                 isbn   TEXT
             );
             CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);",
        )?;
        Ok(())
    }

    fn lock(&self) -> Result<std::sync::MutexGuard<'_, Connection>, ApiError> {
        self.conn
            .lock()
            .map_err(|_| ApiError::Internal("database mutex poisoned".into()))
    }

    pub fn create(&self, book: &ValidBook) -> Result<Book, ApiError> {
        let conn = self.lock()?;
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

    pub fn list(&self, author: Option<&str>) -> Result<Vec<Book>, ApiError> {
        let conn = self.lock()?;
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books
             WHERE ?1 IS NULL OR author = ?1 COLLATE NOCASE
             ORDER BY id",
        )?;
        let books = stmt
            .query_map(params![author], row_to_book)?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(books)
    }

    pub fn get(&self, id: i64) -> Result<Option<Book>, ApiError> {
        let conn = self.lock()?;
        let book = conn
            .query_row(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
                params![id],
                row_to_book,
            )
            .optional()?;
        Ok(book)
    }

    /// Full replacement of a book's fields. Returns `None` if the id does not exist.
    pub fn update(&self, id: i64, book: &ValidBook) -> Result<Option<Book>, ApiError> {
        let conn = self.lock()?;
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

    /// Returns `true` if a row was deleted.
    pub fn delete(&self, id: i64) -> Result<bool, ApiError> {
        let conn = self.lock()?;
        let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        Ok(changed > 0)
    }

    /// Lightweight connectivity check for the health endpoint.
    pub fn ping(&self) -> Result<(), ApiError> {
        let conn = self.lock()?;
        conn.query_row("SELECT 1", [], |_| Ok(()))?;
        Ok(())
    }
}

fn row_to_book(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(title: &str, author: &str) -> ValidBook {
        ValidBook {
            title: title.into(),
            author: author.into(),
            year: Some(2000),
            isbn: None,
        }
    }

    #[test]
    fn crud_roundtrip() {
        let db = Db::in_memory().unwrap();
        let created = db.create(&sample("A", "X")).unwrap();
        assert_eq!(created.id, 1);

        let fetched = db.get(1).unwrap().unwrap();
        assert_eq!(fetched, created);

        let updated = db.update(1, &sample("B", "Y")).unwrap().unwrap();
        assert_eq!(updated.title, "B");
        assert_eq!(db.get(1).unwrap().unwrap().author, "Y");

        assert!(db.delete(1).unwrap());
        assert!(!db.delete(1).unwrap());
        assert!(db.get(1).unwrap().is_none());
    }

    #[test]
    fn list_filters_by_author_case_insensitively() {
        let db = Db::in_memory().unwrap();
        db.create(&sample("A", "Ursula K. Le Guin")).unwrap();
        db.create(&sample("B", "Frank Herbert")).unwrap();
        db.create(&sample("C", "ursula k. le guin")).unwrap();

        assert_eq!(db.list(None).unwrap().len(), 3);
        let filtered = db.list(Some("Ursula K. Le Guin")).unwrap();
        assert_eq!(filtered.len(), 2);
        assert!(filtered.iter().all(|b| b.title == "A" || b.title == "C"));
        assert!(db.list(Some("Nobody")).unwrap().is_empty());
    }

    #[test]
    fn update_missing_returns_none() {
        let db = Db::in_memory().unwrap();
        assert!(db.update(42, &sample("A", "X")).unwrap().is_none());
    }
}

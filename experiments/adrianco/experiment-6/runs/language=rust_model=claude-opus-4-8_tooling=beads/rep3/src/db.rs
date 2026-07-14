use std::sync::{Arc, Mutex};

use rusqlite::Connection;

use crate::models::{Book, ValidatedBook};

/// Thread-safe handle to the SQLite database.
#[derive(Clone)]
pub struct Db {
    conn: Arc<Mutex<Connection>>,
}

impl Db {
    /// Open a database at the given path (use ":memory:" for an in-memory DB)
    /// and ensure the schema exists.
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
        let db = Db {
            conn: Arc::new(Mutex::new(conn)),
        };
        db.init_schema()?;
        Ok(db)
    }

    fn init_schema(&self) -> rusqlite::Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            )",
            [],
        )?;
        Ok(())
    }

    pub fn create(&self, b: &ValidatedBook) -> rusqlite::Result<Book> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params![b.title, b.author, b.year, b.isbn],
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

    pub fn list(&self, author_filter: Option<&str>) -> rusqlite::Result<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut books = Vec::new();
        match author_filter {
            Some(author) => {
                let mut stmt = conn.prepare(
                    "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
                )?;
                let rows = stmt.query_map([author], map_book)?;
                for row in rows {
                    books.push(row?);
                }
            }
            None => {
                let mut stmt = conn
                    .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
                let rows = stmt.query_map([], map_book)?;
                for row in rows {
                    books.push(row?);
                }
            }
        }
        Ok(books)
    }

    pub fn get(&self, id: i64) -> rusqlite::Result<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
        let mut rows = stmt.query_map([id], map_book)?;
        match rows.next() {
            Some(row) => Ok(Some(row?)),
            None => Ok(None),
        }
    }

    /// Replace a book's fields. Returns the updated book, or None if no such id.
    pub fn update(&self, id: i64, b: &ValidatedBook) -> rusqlite::Result<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let affected = conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            rusqlite::params![b.title, b.author, b.year, b.isbn, id],
        )?;
        if affected == 0 {
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

    /// Delete a book by id. Returns true if a row was removed.
    pub fn delete(&self, id: i64) -> rusqlite::Result<bool> {
        let conn = self.conn.lock().unwrap();
        let affected = conn.execute("DELETE FROM books WHERE id = ?1", [id])?;
        Ok(affected > 0)
    }
}

fn map_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

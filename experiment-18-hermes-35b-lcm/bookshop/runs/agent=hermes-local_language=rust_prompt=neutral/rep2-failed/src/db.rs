use rusqlite::{Connection, Result, params};
use rusqlite::OptionalExtension;
use crate::models::Book;
use std::sync::{Arc, Mutex};

pub struct DbState {
    pub conn: Arc<Mutex<Connection>>,
}

impl Clone for DbState {
    fn clone(&self) -> Self {
        DbState {
            conn: Arc::clone(&self.conn),
        }
    }
}

impl DbState {
    pub fn new() -> Result<Self, rusqlite::Error> {
        let conn = Connection::open_in_memory()?;
        DbState::init_db(&conn)?;
        Ok(DbState {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    fn init_db(db: &Connection) -> Result<(), rusqlite::Error> {
        db.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT UNIQUE
            )",
        )?;
        Ok(())
    }

    pub fn create_book(&self, title: &str, author: &str, year: Option<i32>, isbn: &Option<String>) -> Result<Book> {
        let conn = self.conn.lock().unwrap();
        let isbn_ref = isbn.as_deref().unwrap_or("");

        let mut stmt = conn.prepare(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)"
        )?;

        let id = stmt.insert(params![title, author, year, isbn_ref])?;

        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1"
        )?;

        Ok(stmt.query_row(params![id], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })?)
    }

    pub fn list_books(&self) -> Result<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;

        let books = stmt.query_map([], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })?;

        books.collect()
    }

    pub fn list_books_by_author(&self, author: &str) -> Result<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id"
        )?;

        let books = stmt.query_map(params![author], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })?;

        books.collect()
    }

    pub fn get_book(&self, id: i64) -> Result<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1"
        )?;

        stmt.query_row(params![id], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        }).optional()
    }

    pub fn update_book(
        &self,
        id: i64,
        title: &str,
        author: &str,
        year: Option<i32>,
        isbn: &Option<String>,
    ) -> Result<Option<Book>> {
        let mut conn = self.conn.lock().unwrap();

        let book_exists: i64 = conn.query_row(
            "SELECT COUNT(*) FROM books WHERE id = ?1",
            params![id],
            |row| row.get(0),
        )?;

        if book_exists == 0 {
            return Ok(None);
        }

        let isbn_ref = isbn.as_deref().unwrap_or("");

        conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, year, isbn_ref, id],
        )?;

        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1"
        )?;

        Ok(Some(stmt.query_row(params![id], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })?))
    }

    pub fn delete_book(&self, id: i64) -> Result<bool> {
        let conn = self.conn.lock().unwrap();
        let rows = conn.execute(
            "DELETE FROM books WHERE id = ?1",
            params![id],
        )?;
        Ok(rows > 0)
    }
}

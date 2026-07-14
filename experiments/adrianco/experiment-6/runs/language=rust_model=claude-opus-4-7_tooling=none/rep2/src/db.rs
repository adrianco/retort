use rusqlite::{params, Connection, Result as SqlResult};
use std::sync::Mutex;

use crate::models::Book;

pub struct Db {
    pub conn: Mutex<Connection>,
}

impl Db {
    pub fn new(path: &str) -> SqlResult<Self> {
        let conn = if path == ":memory:" {
            Connection::open_in_memory()?
        } else {
            Connection::open(path)?
        };
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
        Ok(Self {
            conn: Mutex::new(conn),
        })
    }

    pub fn insert(&self, book: &Book) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![book.id, book.title, book.author, book.year, book.isbn],
        )?;
        Ok(())
    }

    pub fn list(&self, author_filter: Option<&str>) -> SqlResult<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let map_row = |row: &rusqlite::Row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        };
        let mut books = Vec::new();
        match author_filter {
            Some(a) => {
                let mut stmt = conn.prepare(
                    "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY title",
                )?;
                for b in stmt.query_map(params![a], map_row)? {
                    books.push(b?);
                }
            }
            None => {
                let mut stmt = conn.prepare(
                    "SELECT id, title, author, year, isbn FROM books ORDER BY title",
                )?;
                for b in stmt.query_map([], map_row)? {
                    books.push(b?);
                }
            }
        }
        Ok(books)
    }

    pub fn get(&self, id: &str) -> SqlResult<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt =
            conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
        let mut rows = stmt.query(params![id])?;
        if let Some(row) = rows.next()? {
            Ok(Some(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            }))
        } else {
            Ok(None)
        }
    }

    pub fn update(&self, book: &Book) -> SqlResult<usize> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE books SET title = ?2, author = ?3, year = ?4, isbn = ?5 WHERE id = ?1",
            params![book.id, book.title, book.author, book.year, book.isbn],
        )
    }

    pub fn delete(&self, id: &str) -> SqlResult<usize> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM books WHERE id = ?1", params![id])
    }
}

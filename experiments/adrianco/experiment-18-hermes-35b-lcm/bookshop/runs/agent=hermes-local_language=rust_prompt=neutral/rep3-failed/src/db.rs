use rusqlite::{Connection, Result, params};
use uuid::Uuid;

use crate::models::{Book, CreateBookRequest, UpdateBookRequest};

pub struct Database {
    conn: std::sync::Mutex<Connection>,
}

impl Database {
    pub fn new(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            );",
        )?;
        Ok(Database {
            conn: std::sync::Mutex::new(conn),
        })
    }

    fn row_to_book(&self, row: &rusqlite::Row) -> Result<Book> {
        Ok(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    }

    pub fn create_book(&self, req: &CreateBookRequest) -> Result<Book> {
        let id = Uuid::new_v4().to_string();
        let title = req.title.as_ref().unwrap().clone();
        let author = req.author.as_ref().unwrap().clone();
        let year = req.year;
        let isbn = req.isbn.clone();

        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![&id, &title, &author, year, &isbn],
        )?;

        Ok(Book { id, title, author, year, isbn })
    }

    pub fn list_books(&self, author: Option<&str>) -> Result<Vec<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut books = Vec::new();

        if let Some(a) = author {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?1",
            )?;
            let mut rows = stmt.query(params![format!("%{}%", a)])?;
            while let Some(row) = rows.next()? {
                books.push(self.row_to_book(row)?);
            }
        } else {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books",
            )?;
            let mut rows = stmt.query(params![])?;
            while let Some(row) = rows.next()? {
                books.push(self.row_to_book(row)?);
            }
        }

        Ok(books)
    }

    pub fn get_book(&self, id: &str) -> Result<Option<Book>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        )?;
        let mut rows = stmt.query(params![id])?;
        if let Some(row) = rows.next()? {
            Ok(Some(self.row_to_book(row)?))
        } else {
            Ok(None)
        }
    }

    pub fn update_book(&self, id: &str, req: &UpdateBookRequest) -> Result<Option<Book>> {
        let conn = self.conn.lock().unwrap();

        let current = match self.get_book(id)? {
            Some(b) => b,
            None => return Ok(None),
        };

        let title = req.title.clone().or_else(|| Some(current.title.clone())).unwrap();
        let author = req.author.clone().or_else(|| Some(current.author.clone())).unwrap();
        let year = req.year.or(current.year);
        let isbn = req.isbn.clone().or(current.isbn);

        conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![&title, &author, year, &isbn, id],
        )?;

        Ok(Some(Book {
            id: id.to_string(),
            title,
            author,
            year,
            isbn,
        }))
    }

    pub fn delete_book(&self, id: &str) -> Result<bool> {
        let conn = self.conn.lock().unwrap();
        let count = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        Ok(count > 0)
    }
}

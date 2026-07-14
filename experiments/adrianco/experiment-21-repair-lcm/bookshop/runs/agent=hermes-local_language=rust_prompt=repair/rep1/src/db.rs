use rusqlite::{Connection, Result as SqliteResult, params};
use uuid::Uuid;

use crate::models::{Book, CreateBookRequest, UpdateBookRequest};

pub struct Database {
    conn: Connection,
}

impl Clone for Database {
    fn clone(&self) -> Self {
        // Re-open connection for clone
        // Note: rusqlite Connection isn't cloneable, so we use a new connection
        // For simplicity in this context, we won't derive Clone on Database
        // and handle it differently
        unimplemented!("Database clone not supported")
    }
}

impl Database {
    pub fn new(path: &str) -> SqliteResult<Self> {
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
        Ok(Database { conn })
    }

    pub fn create_book(&self, req: &CreateBookRequest) -> SqliteResult<Book> {
        let id = Uuid::new_v4().to_string();
        let title = req.title.as_ref().unwrap().clone();
        let author = req.author.as_ref().unwrap().clone();
        let year = req.year;
        let isbn = req.isbn.clone();

        self.conn.execute(
            "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![&id, &title, &author, year, &isbn],
        )?;

        Ok(Book {
            id,
            title,
            author,
            year,
            isbn,
        })
    }

    pub fn list_books(&self, author_filter: Option<&str>) -> SqliteResult<Vec<Book>> {
        let books = if let Some(author) = author_filter {
            let mut stmt = self.conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
            )?;
            let rows = stmt.query_map(params![author], |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            })?;
            rows.collect::<SqliteResult<Vec<Book>>>()?
        } else {
            let mut stmt = self.conn.prepare(
                "SELECT id, title, author, year, isbn FROM books",
            )?;
            let rows = stmt.query_map(params![], |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            })?;
            rows.collect::<SqliteResult<Vec<Book>>>()?
        };

        Ok(books)
    }

    pub fn get_book(&self, id: &str) -> SqliteResult<Option<Book>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        )?;

        let mut rows = stmt.query(params![id])?;
        let row = rows.next()?;

        match row {
            Some(row) => Ok(Some(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })),
            None => Ok(None),
        }
    }

    pub fn update_book(&self, id: &str, req: &UpdateBookRequest) -> Option<Book> {
        let existing = match self.get_book(id) {
            Ok(Some(book)) => book,
            _ => return None,
        };

        let title = req.title.as_ref().map(|s| s.as_str()).unwrap_or(&existing.title);
        let author = req.author.as_ref().map(|s| s.as_str()).unwrap_or(&existing.author);
        let year = req.year.or(existing.year);
        let isbn = req.isbn.clone().or(existing.isbn);

        if let Err(_) = self.conn.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, year, &isbn, id],
        ) {
            return None;
        };

        Some(Book {
            id: id.to_string(),
            title: title.to_string(),
            author: author.to_string(),
            year,
            isbn,
        })
    }

    pub fn delete_book(&self, id: &str) -> SqliteResult<bool> {
        let rows = self.conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
        Ok(rows > 0)
    }
}

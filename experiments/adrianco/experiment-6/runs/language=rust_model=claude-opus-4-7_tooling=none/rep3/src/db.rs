use rusqlite::{params, Connection, Result as SqlResult};
use std::sync::{Arc, Mutex};

use crate::models::Book;

pub type Db = Arc<Mutex<Connection>>;

pub fn init(path: &str) -> SqlResult<Db> {
    let conn = if path == ":memory:" {
        Connection::open_in_memory()?
    } else {
        Connection::open(path)?
    };
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id    TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year  INTEGER,
            isbn  TEXT
        )",
        [],
    )?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn insert_book(db: &Db, book: &Book) -> SqlResult<()> {
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(())
}

pub fn get_book(db: &Db, id: &str) -> SqlResult<Option<Book>> {
    let conn = db.lock().unwrap();
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

pub fn list_books(db: &Db, author_filter: Option<&str>) -> SqlResult<Vec<Book>> {
    let conn = db.lock().unwrap();
    let map_row = |row: &rusqlite::Row| -> SqlResult<Book> {
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
            let rows = stmt.query_map(params![a], map_row)?;
            for r in rows {
                books.push(r?);
            }
        }
        None => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY title")?;
            let rows = stmt.query_map([], map_row)?;
            for r in rows {
                books.push(r?);
            }
        }
    }
    Ok(books)
}

pub fn update_book(db: &Db, book: &Book) -> SqlResult<usize> {
    let conn = db.lock().unwrap();
    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, book.id],
    )
}

pub fn delete_book(db: &Db, id: &str) -> SqlResult<usize> {
    let conn = db.lock().unwrap();
    conn.execute("DELETE FROM books WHERE id = ?1", params![id])
}

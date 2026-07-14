use rusqlite::{Connection, Result as SqlResult, params};
use std::sync::{Arc, Mutex};
use crate::models::{Book, CreateBook, UpdateBook};

pub type DbPool = Arc<Mutex<Connection>>;

pub fn init_db(path: &str) -> SqlResult<DbPool> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id      TEXT PRIMARY KEY,
            title   TEXT NOT NULL,
            author  TEXT NOT NULL,
            year    INTEGER,
            isbn    TEXT
        );",
    )?;
    Ok(Arc::new(Mutex::new(conn)))
}

pub fn create_book(pool: &DbPool, id: &str, book: &CreateBook) -> SqlResult<Book> {
    let conn = pool.lock().unwrap();
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(Book {
        id: id.to_string(),
        title: book.title.clone().unwrap_or_default(),
        author: book.author.clone().unwrap_or_default(),
        year: book.year,
        isbn: book.isbn.clone(),
    })
}

pub fn list_books(pool: &DbPool, author_filter: Option<&str>) -> SqlResult<Vec<Book>> {
    let conn = pool.lock().unwrap();
    let (sql, param) = if let Some(author) = author_filter {
        (
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
            Some(author.to_string()),
        )
    } else {
        ("SELECT id, title, author, year, isbn FROM books", None)
    };

    let mut stmt = conn.prepare(sql)?;
    let books = if let Some(p) = param {
        stmt.query_map(params![p], map_row)?.collect::<SqlResult<Vec<_>>>()?
    } else {
        stmt.query_map([], map_row)?.collect::<SqlResult<Vec<_>>>()?
    };
    Ok(books)
}

pub fn get_book(pool: &DbPool, id: &str) -> SqlResult<Option<Book>> {
    let conn = pool.lock().unwrap();
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
    )?;
    let mut rows = stmt.query_map(params![id], map_row)?;
    Ok(rows.next().transpose()?)
}

pub fn update_book(pool: &DbPool, id: &str, update: &UpdateBook) -> SqlResult<Option<Book>> {
    let conn = pool.lock().unwrap();

    // Fetch existing
    let existing: Option<Book> = {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        )?;
        let mut rows = stmt.query_map(params![id], map_row)?;
        rows.next().transpose()?
    };

    let Some(existing) = existing else {
        return Ok(None);
    };

    let title = update.title.as_deref().unwrap_or(&existing.title);
    let author = update.author.as_deref().unwrap_or(&existing.author);
    let year = update.year.or(existing.year);
    let isbn = update.isbn.as_deref().or(existing.isbn.as_deref());

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;

    Ok(Some(Book {
        id: id.to_string(),
        title: title.to_string(),
        author: author.to_string(),
        year,
        isbn: isbn.map(String::from),
    }))
}

pub fn delete_book(pool: &DbPool, id: &str) -> SqlResult<bool> {
    let conn = pool.lock().unwrap();
    let count = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(count > 0)
}

fn map_row(row: &rusqlite::Row) -> SqlResult<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

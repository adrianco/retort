use crate::models::Book;
use rusqlite::{params, Connection, OptionalExtension, Result};

pub fn init_schema(conn: &Connection) -> Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT    NOT NULL,
            author  TEXT    NOT NULL,
            year    INTEGER,
            isbn    TEXT
        )",
        [],
    )?;
    Ok(())
}

pub fn insert_book(
    conn: &Connection,
    title: &str,
    author: &str,
    year: Option<i32>,
    isbn: Option<&str>,
) -> Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, year, isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: title.to_string(),
        author: author.to_string(),
        year,
        isbn: isbn.map(|s| s.to_string()),
    })
}

pub fn get_book(conn: &Connection, id: i64) -> Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}

pub fn list_books(conn: &Connection, author: Option<&str>) -> Result<Vec<Book>> {
    let mut books = Vec::new();
    match author {
        Some(a) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let rows = stmt.query_map(params![a], row_to_book)?;
            for r in rows {
                books.push(r?);
            }
        }
        None => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            for r in rows {
                books.push(r?);
            }
        }
    }
    Ok(books)
}

pub fn update_book(
    conn: &Connection,
    id: i64,
    title: &str,
    author: &str,
    year: Option<i32>,
    isbn: Option<&str>,
) -> Result<Option<Book>> {
    let n = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;
    if n == 0 {
        return Ok(None);
    }
    get_book(conn, id)
}

pub fn delete_book(conn: &Connection, id: i64) -> Result<bool> {
    let n = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(n > 0)
}

fn row_to_book(row: &rusqlite::Row) -> Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

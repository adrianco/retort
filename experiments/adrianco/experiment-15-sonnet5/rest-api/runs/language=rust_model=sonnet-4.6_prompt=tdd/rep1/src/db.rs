use rusqlite::{Connection, Result, params};
use uuid::Uuid;
use crate::models::{Book, CreateBook, UpdateBook};

pub fn init_db(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )
}

pub fn create_book(conn: &Connection, input: &CreateBook) -> Result<Book> {
    let id = Uuid::new_v4().to_string();
    let title = input.title.as_deref().unwrap_or("");
    let author = input.author.as_deref().unwrap_or("");
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![id, title, author, input.year, input.isbn],
    )?;
    Ok(Book {
        id,
        title: title.to_string(),
        author: author.to_string(),
        year: input.year,
        isbn: input.isbn.clone(),
    })
}

pub fn list_books(conn: &Connection, author_filter: Option<&str>) -> Result<Vec<Book>> {
    let (sql, param): (&str, Option<&str>) = match author_filter {
        Some(a) => (
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
            Some(a),
        ),
        None => (
            "SELECT id, title, author, year, isbn FROM books",
            None,
        ),
    };

    let mut stmt = conn.prepare(sql)?;
    let map_row = |row: &rusqlite::Row| {
        Ok(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    };

    let rows = if let Some(p) = param {
        stmt.query_map(params![p], map_row)?
    } else {
        stmt.query_map([], map_row)?
    };

    rows.collect()
}

pub fn get_book(conn: &Connection, id: &str) -> Result<Option<Book>> {
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
    )?;
    let mut rows = stmt.query_map(params![id], |row| {
        Ok(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    })?;
    Ok(rows.next().transpose()?)
}

pub fn update_book(conn: &Connection, id: &str, input: &UpdateBook) -> Result<Option<Book>> {
    let existing = get_book(conn, id)?;
    let Some(book) = existing else { return Ok(None) };

    let title = input.title.as_deref().unwrap_or(&book.title).to_string();
    let author = input.author.as_deref().unwrap_or(&book.author).to_string();
    let year = input.year.or(book.year);
    let isbn = input.isbn.clone().or(book.isbn);

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;

    Ok(Some(Book { id: id.to_string(), title, author, year, isbn }))
}

pub fn delete_book(conn: &Connection, id: &str) -> Result<bool> {
    let count = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(count > 0)
}

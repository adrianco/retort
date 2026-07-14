use crate::models::{Book, BookInput};
use rusqlite::{params, Connection};

pub fn init_db(conn: &Connection) {
    conn.pragma_update(None, "journal_mode", "MEMORY")
        .expect("failed to set journal_mode");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )",
        [],
    )
    .expect("failed to create books table");
}

pub fn insert_book(conn: &Connection, input: &BookInput) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: input.title.clone(),
        author: input.author.clone(),
        year: input.year,
        isbn: input.isbn.clone(),
    })
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

pub fn list_books(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut stmt = match author {
        Some(_) => conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?1",
        )?,
        None => conn.prepare("SELECT id, title, author, year, isbn FROM books")?,
    };

    let rows = match author {
        Some(a) => stmt.query_map(params![format!("%{a}%")], row_to_book)?,
        None => stmt.query_map([], row_to_book)?,
    };

    rows.collect()
}

pub fn get_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .map(Some)
    .or_else(|e| match e {
        rusqlite::Error::QueryReturnedNoRows => Ok(None),
        other => Err(other),
    })
}

pub fn update_book(
    conn: &Connection,
    id: i64,
    input: &BookInput,
) -> rusqlite::Result<Option<Book>> {
    let updated = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![input.title, input.author, input.year, input.isbn, id],
    )?;

    if updated == 0 {
        return Ok(None);
    }

    Ok(Some(Book {
        id,
        title: input.title.clone(),
        author: input.author.clone(),
        year: input.year,
        isbn: input.isbn.clone(),
    }))
}

pub fn delete_book(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let deleted = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(deleted > 0)
}

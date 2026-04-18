use rusqlite::{Connection, Result, params};
use crate::models::{Book, CreateBook, UpdateBook};

pub fn init_db(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id      TEXT PRIMARY KEY,
            title   TEXT NOT NULL,
            author  TEXT NOT NULL,
            year    INTEGER,
            isbn    TEXT
        );",
    )?;
    Ok(())
}

pub fn insert_book(conn: &Connection, book: &Book) -> Result<()> {
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![book.id, book.title, book.author, book.year, book.isbn],
    )?;
    Ok(())
}

pub fn list_books(conn: &Connection, author_filter: Option<&str>) -> Result<Vec<Book>> {
    if let Some(author) = author_filter {
        let mut stmt = conn.prepare(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1",
        )?;
        let books = stmt.query_map(params![author], row_to_book)?.collect::<Result<Vec<_>>>()?;
        Ok(books)
    } else {
        let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books")?;
        let books = stmt.query_map([], row_to_book)?.collect::<Result<Vec<_>>>()?;
        Ok(books)
    }
}

pub fn get_book(conn: &Connection, id: &str) -> Result<Option<Book>> {
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
    )?;
    let mut rows = stmt.query_map(params![id], row_to_book)?;
    Ok(rows.next().transpose()?)
}

pub fn update_book(conn: &Connection, id: &str, update: &UpdateBook) -> Result<Option<Book>> {
    let existing = get_book(conn, id)?;
    let Some(mut book) = existing else { return Ok(None) };

    if let Some(title) = &update.title {
        book.title = title.clone();
    }
    if let Some(author) = &update.author {
        book.author = author.clone();
    }
    if update.year.is_some() {
        book.year = update.year;
    }
    if update.isbn.is_some() {
        book.isbn = update.isbn.clone();
    }

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, id],
    )?;
    Ok(Some(book))
}

pub fn delete_book(conn: &Connection, id: &str) -> Result<bool> {
    let rows = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(rows > 0)
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

pub fn create_book_from_input(input: &CreateBook) -> Book {
    Book {
        id: uuid::Uuid::new_v4().to_string(),
        title: input.title.clone().unwrap_or_default(),
        author: input.author.clone().unwrap_or_default(),
        year: input.year,
        isbn: input.isbn.clone(),
    }
}

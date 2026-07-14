use crate::error::{ApiError, ApiResult};
use crate::models::Book;
use rusqlite::{params, Connection};

pub fn init(conn: &Connection) -> ApiResult<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(())
}

pub fn open(path: &str) -> ApiResult<Connection> {
    let conn = Connection::open(path).map_err(ApiError::Db)?;
    init(&conn)?;
    Ok(conn)
}

pub fn open_in_memory() -> ApiResult<Connection> {
    let conn = Connection::open_in_memory().map_err(ApiError::Db)?;
    init(&conn)?;
    Ok(conn)
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

pub fn insert(
    conn: &Connection,
    title: &str,
    author: &str,
    year: Option<i32>,
    isbn: Option<&str>,
) -> ApiResult<Book> {
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

pub fn get(conn: &Connection, id: i64) -> ApiResult<Book> {
    let mut stmt = conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query(params![id])?;
    match rows.next()? {
        Some(row) => Ok(row_to_book(row)?),
        None => Err(ApiError::NotFound),
    }
}

pub fn list(conn: &Connection, author_filter: Option<&str>) -> ApiResult<Vec<Book>> {
    match author_filter {
        Some(a) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            )?;
            let books = stmt
                .query_map(params![a], row_to_book)?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(books)
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let books = stmt
                .query_map([], row_to_book)?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(books)
        }
    }
}

pub fn update(
    conn: &Connection,
    id: i64,
    title: &str,
    author: &str,
    year: Option<i32>,
    isbn: Option<&str>,
) -> ApiResult<Book> {
    let affected = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![title, author, year, isbn, id],
    )?;
    if affected == 0 {
        return Err(ApiError::NotFound);
    }
    get(conn, id)
}

pub fn delete(conn: &Connection, id: i64) -> ApiResult<()> {
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    if affected == 0 {
        return Err(ApiError::NotFound);
    }
    Ok(())
}

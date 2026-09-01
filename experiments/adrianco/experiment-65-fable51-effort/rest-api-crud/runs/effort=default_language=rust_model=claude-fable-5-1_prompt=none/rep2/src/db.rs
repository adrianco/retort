//! SQLite persistence layer for books.

use rusqlite::{params, Connection, OptionalExtension, Row};

use crate::models::{Book, ValidBook};

/// Open a connection to `path` (or `:memory:`) and ensure the schema exists.
pub fn open(path: &str) -> rusqlite::Result<Connection> {
    let conn = if path == ":memory:" {
        Connection::open_in_memory()?
    } else {
        Connection::open(path)?
    };
    init_schema(&conn)?;
    Ok(conn)
}

/// Create the `books` table if it does not already exist.
pub fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "PRAGMA foreign_keys = ON;
         CREATE TABLE IF NOT EXISTS books (
             id     INTEGER PRIMARY KEY AUTOINCREMENT,
             title  TEXT    NOT NULL,
             author TEXT    NOT NULL,
             year   INTEGER,
             isbn   TEXT    UNIQUE
         );
         CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);",
    )
}

fn row_to_book(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get("id")?,
        title: row.get("title")?,
        author: row.get("author")?,
        year: row.get("year")?,
        isbn: row.get("isbn")?,
    })
}

pub fn insert(conn: &Connection, book: &ValidBook) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![book.title, book.author, book.year, book.isbn],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: book.title.clone(),
        author: book.author.clone(),
        year: book.year,
        isbn: book.isbn.clone(),
    })
}

/// List all books, optionally filtered by exact (case-insensitive) author.
pub fn list(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    match author {
        Some(a) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, author, year, isbn FROM books
                 WHERE author = ?1 COLLATE NOCASE ORDER BY id",
            )?;
            let rows = stmt.query_map(params![a], row_to_book)?;
            rows.collect()
        }
        None => {
            let mut stmt =
                conn.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")?;
            let rows = stmt.query_map([], row_to_book)?;
            rows.collect()
        }
    }
}

pub fn get(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        row_to_book,
    )
    .optional()
}

/// Replace all fields of the book with `id`. Returns `None` if it does not exist.
pub fn update(conn: &Connection, id: i64, book: &ValidBook) -> rusqlite::Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, id],
    )?;
    if changed == 0 {
        return Ok(None);
    }
    Ok(Some(Book {
        id,
        title: book.title.clone(),
        author: book.author.clone(),
        year: book.year,
        isbn: book.isbn.clone(),
    }))
}

/// Delete the book with `id`. Returns `true` if a row was removed.
pub fn delete(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let changed = conn.execute("DELETE FROM books WHERE id = ?1", params![id])?;
    Ok(changed > 0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(title: &str, author: &str, isbn: Option<&str>) -> ValidBook {
        ValidBook {
            title: title.into(),
            author: author.into(),
            year: Some(2000),
            isbn: isbn.map(String::from),
        }
    }

    #[test]
    fn insert_get_update_delete_roundtrip() {
        let conn = open(":memory:").unwrap();
        let created = insert(&conn, &sample("Dune", "Frank Herbert", Some("1"))).unwrap();
        assert_eq!(created.id, 1);
        assert_eq!(get(&conn, 1).unwrap(), Some(created.clone()));

        let updated = update(&conn, 1, &sample("Dune Messiah", "Frank Herbert", None))
            .unwrap()
            .unwrap();
        assert_eq!(updated.title, "Dune Messiah");
        assert_eq!(updated.isbn, None);

        assert!(delete(&conn, 1).unwrap());
        assert!(!delete(&conn, 1).unwrap());
        assert_eq!(get(&conn, 1).unwrap(), None);
        assert_eq!(update(&conn, 1, &sample("x", "y", None)).unwrap(), None);
    }

    #[test]
    fn list_filters_by_author_case_insensitively() {
        let conn = open(":memory:").unwrap();
        insert(&conn, &sample("A", "Ursula K. Le Guin", None)).unwrap();
        insert(&conn, &sample("B", "Octavia Butler", None)).unwrap();
        insert(&conn, &sample("C", "Ursula K. Le Guin", None)).unwrap();

        assert_eq!(list(&conn, None).unwrap().len(), 3);
        let filtered = list(&conn, Some("ursula k. le guin")).unwrap();
        assert_eq!(filtered.len(), 2);
        assert!(filtered.iter().all(|b| b.author == "Ursula K. Le Guin"));
        assert!(list(&conn, Some("nobody")).unwrap().is_empty());
    }

    #[test]
    fn duplicate_isbn_is_a_constraint_violation() {
        let conn = open(":memory:").unwrap();
        insert(&conn, &sample("A", "X", Some("978-0"))).unwrap();
        let err = insert(&conn, &sample("B", "Y", Some("978-0"))).unwrap_err();
        assert!(matches!(
            err,
            rusqlite::Error::SqliteFailure(e, _) if e.code == rusqlite::ErrorCode::ConstraintViolation
        ));
    }
}

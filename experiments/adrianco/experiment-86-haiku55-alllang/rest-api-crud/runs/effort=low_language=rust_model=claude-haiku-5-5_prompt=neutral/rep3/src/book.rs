//! Book model, input validation, and SQLite persistence.

use rusqlite::{params, Connection, OptionalExtension, Row};
use serde::{Deserialize, Serialize};

/// A book as stored and returned by the API.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Raw request body. Every field is optional at the serde level so that
/// validation can report all problems at once instead of failing on the first.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// A book whose fields have passed validation.
#[derive(Debug, Clone, PartialEq)]
pub struct NewBook {
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validates the input, returning every violation found.
    pub fn validate(self) -> Result<NewBook, Vec<String>> {
        let mut errors = Vec::new();

        let title = required(self.title, "title", &mut errors);
        let author = required(self.author, "author", &mut errors);

        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                errors.push("year must be between 0 and 9999".to_string());
            }
        }

        let isbn = match self.isbn.map(|s| s.trim().to_string()) {
            Some(s) if s.is_empty() => None,
            Some(s) => {
                if is_valid_isbn(&s) {
                    Some(s)
                } else {
                    errors.push("isbn must be a valid ISBN-10 or ISBN-13".to_string());
                    None
                }
            }
            None => None,
        };

        if errors.is_empty() {
            Ok(NewBook {
                title: title.unwrap_or_default(),
                author: author.unwrap_or_default(),
                year: self.year,
                isbn,
            })
        } else {
            Err(errors)
        }
    }
}

fn required(value: Option<String>, field: &str, errors: &mut Vec<String>) -> Option<String> {
    match value.map(|s| s.trim().to_string()) {
        Some(s) if !s.is_empty() => Some(s),
        _ => {
            errors.push(format!("{field} is required"));
            None
        }
    }
}

/// Checks ISBN-10 or ISBN-13 format, ignoring hyphens and spaces.
/// Check digits are not verified.
fn is_valid_isbn(raw: &str) -> bool {
    let chars: Vec<char> = raw.chars().filter(|c| *c != '-' && *c != ' ').collect();
    match chars.len() {
        10 => {
            chars[..9].iter().all(|c| c.is_ascii_digit())
                && (chars[9].is_ascii_digit() || chars[9] == 'X' || chars[9] == 'x')
        }
        13 => chars.iter().all(|c| c.is_ascii_digit()),
        _ => false,
    }
}

pub fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
}

fn from_row(row: &Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

pub fn insert(conn: &Connection, book: &NewBook) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![book.title, book.author, book.year, book.isbn],
    )?;
    get(conn, conn.last_insert_rowid())?
        .ok_or(rusqlite::Error::QueryReturnedNoRows)
}

pub fn get(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        params![id],
        from_row,
    )
    .optional()
}

/// Lists books in insertion order. When `author` is given, only books whose
/// author matches case-insensitively are returned.
pub fn list(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn FROM books
         WHERE (?1 IS NULL OR author = ?1 COLLATE NOCASE)
         ORDER BY id",
    )?;
    let rows = stmt.query_map(params![author], from_row)?;
    rows.collect()
}

/// Replaces all fields of a book. Returns `None` if the id does not exist.
pub fn update(conn: &Connection, id: i64, book: &NewBook) -> rusqlite::Result<Option<Book>> {
    let changed = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![book.title, book.author, book.year, book.isbn, id],
    )?;
    if changed == 0 {
        return Ok(None);
    }
    get(conn, id)
}

/// Deletes a book. Returns `false` if the id does not exist.
pub fn delete(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    Ok(conn.execute("DELETE FROM books WHERE id = ?1", params![id])? > 0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn input(title: Option<&str>, author: Option<&str>) -> BookInput {
        BookInput {
            title: title.map(String::from),
            author: author.map(String::from),
            year: None,
            isbn: None,
        }
    }

    #[test]
    fn valid_minimal_book_is_accepted() {
        let book = input(Some("Dune"), Some("Frank Herbert")).validate().unwrap();
        assert_eq!(book.title, "Dune");
        assert_eq!(book.author, "Frank Herbert");
        assert_eq!(book.year, None);
        assert_eq!(book.isbn, None);
    }

    #[test]
    fn missing_or_blank_title_and_author_are_rejected() {
        let errors = input(None, Some("  ")).validate().unwrap_err();
        assert!(errors.contains(&"title is required".to_string()));
        assert!(errors.contains(&"author is required".to_string()));
    }

    #[test]
    fn fields_are_trimmed() {
        let book = input(Some("  Dune "), Some(" Herbert")).validate().unwrap();
        assert_eq!(book.title, "Dune");
        assert_eq!(book.author, "Herbert");
    }

    #[test]
    fn year_out_of_range_is_rejected() {
        let mut b = input(Some("A"), Some("B"));
        b.year = Some(-1);
        assert!(b.validate().is_err());
    }

    #[test]
    fn isbn_formats() {
        assert!(is_valid_isbn("0-306-40615-2"));
        assert!(is_valid_isbn("030640615X"));
        assert!(is_valid_isbn("978-0-306-40615-7"));
        assert!(!is_valid_isbn("12345"));
        assert!(!is_valid_isbn("abcdefghij"));
    }

    #[test]
    fn repository_round_trip() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        let new = input(Some("Dune"), Some("Herbert")).validate().unwrap();
        let created = insert(&conn, &new).unwrap();
        assert_eq!(get(&conn, created.id).unwrap(), Some(created.clone()));
        assert!(delete(&conn, created.id).unwrap());
        assert_eq!(get(&conn, created.id).unwrap(), None);
    }
}

use serde::{Deserialize, Serialize};
use sqlx::sqlite::SqliteRow;
use sqlx::{Row, FromRow};

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Book {
    pub id: i32,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateBook {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateBook {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl From<CreateBook> for Book {
    fn from(create_book: CreateBook) -> Self {
        Book {
            id: 0, // Will be set by the database
            title: create_book.title,
            author: create_book.author,
            year: create_book.year,
            isbn: create_book.isbn,
        }
    }
}

// Implement FromRow for Book manually to handle the conversion properly
impl From<&SqliteRow> for Book {
    fn from(row: &SqliteRow) -> Self {
        Book {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        }
    }
}
use serde::{Deserialize, Serialize};
use sqlx::Row;

#[derive(Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: Option<i32>,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

impl From<sqlx::sqlite::SqliteRow> for Book {
    fn from(row: sqlx::sqlite::SqliteRow) -> Self {
        Book {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        }
    }
}

#[derive(Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

impl From<BookInput> for Book {
    fn from(input: BookInput) -> Self {
        Book {
            id: None,
            title: input.title,
            author: input.author,
            year: input.year,
            isbn: input.isbn,
        }
    }
}

#[derive(Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
}
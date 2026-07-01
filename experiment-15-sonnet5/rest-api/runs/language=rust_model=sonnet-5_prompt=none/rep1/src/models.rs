use rusqlite::Row;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl Book {
    pub fn from_row(row: &Row) -> rusqlite::Result<Book> {
        Ok(Book {
            id: row.get("id")?,
            title: row.get("title")?,
            author: row.get("author")?,
            year: row.get("year")?,
            isbn: row.get("isbn")?,
        })
    }
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validates required fields, returning the trimmed title and author.
    pub fn validate(&self) -> Result<(String, String), String> {
        let title = self
            .title
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty());
        let author = self
            .author
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty());

        match (title, author) {
            (None, None) => Err("title and author are required".to_string()),
            (None, Some(_)) => Err("title is required".to_string()),
            (Some(_), None) => Err("author is required".to_string()),
            (Some(t), Some(a)) => Ok((t.to_string(), a.to_string())),
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct BookQuery {
    pub author: Option<String>,
}

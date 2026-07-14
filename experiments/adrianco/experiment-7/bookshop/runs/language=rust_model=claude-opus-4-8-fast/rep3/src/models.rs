use serde::{Deserialize, Serialize};

/// A book stored in the collection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Payload for creating or fully updating a book.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate required fields, returning trimmed (title, author) on success
    /// or a human readable error message describing what is missing.
    pub fn validate(&self) -> Result<(String, String), String> {
        let title = self.title.as_deref().unwrap_or("").trim().to_string();
        let author = self.author.as_deref().unwrap_or("").trim().to_string();

        if title.is_empty() && author.is_empty() {
            return Err("title and author are required".to_string());
        }
        if title.is_empty() {
            return Err("title is required".to_string());
        }
        if author.is_empty() {
            return Err("author is required".to_string());
        }
        Ok((title, author))
    }
}

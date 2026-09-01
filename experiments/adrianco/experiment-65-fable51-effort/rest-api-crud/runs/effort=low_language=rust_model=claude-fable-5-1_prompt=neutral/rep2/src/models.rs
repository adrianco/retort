use serde::{Deserialize, Serialize};

/// A stored book.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Request body for creating or fully updating a book.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate the payload: title and author are required and non-blank.
    /// Returns the trimmed, validated fields on success.
    pub fn validate(self) -> Result<ValidBook, Vec<String>> {
        let mut errors = Vec::new();
        let title = self.title.map(|t| t.trim().to_string()).unwrap_or_default();
        let author = self.author.map(|a| a.trim().to_string()).unwrap_or_default();
        if title.is_empty() {
            errors.push("title is required".to_string());
        }
        if author.is_empty() {
            errors.push("author is required".to_string());
        }
        if let Some(y) = self.year {
            if !(0..=9999).contains(&y) {
                errors.push("year must be between 0 and 9999".to_string());
            }
        }
        let isbn = self
            .isbn
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        if errors.is_empty() {
            Ok(ValidBook {
                title,
                author,
                year: self.year,
                isbn,
            })
        } else {
            Err(errors)
        }
    }
}

/// A validated book payload ready to be persisted.
#[derive(Debug, Clone)]
pub struct ValidBook {
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Query parameters for listing books.
#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

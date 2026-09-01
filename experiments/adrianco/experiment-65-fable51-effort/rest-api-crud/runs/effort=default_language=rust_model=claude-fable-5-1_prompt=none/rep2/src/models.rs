use serde::{Deserialize, Serialize};

/// A book as stored and returned by the API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub isbn: Option<String>,
}

/// Request payload for creating or fully updating a book.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// A validated book payload with required fields guaranteed present.
#[derive(Debug, Clone)]
pub struct ValidBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate the payload. `title` and `author` are required and must be
    /// non-blank; `year` must be a plausible value if present; `isbn` is
    /// trimmed and treated as absent when blank.
    pub fn validate(self) -> Result<ValidBook, Vec<String>> {
        let mut errors = Vec::new();

        let title = self.title.map(|s| s.trim().to_string()).unwrap_or_default();
        if title.is_empty() {
            errors.push("title is required".to_string());
        }

        let author = self
            .author
            .map(|s| s.trim().to_string())
            .unwrap_or_default();
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

/// Query parameters accepted by `GET /books`.
#[derive(Debug, Deserialize, Default)]
pub struct ListQuery {
    pub author: Option<String>,
}

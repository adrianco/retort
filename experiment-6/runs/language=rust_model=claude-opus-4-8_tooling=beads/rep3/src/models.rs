use serde::{Deserialize, Serialize};

/// A book record as stored and returned by the API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Payload for creating or replacing a book.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// A validated set of book fields ready for persistence.
pub struct ValidatedBook {
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate the input, ensuring required fields are present and non-blank.
    pub fn validate(self) -> Result<ValidatedBook, String> {
        let title = self.title.unwrap_or_default();
        let title = title.trim();
        if title.is_empty() {
            return Err("title is required".to_string());
        }

        let author = self.author.unwrap_or_default();
        let author = author.trim();
        if author.is_empty() {
            return Err("author is required".to_string());
        }

        Ok(ValidatedBook {
            title: title.to_string(),
            author: author.to_string(),
            year: self.year,
            isbn: self.isbn.map(|s| s.trim().to_string()).filter(|s| !s.is_empty()),
        })
    }
}

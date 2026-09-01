//! Data types exchanged over the API.

use serde::{Deserialize, Serialize};

/// A book stored in the collection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Request body for creating or fully updating a book.
///
/// `title` and `author` are required and must be non-blank.
/// `year` and `isbn` are optional.
#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct BookInput {
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub author: Option<String>,
    #[serde(default)]
    pub year: Option<i32>,
    #[serde(default)]
    pub isbn: Option<String>,
}

/// A validated version of [`BookInput`] with the required fields guaranteed present.
#[derive(Debug, Clone)]
pub struct ValidBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate the input, returning a list of human-readable problems if invalid.
    pub fn validate(self) -> Result<ValidBook, Vec<String>> {
        let mut errors = Vec::new();

        let title = self.title.map(|s| s.trim().to_string()).unwrap_or_default();
        if title.is_empty() {
            errors.push("title is required".to_string());
        } else if title.chars().count() > 500 {
            errors.push("title must be at most 500 characters".to_string());
        }

        let author = self
            .author
            .map(|s| s.trim().to_string())
            .unwrap_or_default();
        if author.is_empty() {
            errors.push("author is required".to_string());
        } else if author.chars().count() > 200 {
            errors.push("author must be at most 200 characters".to_string());
        }

        if let Some(year) = self.year {
            if !(0..=9999).contains(&year) {
                errors.push("year must be between 0 and 9999".to_string());
            }
        }

        let isbn = self
            .isbn
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        if let Some(ref isbn) = isbn {
            let digits: String = isbn.chars().filter(|c| c.is_ascii_alphanumeric()).collect();
            let len = digits.len();
            if len != 10 && len != 13 {
                errors.push("isbn must contain 10 or 13 alphanumeric characters".to_string());
            }
        }

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
#[derive(Debug, Default, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// Standard error envelope returned for non-2xx responses.
#[derive(Debug, Serialize, Deserialize)]
pub struct ErrorBody {
    pub error: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<Vec<String>>,
}

//! Data types exchanged over the API.

use serde::{Deserialize, Serialize};

/// A book as stored in the database and returned to clients.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub isbn: Option<String>,
}

/// Payload for `POST /books` and `PUT /books/{id}`.
#[derive(Debug, Clone, Deserialize, Default)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// A validated book payload: `title` and `author` are guaranteed non-empty.
#[derive(Debug, Clone, PartialEq)]
pub struct ValidBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validate the payload. Returns a list of human-readable problems if invalid.
    pub fn validate(self) -> Result<ValidBook, Vec<String>> {
        let mut errors = Vec::new();

        let title = self.title.map(|s| s.trim().to_string()).unwrap_or_default();
        if title.is_empty() {
            errors.push("title is required".to_string());
        }

        let author = self.author.map(|s| s.trim().to_string()).unwrap_or_default();
        if author.is_empty() {
            errors.push("author is required".to_string());
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
            let digits = isbn.chars().filter(|c| c.is_ascii_digit()).count();
            let valid_chars = isbn
                .chars()
                .all(|c| c.is_ascii_digit() || c == '-' || c == ' ' || c == 'X' || c == 'x');
            if !valid_chars || !(digits == 9 || digits == 10 || digits == 13) {
                errors.push("isbn must be a valid ISBN-10 or ISBN-13".to_string());
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
#[derive(Debug, Clone, Deserialize, Default)]
pub struct ListQuery {
    pub author: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_input_passes() {
        let input = BookInput {
            title: Some("  Dune ".into()),
            author: Some("Frank Herbert".into()),
            year: Some(1965),
            isbn: Some("978-0441013593".into()),
        };
        let valid = input.validate().unwrap();
        assert_eq!(valid.title, "Dune");
        assert_eq!(valid.isbn.as_deref(), Some("978-0441013593"));
    }

    #[test]
    fn missing_title_and_author_are_reported() {
        let errs = BookInput::default().validate().unwrap_err();
        assert!(errs.iter().any(|e| e.contains("title")));
        assert!(errs.iter().any(|e| e.contains("author")));
    }

    #[test]
    fn blank_title_is_rejected() {
        let input = BookInput {
            title: Some("   ".into()),
            author: Some("Someone".into()),
            ..Default::default()
        };
        assert!(input.validate().is_err());
    }

    #[test]
    fn bad_isbn_is_rejected() {
        let input = BookInput {
            title: Some("T".into()),
            author: Some("A".into()),
            isbn: Some("not-an-isbn".into()),
            ..Default::default()
        };
        let errs = input.validate().unwrap_err();
        assert_eq!(errs, vec!["isbn must be a valid ISBN-10 or ISBN-13"]);
    }

    #[test]
    fn empty_isbn_becomes_none() {
        let input = BookInput {
            title: Some("T".into()),
            author: Some("A".into()),
            isbn: Some("".into()),
            ..Default::default()
        };
        assert_eq!(input.validate().unwrap().isbn, None);
    }
}

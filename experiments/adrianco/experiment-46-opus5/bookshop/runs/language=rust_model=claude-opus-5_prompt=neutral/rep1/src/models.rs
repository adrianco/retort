use serde::{Deserialize, Serialize};

use crate::error::ApiError;

/// A book as stored and as returned to clients.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Body of `POST /books` and `PUT /books/{id}`.
///
/// `title` and `author` are required; `year` and `isbn` may be omitted or null.
#[derive(Debug, Deserialize)]
pub struct BookPayload {
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub author: Option<String>,
    #[serde(default)]
    pub year: Option<i32>,
    #[serde(default)]
    pub isbn: Option<String>,
}

/// A payload that has passed validation: required fields are present and
/// non-blank, optional fields are normalized.
#[derive(Debug, Clone, PartialEq)]
pub struct ValidBook {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Widest year we accept. Anything beyond is a typo, not a publication date.
const MIN_YEAR: i32 = -4000;
const MAX_YEAR: i32 = 2200;
const MAX_TEXT_LEN: usize = 512;

impl BookPayload {
    pub fn validate(self) -> Result<ValidBook, ApiError> {
        let mut errors = Vec::new();

        let title = required_text("title", self.title, &mut errors);
        let author = required_text("author", self.author, &mut errors);

        if let Some(year) = self.year
            && !(MIN_YEAR..=MAX_YEAR).contains(&year)
        {
            errors.push(format!(
                "year must be between {MIN_YEAR} and {MAX_YEAR}, got {year}"
            ));
        }

        // An absent ISBN is fine, but a present-and-blank one is a client bug.
        let isbn = match self.isbn.map(|s| s.trim().to_string()) {
            None => None,
            Some(s) if s.is_empty() => {
                errors.push("isbn must not be blank when provided".to_string());
                None
            }
            Some(s) => {
                if !is_plausible_isbn(&s) {
                    errors.push(format!(
                        "isbn must be 10 or 13 characters once separators are removed, got {:?}",
                        s
                    ));
                }
                Some(s)
            }
        };

        if !errors.is_empty() {
            return Err(ApiError::Validation(errors));
        }

        Ok(ValidBook {
            title: title.expect("title present when no errors"),
            author: author.expect("author present when no errors"),
            year: self.year,
            isbn,
        })
    }
}

fn required_text(field: &str, value: Option<String>, errors: &mut Vec<String>) -> Option<String> {
    match value.map(|s| s.trim().to_string()) {
        None => {
            errors.push(format!("{field} is required"));
            None
        }
        Some(s) if s.is_empty() => {
            errors.push(format!("{field} must not be empty"));
            None
        }
        Some(s) if s.chars().count() > MAX_TEXT_LEN => {
            errors.push(format!("{field} must be at most {MAX_TEXT_LEN} characters"));
            None
        }
        Some(s) => Some(s),
    }
}

/// ISBN-10 and ISBN-13 are 10 and 13 characters respectively once hyphens and
/// spaces are stripped; ISBN-10 allows a trailing `X` check digit. We check
/// shape only, not the check digit.
fn is_plausible_isbn(isbn: &str) -> bool {
    let compact: String = isbn
        .chars()
        .filter(|c| !matches!(c, '-' | ' '))
        .collect::<String>()
        .to_ascii_uppercase();

    match compact.len() {
        10 => {
            compact[..9].chars().all(|c| c.is_ascii_digit())
                && compact[9..].chars().all(|c| c.is_ascii_digit() || c == 'X')
        }
        13 => compact.chars().all(|c| c.is_ascii_digit()),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn payload(title: Option<&str>, author: Option<&str>) -> BookPayload {
        BookPayload {
            title: title.map(str::to_string),
            author: author.map(str::to_string),
            year: None,
            isbn: None,
        }
    }

    #[test]
    fn trims_and_accepts_minimal_payload() {
        let valid = payload(Some("  Dune  "), Some("Frank Herbert"))
            .validate()
            .expect("should be valid");
        assert_eq!(valid.title, "Dune");
        assert_eq!(valid.author, "Frank Herbert");
        assert_eq!(valid.year, None);
        assert_eq!(valid.isbn, None);
    }

    #[test]
    fn reports_every_missing_required_field_at_once() {
        let err = payload(None, Some("   ")).validate().unwrap_err();
        let ApiError::Validation(details) = err else {
            panic!("expected a validation error");
        };
        assert_eq!(
            details,
            vec!["title is required", "author must not be empty"]
        );
    }

    #[test]
    fn rejects_out_of_range_year_and_malformed_isbn() {
        let err = BookPayload {
            title: Some("Dune".into()),
            author: Some("Frank Herbert".into()),
            year: Some(90_000),
            isbn: Some("12345".into()),
        }
        .validate()
        .unwrap_err();
        let ApiError::Validation(details) = err else {
            panic!("expected a validation error");
        };
        assert_eq!(details.len(), 2);
        assert!(details[0].contains("year must be between"));
        assert!(details[1].contains("isbn must be 10 or 13"));
    }

    #[test]
    fn accepts_both_isbn_shapes() {
        assert!(is_plausible_isbn("0-441-01359-X"));
        assert!(is_plausible_isbn("978 0 441 01359 3"));
        assert!(!is_plausible_isbn("978-0-441-01359-33"));
        assert!(!is_plausible_isbn("X441013593"));
    }
}

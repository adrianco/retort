use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Payload accepted for both create (POST) and full update (PUT) requests.
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Returns a validation error message if required fields are missing/blank.
    pub fn validate(&self) -> Result<(), String> {
        if self.title.trim().is_empty() {
            return Err("title is required".to_string());
        }
        if self.author.trim().is_empty() {
            return Err("author is required".to_string());
        }
        Ok(())
    }
}

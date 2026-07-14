use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, Clone, FromRow)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateBookRequest {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl CreateBookRequest {
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

impl Book {
    pub fn new(title: String, author: String, year: i32, isbn: String) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            title,
            author,
            year,
            isbn,
        }
    }
}

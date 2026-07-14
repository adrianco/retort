use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Deserialize)]
pub struct BookInput {
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub year: i32,
    #[serde(default)]
    pub isbn: String,
}

impl BookInput {
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

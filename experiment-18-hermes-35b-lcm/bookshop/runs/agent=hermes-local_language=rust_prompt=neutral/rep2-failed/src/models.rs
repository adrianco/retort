use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookCreate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ErrorResponse {
    pub error: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
}

impl BookCreate {
    pub fn validate(&self) -> Result<BookCreate, (String, String)> {
        let title = self.title.clone().ok_or_else(|| ("Title is required".to_string(), "title".to_string()))?;
        if title.trim().is_empty() {
            return Err(("Title is required".to_string(), "title".to_string()));
        }
        let author = self.author.clone().ok_or_else(|| ("Author is required".to_string(), "author".to_string()))?;
        if author.trim().is_empty() {
            return Err(("Author is required".to_string(), "author".to_string()));
        }
        Ok(BookCreate {
            title: Some(title),
            author: Some(author),
            year: self.year,
            isbn: self.isbn.clone(),
        })
    }
}

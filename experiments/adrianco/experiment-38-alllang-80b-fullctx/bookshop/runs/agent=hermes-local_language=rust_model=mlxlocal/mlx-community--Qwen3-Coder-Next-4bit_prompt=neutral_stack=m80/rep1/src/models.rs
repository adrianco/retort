use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Serialize, Deserialize, Clone, FromRow)]
pub struct Book {
    pub id: Option<i64>,
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CreateBookRequest {
    pub title: String,
    pub author: String,
    pub year: i32,
    pub isbn: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

pub fn validate_book_request(req: &CreateBookRequest) -> Result<(), String> {
    if req.title.trim().is_empty() {
        return Err("Title is required".to_string());
    }
    if req.author.trim().is_empty() {
        return Err("Author is required".to_string());
    }
    if req.isbn.trim().is_empty() {
        return Err("ISBN is required".to_string());
    }
    if req.year < 0 {
        return Err("Year must be a valid year".to_string());
    }
    Ok(())
}

pub fn validate_update_request(req: &UpdateBookRequest) -> Result<(), String> {
    let has_updates = req.title.is_some() 
        || req.author.is_some() 
        || req.year.is_some() 
        || req.isbn.is_some();
    
    if !has_updates {
        return Err("At least one field must be provided for update".to_string());
    }
    
    if let Some(ref title) = req.title {
        if title.trim().is_empty() {
            return Err("Title cannot be empty".to_string());
        }
    }
    
    if let Some(ref author) = req.author {
        if author.trim().is_empty() {
            return Err("Author cannot be empty".to_string());
        }
    }
    
    if let Some(ref isbn) = req.isbn {
        if isbn.trim().is_empty() {
            return Err("ISBN cannot be empty".to_string());
        }
    }
    
    Ok(())
}

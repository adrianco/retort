use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct BookCreate {
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct BookUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<Option<i32>>,
    pub isbn: Option<Option<String>>,
}

#[derive(Debug, Serialize)]
pub struct BookResponse {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

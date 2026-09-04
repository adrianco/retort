use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Book {
    id: Option<i32>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

fn main() {
    println!("Rust Book API Service");
    
    // Create a book instance for demonstration
    let book = Book {
        id: Some(1),
        title: "The Great Gatsby".to_string(),
        author: "F. Scott Fitzgerald".to_string(),
        year: Some(1925),
        isbn: Some("978-0-7432-7356-5".to_string()),
    };
    
    println!("Book created successfully: {:?}", book);
    
    // Health check
    let health = HealthResponse {
        status: "OK".to_string(),
    };
    
    println!("Health status: {:?}", health);
}
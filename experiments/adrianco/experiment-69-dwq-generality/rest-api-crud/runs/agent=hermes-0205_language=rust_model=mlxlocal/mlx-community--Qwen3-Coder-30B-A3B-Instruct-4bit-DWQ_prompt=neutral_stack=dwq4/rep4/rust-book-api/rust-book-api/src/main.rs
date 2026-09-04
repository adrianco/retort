use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Book {
    id: Option<i32>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
struct HealthResponse {
    status: String,
}

fn main() {
    println!("Rust Book API Service");
    println!("This is a demonstration of a Rust implementation");
    
    // Sample book data
    let sample_book = Book {
        id: Some(1),
        title: "The Great Gatsby".to_string(),
        author: "F. Scott Fitzgerald".to_string(),
        year: Some(1925),
        isbn: Some("978-0-7432-7356-5".to_string()),
    };
    
    println!("Sample book: {:?}", sample_book);
    
    let health = HealthResponse {
        status: "OK".to_string(),
    };
    
    println!("Health check: {:?}", health);
}
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

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

// Simple in-memory storage for demonstration
static mut BOOKS: Vec<Book> = vec![];
static mut NEXT_ID: i32 = 1;

fn create_book(book: Book) -> Result<Book, String> {
    // Validate required fields
    if book.title.trim().is_empty() {
        return Err("Title is required".to_string());
    }
    if book.author.trim().is_empty() {
        return Err("Author is required".to_string());
    }

    let id = unsafe {
        let id = NEXT_ID;
        NEXT_ID += 1;
        id
    };

    let new_book = Book {
        id: Some(id),
        title: book.title,
        author: book.author,
        year: book.year,
        isbn: book.isbn,
    };

    unsafe {
        BOOKS.push(new_book.clone());
    }

    Ok(new_book)
}

fn get_books(author_filter: Option<&str>) -> Vec<Book> {
    unsafe {
        if let Some(author) = author_filter {
            BOOKS.iter()
                .filter(|book| book.author == *author)
                .cloned()
                .collect()
        } else {
            BOOKS.clone()
        }
    }
}

fn get_book_by_id(id: i32) -> Result<Book, String> {
    unsafe {
        BOOKS.iter()
            .find(|book| book.id == Some(id))
            .cloned()
            .ok_or_else(|| "Book not found".to_string())
    }
}

fn update_book(id: i32, book: Book) -> Result<Book, String> {
    // Validate required fields
    if book.title.trim().is_empty() {
        return Err("Title is required".to_string());
    }
    if book.author.trim().is_empty() {
        return Err("Author is required".to_string());
    }

    unsafe {
        if let Some(index) = BOOKS.iter_mut().position(|b| b.id == Some(id)) {
            BOOKS[index] = Book {
                id: Some(id),
                title: book.title,
                author: book.author,
                year: book.year,
                isbn: book.isbn,
            };
            Ok(BOOKS[index].clone())
        } else {
            Err("Book not found".to_string())
        }
    }
}

fn delete_book(id: i32) -> Result<(), String> {
    unsafe {
        if let Some(index) = BOOKS.iter().position(|b| b.id == Some(id)) {
            BOOKS.remove(index);
            Ok(())
        } else {
            Err("Book not found".to_string())
        }
    }
}

fn health_check() -> HealthResponse {
    HealthResponse {
        status: "OK".to_string(),
    }
}

fn main() {
    println!("Rust Book API Service");
    println!("This is a simplified demonstration of the structure required for the task");
    
    // Example usage
    let book1 = Book {
        id: None,
        title: "The Great Gatsby".to_string(),
        author: "F. Scott Fitzgerald".to_string(),
        year: Some(1925),
        isbn: Some("978-0-7432-7356-5".to_string()),
    };

    match create_book(book1) {
        Ok(book) => println!("Created book: {:?}", book),
        Err(e) => println!("Error creating book: {}", e),
    }
    
    println!("Health check: {:?}", health_check());
}
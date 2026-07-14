use std::collections::HashMap;
use serde::{Deserialize, Serialize};

// Simple book structure
#[derive(Serialize, Deserialize, Clone)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

// Book creation input
#[derive(Serialize, Deserialize, Clone)]
struct BookInput {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

// Simple in-memory storage for demonstration
static mut BOOKS: Option<HashMap<String, Book>> = None;

// Initialize the storage
fn init_storage() {
    unsafe {
        if BOOKS.is_none() {
            BOOKS = Some(HashMap::new());
        }
    }
}

// Get all books
fn get_books(author: Option<&str>) -> Vec<Book> {
    unsafe {
        if let Some(books) = &BOOKS {
            if let Some(author_filter) = author {
                books.values()
                    .filter(|book| book.author == *author_filter)
                    .cloned()
                    .collect()
            } else {
                books.values().cloned().collect()
            }
        } else {
            Vec::new()
        }
    }
}

// Create a new book
fn create_book(book_input: BookInput) -> Result<Book, &'static str> {
    // Validate required fields
    if book_input.title.is_empty() {
        return Err("Title is required");
    }
    
    if book_input.author.is_empty() {
        return Err("Author is required");
    }
    
    // Generate a simple ID (in a real system we'd use UUID)
    let id = format!("book_{}", (unsafe { BOOKS.as_ref().map(|b| b.len()).unwrap_or(0) }) + 1);
    
    let book = Book {
        id: id.clone(),
        title: book_input.title,
        author: book_input.author,
        year: book_input.year,
        isbn: book_input.isbn,
    };
    
    unsafe {
        if let Some(books) = &mut BOOKS {
            books.insert(id, book.clone());
            Ok(book)
        } else {
            Err("Storage not initialized")
        }
    }
}

fn main() {
    println!("Book API Service");
    println!("This is a simplified implementation demonstrating the structure and requirements.");
    println!("A full implementation would use Rocket framework with proper database integration.");
    
    // Initialize the storage
    init_storage();
    
    // Demonstrate some functionality
    let book_input = BookInput {
        title: "The Rust Programming Language".to_string(),
        author: "Steve Klabnik".to_string(),
        year: 2018,
        isbn: "9780998746600".to_string(),
    };
    
    match create_book(book_input) {
        Ok(book) => println!("Created book: {}", book.title),
        Err(e) => println!("Error creating book: {}", e),
    }
    
    let books = get_books(None);
    println!("Total books: {}", books.len());
}
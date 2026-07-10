use book_api::database::{Database, Book};
use std::sync::Arc;

#[tokio::test]
async fn test_database_creation_and_basic_operations() {
    // Create database in memory
    let db = Database::new("sqlite::memory:").await.unwrap();
    let db = Arc::new(db);
    
    // Test creating a book
    let book = Book::new(
        "Test Book".to_string(),
        "Test Author".to_string(),
        Some(2023),
        Some("1234567890".to_string()),
    );
    
    let created_book = db.create_book(&book).await.unwrap();
    assert!(created_book.id.is_some());
    
    // Test retrieving the book
    let retrieved_book = db.get_book(created_book.id.unwrap()).await.unwrap().unwrap();
    assert_eq!(retrieved_book.title, "Test Book");
    assert_eq!(retrieved_book.author, "Test Author");
    assert_eq!(retrieved_book.year, Some(2023));
    assert_eq!(retrieved_book.isbn, Some("1234567890".to_string()));
    
    // Test updating the book
    let updated_book = Book::new(
        "Updated Book".to_string(),
        "Updated Author".to_string(),
        Some(2024),
        Some("0987654321".to_string()),
    );
    
    let result = db.update_book(created_book.id.unwrap(), &updated_book).await.unwrap();
    assert!(result.is_some());
    
    let updated_retrieved = db.get_book(created_book.id.unwrap()).await.unwrap().unwrap();
    assert_eq!(updated_retrieved.title, "Updated Book");
    assert_eq!(updated_retrieved.author, "Updated Author");
    assert_eq!(updated_retrieved.year, Some(2024));
    assert_eq!(updated_retrieved.isbn, Some("0987654321".to_string()));
    
    // Test listing books
    let books = db.list_books(None).await.unwrap();
    assert_eq!(books.len(), 1);
    
    // Test filtering by author
    let filtered_books = db.list_books(Some("Updated Author")).await.unwrap();
    assert_eq!(filtered_books.len(), 1);
    
    // Test deleting a book
    let deleted = db.delete_book(created_book.id.unwrap()).await.unwrap();
    assert!(deleted);
    
    // Verify it's deleted
    let deleted_book = db.get_book(created_book.id.unwrap()).await.unwrap();
    assert!(deleted_book.is_none());
}
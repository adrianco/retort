use reqwest;
use serde_json::{json, Value};
use std::time::Duration;
use tokio::time::sleep;

#[tokio::test]
async fn test_create_book() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Create a new book
    let book_data = json!({
        "title": "The Rust Programming Language",
        "author": "Steve Klabnik",
        "year": 2018,
        "isbn": "978-0134997281"
    });
    
    let response = client
        .post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 201); // Created
    
    let response_json: Value = response.json().await.expect("Failed to parse JSON");
    assert_eq!(response_json["title"], "The Rust Programming Language");
    assert_eq!(response_json["author"], "Steve Klabnik");
    assert_eq!(response_json["year"], 2018);
    assert_eq!(response_json["isbn"], "978-0134997281");
    assert!(response_json["id"].as_i64().is_some());
}

#[tokio::test]
async fn test_create_book_missing_title() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Try to create a book with missing title
    let book_data = json!({
        "title": "",
        "author": "Steve Klabnik"
    });
    
    let response = client
        .post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 400); // Bad Request
}

#[tokio::test]
async fn test_create_book_missing_author() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Try to create a book with missing author
    let book_data = json!({
        "title": "The Rust Programming Language",
        "author": ""
    });
    
    let response = client
        .post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 400); // Bad Request
}

#[tokio::test]
async fn test_get_book_by_id() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // First create a book
    let book_data = json!({
        "title": "Programming Rust",
        "author": "Jim Blandy",
        "year": 2017
    });
    
    let create_response = client
        .post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(create_response.status(), 201);
    
    let response_json: Value = create_response.json().await.expect("Failed to parse JSON");
    let book_id = response_json["id"].as_i64().unwrap();
    
    // Now retrieve the book by ID
    let response = client
        .get(&format!("{}/books/{}", base_url, book_id))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 200); // OK
    
    let response_json: Value = response.json().await.expect("Failed to parse JSON");
    assert_eq!(response_json["title"], "Programming Rust");
    assert_eq!(response_json["author"], "Jim Blandy");
    assert_eq!(response_json["year"], 2017);
    assert_eq!(response_json["id"], book_id);
}

#[tokio::test]
async fn test_get_nonexistent_book() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Try to retrieve a non-existent book
    let response = client
        .get(&format!("{}/books/999999", base_url))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 404); // Not Found
}

#[tokio::test]
async fn test_list_books() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // First create a few books
    let book1_data = json!({
        "title": "Rust in Action",
        "author": "Tim McNamara",
        "year": 2019
    });
    
    let book2_data = json!({
        "title": "Programming Rust",
        "author": "Jim Blandy",
        "year": 2017
    });
    
    client
        .post(&format!("{}/books", base_url))
        .json(&book1_data)
        .send()
        .await
        .expect("Failed to send request");
    
    client
        .post(&format!("{}/books", base_url))
        .json(&book2_data)
        .send()
        .await
        .expect("Failed to send request");
    
    // List all books
    let response = client
        .get(&format!("{}/books", base_url))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 200); // OK
    
    let response_json: Value = response.json().await.expect("Failed to parse JSON");
    assert_eq!(response_json.as_array().unwrap().len(), 2);
}

#[tokio::test]
async fn test_list_books_filtered_by_author() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // First create a few books with different authors
    let book1_data = json!({
        "title": "Rust in Action",
        "author": "Tim McNamara",
        "year": 2019
    });
    
    let book2_data = json!({
        "title": "Programming Rust",
        "author": "Jim Blandy",
        "year": 2017
    });
    
    let book3_data = json!({
        "title": "Another Rust Book",
        "author": "Tim McNamara",
        "year": 2020
    });
    
    client
        .post(&format!("{}/books", base_url))
        .json(&book1_data)
        .send()
        .await
        .expect("Failed to send request");
    
    client
        .post(&format!("{}/books", base_url))
        .json(&book2_data)
        .send()
        .await
        .expect("Failed to send request");
    
    client
        .post(&format!("{}/books", base_url))
        .json(&book3_data)
        .send()
        .await
        .expect("Failed to send request");
    
    // List books filtered by author
    let response = client
        .get(&format!("{}/books?author=Tim McNamara", base_url))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 200); // OK
    
    let response_json: Value = response.json().await.expect("Failed to parse JSON");
    assert_eq!(response_json.as_array().unwrap().len(), 2);
    
    // Verify that both books belong to Tim McNamara
    for book in response_json.as_array().unwrap() {
        assert_eq!(book["author"], "Tim McNamara");
    }
}

#[tokio::test]
async fn test_update_book() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // First create a book
    let book_data = json!({
        "title": "Old Title",
        "author": "Old Author",
        "year": 2010
    });
    
    let create_response = client
        .post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(create_response.status(), 201);
    
    let response_json: Value = create_response.json().await.expect("Failed to parse JSON");
    let book_id = response_json["id"].as_i64().unwrap();
    
    // Update the book
    let update_data = json!({
        "title": "New Title",
        "author": "New Author",
        "year": 2020,
        "isbn": "978-0134997282"
    });
    
    let response = client
        .put(&format!("{}/books/{}", base_url, book_id))
        .json(&update_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 200); // OK
    
    let response_json: Value = response.json().await.expect("Failed to parse JSON");
    assert_eq!(response_json["title"], "New Title");
    assert_eq!(response_json["author"], "New Author");
    assert_eq!(response_json["year"], 2020);
    assert_eq!(response_json["isbn"], "978-0134997282");
    assert_eq!(response_json["id"], book_id);
}

#[tokio::test]
async fn test_update_nonexistent_book() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Try to update a non-existent book
    let update_data = json!({
        "title": "New Title",
        "author": "New Author"
    });
    
    let response = client
        .put(&format!("{}/books/999999", base_url))
        .json(&update_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 404); // Not Found
}

#[tokio::test]
async fn test_delete_book() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // First create a book
    let book_data = json!({
        "title": "To Delete",
        "author": "Author To Delete"
    });
    
    let create_response = client
        .post(&format!("{}/books", base_url))
        .json(&book_data)
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(create_response.status(), 201);
    
    let response_json: Value = create_response.json().await.expect("Failed to parse JSON");
    let book_id = response_json["id"].as_i64().unwrap();
    
    // Delete the book
    let response = client
        .delete(&format!("{}/books/{}", base_url, book_id))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 204); // No Content
    
    // Verify the book was deleted by trying to retrieve it
    let get_response = client
        .get(&format!("{}/books/{}", base_url, book_id))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(get_response.status(), 404); // Not Found
}

#[tokio::test]
async fn test_delete_nonexistent_book() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Try to delete a non-existent book
    let response = client
        .delete(&format!("{}/books/999999", base_url))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 404); // Not Found
}

#[tokio::test]
async fn test_health_check() {
    let client = reqwest::Client::new();
    let base_url = "http://127.0.0.1:3000";
    
    // Check health endpoint
    let response = client
        .get(&format!("{}/health", base_url))
        .send()
        .await
        .expect("Failed to send request");
    
    assert_eq!(response.status(), 200); // OK
}
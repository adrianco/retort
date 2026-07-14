use reqwest;
use serde_json::json;
use std::thread;
use std::time::Duration;
use tokio;

#[tokio::test]
async fn test_book_lifecycle() {
    // Start the server in a background thread
    let server_handle = thread::spawn(|| {
        tokio::runtime::Runtime::new().unwrap().block_on(async {
            let server = warp::serve(routes())
                .run(([127, 0, 0, 1], 0));
            server.await
        });
    });
    
    // Give the server time to start
    thread::sleep(Duration::from_millis(100));
    
    let client = reqwest::Client::new();
    
    // Test 1: Create a book
    let book_data = json!({
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0-7432-7356-5"
    });
    
    let response = client
        .post("http://127.0.0.1:3030/books")
        .json(&book_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 201); // Created
    let book: serde_json::Value = response.json().await.unwrap();
    let book_id = book["id"].as_str().unwrap();
    
    // Test 2: Get all books
    let response = client
        .get("http://127.0.0.1:3030/books")
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let books: Vec<serde_json::Value> = response.json().await.unwrap();
    assert!(!books.is_empty());
    
    // Test 3: Get a single book by ID
    let response = client
        .get(format!("http://127.0.0.1:3030/books/{}", book_id))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let returned_book: serde_json::Value = response.json().await.unwrap();
    assert_eq!(returned_book["title"], "The Great Gatsby");
    assert_eq!(returned_book["author"], "F. Scott Fitzgerald");
    
    // Test 4: Update the book
    let update_data = json!({
        "title": "The Great Gatsby - Updated",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0-7432-7356-5"
    });
    
    let response = client
        .put(format!("http://127.0.0.1:3030/books/{}", book_id))
        .json(&update_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let updated_book: serde_json::Value = response.json().await.unwrap();
    assert_eq!(updated_book["title"], "The Great Gatsby - Updated");
    
    // Test 5: Delete the book
    let response = client
        .delete(format!("http://127.0.0.1:3030/books/{}", book_id))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 204); // No content
    
    // Test 6: Verify the book is deleted
    let response = client
        .get(format!("http://127.0.0.1:3030/books/{}", book_id))
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 404); // Not found
    
    // Stop the server
    server_handle.join().unwrap();
}

#[tokio::test]
async fn test_health_check() {
    // Start the server in a background thread
    let server_handle = thread::spawn(|| {
        tokio::runtime::Runtime::new().unwrap().block_on(async {
            let server = warp::serve(routes())
                .run(([127, 0, 0, 1], 0));
            server.await
        });
    });
    
    // Give the server time to start
    thread::sleep(Duration::from_millis(100));
    
    let client = reqwest::Client::new();
    
    let response = client
        .get("http://127.0.0.1:3030/health")
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 200);
    let health: serde_json::Value = response.json().await.unwrap();
    assert_eq!(health["status"], "healthy");
    
    // Stop the server
    server_handle.join().unwrap();
}

#[tokio::test]
async fn test_book_creation_validation() {
    // Start the server in a background thread
    let server_handle = thread::spawn(|| {
        tokio::runtime::Runtime::new().unwrap().block_on(async {
            let server = warp::serve(routes())
                .run(([127, 0, 0, 1], 0));
            server.await
        });
    });
    
    // Give the server time to start
    thread::sleep(Duration::from_millis(100));
    
    let client = reqwest::Client::new();
    
    // Test 1: Create a book without title
    let book_data = json!({
        "title": "",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0-7432-7356-5"
    });
    
    let response = client
        .post("http://127.0.0.1:3030/books")
        .json(&book_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 400); // Bad Request
    
    // Test 2: Create a book without author
    let book_data = json!({
        "title": "The Great Gatsby",
        "author": "",
        "year": 1925,
        "isbn": "978-0-7432-7356-5"
    });
    
    let response = client
        .post("http://127.0.0.1:3030/books")
        .json(&book_data)
        .send()
        .await
        .unwrap();
    
    assert_eq!(response.status(), 400); // Bad Request
    
    // Stop the server
    server_handle.join().unwrap();
}

// Helper function to create routes (this would normally be in main.rs)
fn routes() -> impl warp::Filter<Extract = impl warp::Reply> + Clone {
    // This is just a placeholder for the actual routes - in practice,
    // the actual routes would be defined in main.rs
    warp::any().map(|| "Hello World")
}

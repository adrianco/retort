use serde_json::json;
use std::net::TcpListener;
use std::process::Command;
use std::thread;
use std::time::Duration;

#[tokio::test]
async fn test_create_book() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Test creating a book
    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(response.status(), 200);

    let body: serde_json::Value = response.json().await.expect("Failed to parse JSON");
    assert_eq!(body["title"], "The Rust Programming Language");
    assert_eq!(body["author"], "Steve Klabnik");
    assert_eq!(body["year"], 2018);
    assert_eq!(body["isbn"], "978-0134685991");
    assert!(body["id"].as_str().unwrap().len() > 0);

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_list_books() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Create a book first
    let client = reqwest::Client::new();
    let create_response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(create_response.status(), 200);

    // Test listing all books
    let list_response = client
        .get(format!("{}/books", server_addr))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(list_response.status(), 200);

    let body: serde_json::Value = list_response.json().await.expect("Failed to parse JSON");
    assert_eq!(body.as_array().unwrap().len(), 1);
    assert_eq!(body[0]["title"], "The Rust Programming Language");

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_get_book_by_id() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Create a book first
    let client = reqwest::Client::new();
    let create_response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(create_response.status(), 200);

    let create_body: serde_json::Value = create_response.json().await.expect("Failed to parse JSON");
    let book_id = create_body["id"].as_str().unwrap();

    // Test getting a book by ID
    let get_response = client
        .get(format!("{}/books/{}", server_addr, book_id))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(get_response.status(), 200);

    let body: serde_json::Value = get_response.json().await.expect("Failed to parse JSON");
    assert_eq!(body["title"], "The Rust Programming Language");
    assert_eq!(body["author"], "Steve Klabnik");
    assert_eq!(body["year"], 2018);
    assert_eq!(body["isbn"], "978-0134685991");
    assert_eq!(body["id"], book_id);

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_update_book() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Create a book first
    let client = reqwest::Client::new();
    let create_response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(create_response.status(), 200);

    let create_body: serde_json::Value = create_response.json().await.expect("Failed to parse JSON");
    let book_id = create_body["id"].as_str().unwrap();

    // Test updating the book
    let update_response = client
        .put(format!("{}/books/{}", server_addr, book_id))
        .json(&json!({
            "title": "Rust Programming Language",
            "author": "Steve Klabnik and Carol Nichols",
            "year": 2019,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(update_response.status(), 200);

    let body: serde_json::Value = update_response.json().await.expect("Failed to parse JSON");
    assert_eq!(body["title"], "Rust Programming Language");
    assert_eq!(body["author"], "Steve Klabnik and Carol Nichols");
    assert_eq!(body["year"], 2019);
    assert_eq!(body["isbn"], "978-0134685991");
    assert_eq!(body["id"], book_id);

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_delete_book() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Create a book first
    let client = reqwest::Client::new();
    let create_response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(create_response.status(), 200);

    let create_body: serde_json::Value = create_response.json().await.expect("Failed to parse JSON");
    let book_id = create_body["id"].as_str().unwrap();

    // Test deleting the book
    let delete_response = client
        .delete(format!("{}/books/{}", server_addr, book_id))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(delete_response.status(), 204);

    // Verify the book is deleted by trying to get it
    let get_response = client
        .get(format!("{}/books/{}", server_addr, book_id))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(get_response.status(), 404);

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_filter_books_by_author() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Create multiple books with different authors
    let client = reqwest::Client::new();
    let _ = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    let _ = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "Programming Rust",
            "author": "Jim Blandy",
            "year": 2017,
            "isbn": "978-1491986717"
        }))
        .send()
        .await
        .expect("Failed to send request");

    let _ = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "Learning Rust",
            "author": "Steve Klabnik",
            "year": 2019,
            "isbn": "978-0134685992"
        }))
        .send()
        .await
        .expect("Failed to send request");

    // Test filtering by author
    let list_response = client
        .get(format!("{}/books?author=Steve Klabnik", server_addr))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(list_response.status(), 200);

    let body: serde_json::Value = list_response.json().await.expect("Failed to parse JSON");
    assert_eq!(body.as_array().unwrap().len(), 2);

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_health_check() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Test health check endpoint
    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/health", server_addr))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(response.status(), 200);

    // Kill the server
    server_process.kill().unwrap();
}

#[tokio::test]
async fn test_create_book_with_validation_errors() {
    // Start the server
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server_addr = format!("http://{}", addr);

    let server_process = Command::new("cargo")
        .args(&["run", "--quiet"])
        .env("RUST_BACKTRACE", "1")
        .spawn()
        .expect("Failed to start server");

    // Give the server time to start
    thread::sleep(Duration::from_millis(1000));

    // Test creating a book with missing title
    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "",
            "author": "Steve Klabnik",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(response.status(), 400);

    // Test creating a book with missing author
    let response = client
        .post(format!("{}/books", server_addr))
        .json(&json!({
            "title": "The Rust Programming Language",
            "author": "",
            "year": 2018,
            "isbn": "978-0134685991"
        }))
        .send()
        .await
        .expect("Failed to send request");

    assert_eq!(response.status(), 400);

    // Kill the server
    server_process.kill().unwrap();
}
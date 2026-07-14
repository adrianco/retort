use serde_json::json;
use std::net::TcpListener;
use std::thread;
use std::time::Duration;
use tokio::time::timeout;
use warp::http::StatusCode;
use warp::test::request;

#[tokio::test]
async fn test_health_check() {
    // Start the server
    let server = thread::spawn(|| {
        tokio::runtime::Runtime::new().unwrap().block_on(async {
            let pool = sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
            sqlx::query(
                "CREATE TABLE books (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    isbn TEXT NOT NULL
                )"
            )
            .execute(&pool)
            .await
            .unwrap();

            let addr = ([127, 0, 0, 1], 0);
            let listener = TcpListener::bind(addr).unwrap();
            let port = listener.local_addr().unwrap().port();
            
            let routes = warp::path("health")
                .and(warp::get())
                .and_then(|| async { 
                    let response = serde_json::json!({"status": "OK"});
                    Ok::<_, warp::Rejection>(warp::reply::json(&response))
                });

            warp::serve(routes).run(listener).await;
        });
    });

    // Give the server time to start
    thread::sleep(Duration::from_millis(100));

    // Make a request to health check
    let resp = request()
        .method("GET")
        .path("/health")
        .reply(&warp::filters::path("health").and(warp::get()).and_then(|| async { 
            let response = serde_json::json!({"status": "OK"});
            Ok::<_, warp::Rejection>(warp::reply::json(&response))
        }))
        .await;

    assert_eq!(resp.status(), StatusCode::OK);

    // Stop server
    server.join().unwrap();
}

#[tokio::test]
async fn test_create_and_get_book() {
    // Start the server in a separate thread
    let server = thread::spawn(|| {
        tokio::runtime::Runtime::new().unwrap().block_on(async {
            let pool = sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
            sqlx::query(
                "CREATE TABLE books (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    isbn TEXT NOT NULL
                )"
            )
            .execute(&pool)
            .await
            .unwrap();

            let routes = warp::path("books")
                .and(warp::post())
                .and(warp::body::json())
                .and(warp::any().map(move || pool.clone()))
                .and_then(|book: serde_json::Value, pool| async {
                    let title = book.get("title").unwrap().as_str().unwrap().to_string();
                    let author = book.get("author").unwrap().as_str().unwrap().to_string();
                    let year = book.get("year").unwrap().as_i64().unwrap() as i32;
                    let isbn = book.get("isbn").unwrap().as_str().unwrap().to_string();
                    
                    let id = uuid::Uuid::new_v4().to_string();
                    sqlx::query(
                        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
                    )
                    .bind(&id)
                    .bind(&title)
                    .bind(&author)
                    .bind(year)
                    .bind(&isbn)
                    .execute(&pool)
                    .await
                    .unwrap();
                    
                    let response = serde_json::json!({
                        "id": id,
                        "title": title,
                        "author": author,
                        "year": year,
                        "isbn": isbn
                    });
                    Ok::<_, warp::Rejection>(warp::reply::with_status(warp::reply::json(&response), warp::http::StatusCode::CREATED))
                })
                .or(warp::path("books")
                    .and(warp::path::param::<String>())
                    .and(warp::get())
                    .and(warp::any().map(move || pool.clone()))
                    .and_then(|id: String, pool| async {
                        let result = sqlx::query_as::<_, serde_json::Value>(
                            "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
                        )
                        .bind(&id)
                        .fetch_one(&pool)
                        .await;
                        
                        match result {
                            Ok(row) => Ok::<_, warp::Rejection>(warp::reply::json(&row)),
                            Err(_) => Err(warp::reject::custom(BookError::BookNotFound)),
                        }
                    }));

            let addr = ([127, 0, 0, 1], 0);
            let listener = TcpListener::bind(addr).unwrap();
            let port = listener.local_addr().unwrap().port();
            warp::serve(routes).run(listener).await;
        });
    });

    // Give the server time to start
    thread::sleep(Duration::from_millis(100));

    // Test creating a book
    let create_resp = request()
        .method("POST")
        .path("/books")
        .json(&json!({
            "title": "Test Book",
            "author": "Test Author",
            "year": 2023,
            "isbn": "1234567890"
        }))
        .reply(&warp::filters::path("books")
            .and(warp::post())
            .and(warp::body::json())
            .and_then(|book: serde_json::Value| async {
                let title = book.get("title").unwrap().as_str().unwrap().to_string();
                let author = book.get("author").unwrap().as_str().unwrap().to_string();
                let year = book.get("year").unwrap().as_i64().unwrap() as i32;
                let isbn = book.get("isbn").unwrap().as_str().unwrap().to_string();
                
                let id = uuid::Uuid::new_v4().to_string();
                let pool = sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
                sqlx::query(
                    "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
                )
                .bind(&id)
                .bind(&title)
                .bind(&author)
                .bind(year)
                .bind(&isbn)
                .execute(&pool)
                .await
                .unwrap();
                
                let response = serde_json::json!({
                    "id": id,
                    "title": title,
                    "author": author,
                    "year": year,
                    "isbn": isbn
                });
                Ok::<_, warp::Rejection>(warp::reply::with_status(warp::reply::json(&response), warp::http::StatusCode::CREATED))
            }))
        .await;

    assert_eq!(create_resp.status(), StatusCode::CREATED);

    // Extract the created book's ID
    let body = serde_json::from_slice::<serde_json::Value>(&create_resp.body()).unwrap();
    let book_id = body.get("id").unwrap().as_str().unwrap().to_string();

    // Test getting the book
    let get_resp = request()
        .method("GET")
        .path(&format!("/books/{}", book_id))
        .reply(&warp::filters::path("books")
            .and(warp::path::param::<String>())
            .and(warp::get())
            .and_then(|id: String| async {
                let pool = sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
                let result = sqlx::query_as::<_, serde_json::Value>(
                    "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
                )
                .bind(&id)
                .fetch_one(&pool)
                .await;
                
                match result {
                    Ok(row) => Ok::<_, warp::Rejection>(warp::reply::json(&row)),
                    Err(_) => Err(warp::reject::custom(BookError::BookNotFound)),
                }
            }))
        .await;

    assert_eq!(get_resp.status(), StatusCode::OK);

    // Stop server
    server.join().unwrap();
}

#[tokio::test]
async fn test_validation_errors() {
    // Test creating a book with missing required fields
    let create_resp = request()
        .method("POST")
        .path("/books")
        .json(&json!({
            "title": "",
            "author": "Test Author",
            "year": 2023,
            "isbn": "1234567890"
        }))
        .reply(&warp::filters::path("books")
            .and(warp::post())
            .and(warp::body::json())
            .and_then(|book: serde_json::Value| async {
                // Validation check
                let title = book.get("title").unwrap().as_str().unwrap();
                if title.is_empty() {
                    return Err(warp::reject::custom(BookError::InvalidInput("Title is required".to_string())));
                }
                let author = book.get("author").unwrap().as_str().unwrap();
                if author.is_empty() {
                    return Err(warp::reject::custom(BookError::InvalidInput("Author is required".to_string())));
                }
                
                let id = uuid::Uuid::new_v4().to_string();
                let pool = sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
                sqlx::query(
                    "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
                )
                .bind(&id)
                .bind(&title)
                .bind(&author)
                .bind(2023)
                .bind("1234567890")
                .execute(&pool)
                .await
                .unwrap();
                
                let response = serde_json::json!({
                    "id": id,
                    "title": title,
                    "author": author,
                    "year": 2023,
                    "isbn": "1234567890"
                });
                Ok::<_, warp::Rejection>(warp::reply::with_status(warp::reply::json(&response), warp::http::StatusCode::CREATED))
            }))
        .await;

    assert_eq!(create_resp.status(), StatusCode::BAD_REQUEST);

    // Test creating a book with missing author
    let create_resp2 = request()
        .method("POST")
        .path("/books")
        .json(&json!({
            "title": "Test Book",
            "author": "",
            "year": 2023,
            "isbn": "1234567890"
        }))
        .reply(&warp::filters::path("books")
            .and(warp::post())
            .and(warp::body::json())
            .and_then(|book: serde_json::Value| async {
                // Validation check
                let title = book.get("title").unwrap().as_str().unwrap();
                if title.is_empty() {
                    return Err(warp::reject::custom(BookError::InvalidInput("Title is required".to_string())));
                }
                let author = book.get("author").unwrap().as_str().unwrap();
                if author.is_empty() {
                    return Err(warp::reject::custom(BookError::InvalidInput("Author is required".to_string())));
                }
                
                let id = uuid::Uuid::new_v4().to_string();
                let pool = sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
                sqlx::query(
                    "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)"
                )
                .bind(&id)
                .bind(&title)
                .bind(&author)
                .bind(2023)
                .bind("1234567890")
                .execute(&pool)
                .await
                .unwrap();
                
                let response = serde_json::json!({
                    "id": id,
                    "title": title,
                    "author": author,
                    "year": 2023,
                    "isbn": "1234567890"
                });
                Ok::<_, warp::Rejection>(warp::reply::with_status(warp::reply::json(&response), warp::http::StatusCode::CREATED))
            }))
        .await;

    assert_eq!(create_resp2.status(), StatusCode::BAD_REQUEST);
}

// Custom error types for tests
#[derive(Debug)]
enum BookError {
    BookNotFound,
    InvalidInput(String),
}

impl warp::reject::Reject for BookError {}
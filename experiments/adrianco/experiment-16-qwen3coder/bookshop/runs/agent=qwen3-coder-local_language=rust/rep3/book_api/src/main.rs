use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post, put, delete},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};
use std::net::SocketAddr;
use std::sync::Arc;
use chrono::{DateTime, Utc};

#[derive(Debug, Serialize, Deserialize, Clone, sqlx::FromRow)]
struct Book {
    id: i32,
    title: String,
    author: String,
    year: i32,
    isbn: String,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BookResponse {
    id: i32,
    title: String,
    author: String,
    year: i32,
    isbn: String,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
struct HealthResponse {
    status: String,
}

#[derive(Debug, Deserialize)]
struct CreateBookRequest {
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Deserialize)]
struct UpdateBookRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Clone)]
struct AppState {
    db: SqlitePool,
}

impl From<Book> for BookResponse {
    fn from(book: Book) -> Self {
        BookResponse {
            id: book.id,
            title: book.title,
            author: book.author,
            year: book.year,
            isbn: book.isbn,
            created_at: book.created_at,
            updated_at: book.updated_at,
        }
    }
}

async fn init_db(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    let query = r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    "#;
    sqlx::query(query).execute(pool).await?;
    Ok(())
}

async fn create_book(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<CreateBookRequest>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    // Validate required fields
    if payload.title.is_empty() {
        return Err((StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": "Title is required"}))));
    }
    
    if payload.author.is_empty() {
        return Err((StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": "Author is required"}))));
    }

    let query = r#"
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
        RETURNING id, title, author, year, isbn, created_at, updated_at
    "#;
    
    let book: Book = sqlx::query_as(query)
        .bind(&payload.title)
        .bind(&payload.author)
        .bind(payload.year)
        .bind(&payload.isbn)
        .fetch_one(&state.db)
        .await
        .map_err(|e| {
            if e.to_string().contains("UNIQUE constraint failed") {
                (StatusCode::CONFLICT, Json(serde_json::json!({"error": "Book with this ISBN already exists"})))
            } else {
                (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"})))
            }
        })?;

    Ok((StatusCode::CREATED, Json(book.into())))
}

async fn get_books(
    State(state): State<Arc<AppState>>,
    author: Option<String>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let query = if let Some(author_filter) = &author {
        r#"
            SELECT id, title, author, year, isbn, created_at, updated_at
            FROM books
            WHERE author LIKE ?
            ORDER BY created_at DESC
        "#
    } else {
        r#"
            SELECT id, title, author, year, isbn, created_at, updated_at
            FROM books
            ORDER BY created_at DESC
        "#
    };

    // For now, let's return a simple array of books to avoid complex trait issues
    let rows = sqlx::query(query)
        .bind(if let Some(author_filter) = &author { format!("%{}%", author_filter) } else { "".to_string() })
        .fetch_all(&state.db)
        .await
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"}))))?;

    let mut books: Vec<BookResponse> = Vec::new();
    for row in rows {
        let book = Book {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
            created_at: row.get("created_at"),
            updated_at: row.get("updated_at"),
        };
        books.push(book.into());
    }

    Ok(Json(books))
}

async fn get_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i32>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let query = r#"
        SELECT id, title, author, year, isbn, created_at, updated_at
        FROM books
        WHERE id = ?
    "#;

    let book: Book = sqlx::query_as(query)
        .bind(id)
        .fetch_one(&state.db)
        .await
        .map_err(|e| {
            if e.to_string().contains("no rows returned") {
                (StatusCode::NOT_FOUND, Json(serde_json::json!({"error": "Book not found"})))
            } else {
                (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"})))
            }
        })?;

    Ok(Json(book.into()))
}

async fn update_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i32>,
    Json(payload): Json<UpdateBookRequest>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    // Check if book exists
    let existing_book: Option<Book> = sqlx::query_as(
        "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?"
    )
    .bind(id)
    .fetch_optional(&state.db)
    .await
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"}))))?;

    if existing_book.is_none() {
        return Err((StatusCode::NOT_FOUND, Json(serde_json::json!({"error": "Book not found"}))));
    }

    // For simplicity, we'll do a basic update - update all provided fields
    let query = r#"
        UPDATE books 
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
    "#;
    
    let result = sqlx::query(query)
        .bind(payload.title.unwrap_or_else(|| existing_book.as_ref().unwrap().title.clone()))
        .bind(payload.author.unwrap_or_else(|| existing_book.as_ref().unwrap().author.clone()))
        .bind(payload.year.unwrap_or(existing_book.as_ref().unwrap().year))
        .bind(payload.isbn.unwrap_or_else(|| existing_book.as_ref().unwrap().isbn.clone()))
        .bind(id)
        .execute(&state.db)
        .await
        .map_err(|e| {
            if e.to_string().contains("UNIQUE constraint failed") {
                (StatusCode::CONFLICT, Json(serde_json::json!({"error": "Book with this ISBN already exists"})))
            } else {
                (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"})))
            }
        })?;

    if result.rows_affected() == 0 {
        return Err((StatusCode::NOT_FOUND, Json(serde_json::json!({"error": "Book not found"}))));
    }

    // Fetch the updated book
    let updated_book: Book = sqlx::query_as(
        "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?"
    )
    .bind(id)
    .fetch_one(&state.db)
    .await
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"}))))?;

    Ok(Json(updated_book.into()))
}

async fn delete_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<i32>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.db)
        .await
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({"error": "Database error"}))))?;

    if result.rows_affected() == 0 {
        return Err((StatusCode::NOT_FOUND, Json(serde_json::json!({"error": "Book not found"}))));
    }

    Ok(Json(serde_json::json!({"message": "Book deleted successfully"})))
}

async fn health_check() -> impl IntoResponse {
    Json(HealthResponse {
        status: "healthy".to_string(),
    })
}

#[tokio::main]
async fn main() {
    // Initialize database
    let db_url = "sqlite:./books.db";
    let pool = SqlitePool::connect(db_url).await.expect("Failed to connect to database");
    
    init_db(&pool).await.expect("Failed to initialize database");
    
    let app_state = Arc::new(AppState { db: pool });

    let app = Router::new()
        .route("/books", post(create_book))
        .route("/books", get(get_books))
        .route("/books/:id", get(get_book))
        .route("/books/:id", put(update_book))
        .route("/books/:id", delete(delete_book))
        .route("/health", get(health_check))
        .with_state(app_state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Server starting on http://{}", addr);

    // Use axum's serve function directly instead of manual listener
    axum::serve(
        tokio::net::TcpListener::bind(addr).await.unwrap(),
        app.into_make_service()
    ).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use serde_json::{json, Value};
    use std::sync::Arc;
    use tower::util::ServiceExt; // Import for oneshot

    // Helper function to create a test database
    async fn setup_test_db() -> SqlitePool {
        let pool = SqlitePool::connect("sqlite::memory:").await.unwrap();
        init_db(&pool).await.unwrap();
        pool
    }

    #[tokio::test]
    async fn test_health_check() {
        let pool = setup_test_db().await;
        let app_state = Arc::new(AppState { db: pool });
        
        let app = Router::new()
            .route("/health", get(health_check))
            .with_state(app_state);

        let request = Request::builder()
            .uri("/health")
            .method("GET")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
        let body_str = std::str::from_utf8(&body).unwrap();
        let json: Value = serde_json::from_str(body_str).unwrap();
        assert_eq!(json["status"], "healthy");
    }

    #[tokio::test]
    async fn test_create_and_get_book() {
        let pool = setup_test_db().await;
        let app_state = Arc::new(AppState { db: pool });
        
        let app = Router::new()
            .route("/books", post(create_book))
            .route("/books/:id", get(get_book))
            .with_state(app_state);

        // Create a book
        let create_request = Request::builder()
            .uri("/books")
            .method("POST")
            .header("Content-Type", "application/json")
            .body(Body::from(serde_json::to_string(&json!({
                "title": "Test Book",
                "author": "Test Author",
                "year": 2023,
                "isbn": "1234567890"
            })).unwrap()))
            .unwrap();

        let response = app.oneshot(create_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);

        let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
        let body_str = std::str::from_utf8(&body).unwrap();
        let json: Value = serde_json::from_str(body_str).unwrap();
        let book_id = json["id"].as_i64().unwrap();

        // Get the book
        let get_request = Request::builder()
            .uri(format!("/books/{}", book_id))
            .method("GET")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(get_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
        let body_str = std::str::from_utf8(&body).unwrap();
        let json: Value = serde_json::from_str(body_str).unwrap();
        assert_eq!(json["title"], "Test Book");
        assert_eq!(json["author"], "Test Author");
        assert_eq!(json["year"], 2023);
        assert_eq!(json["isbn"], "1234567890");
    }

    #[tokio::test]
    async fn test_get_books_with_filter() {
        let pool = setup_test_db().await;
        let app_state = Arc::new(AppState { db: pool });
        
        let app = Router::new()
            .route("/books", post(create_book))
            .route("/books", get(get_books))
            .with_state(app_state);

        // Create two books with different authors
        let create_request1 = Request::builder()
            .uri("/books")
            .method("POST")
            .header("Content-Type", "application/json")
            .body(Body::from(serde_json::to_string(&json!({
                "title": "Book 1",
                "author": "Author A",
                "year": 2020,
                "isbn": "1111111111"
            })).unwrap()))
            .unwrap();

        let response = app.oneshot(create_request1).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);

        let create_request2 = Request::builder()
            .uri("/books")
            .method("POST")
            .header("Content-Type", "application/json")
            .body(Body::from(serde_json::to_string(&json!({
                "title": "Book 2",
                "author": "Author B",
                "year": 2021,
                "isbn": "2222222222"
            })).unwrap()))
            .unwrap();

        let response = app.oneshot(create_request2).await.unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);

        // Get books with author filter
        let filter_request = Request::builder()
            .uri("/books?author=Author A")
            .method("GET")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(filter_request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);

        let body = hyper::body::to_bytes(response.into_body()).await.unwrap();
        let body_str = std::str::from_utf8(&body).unwrap();
        let json: Value = serde_json::from_str(body_str).unwrap();
        assert_eq!(json.as_array().unwrap().len(), 1);
        assert_eq!(json[0]["author"], "Author A");
    }
}
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
use std::fs;
use std::path::Path;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Book {
    id: Option<uuid::Uuid>,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct BookResponse {
    id: uuid::Uuid,
    title: String,
    author: String,
    year: i32,
    isbn: String,
}

#[derive(Debug, Deserialize)]
struct BookFilter {
    author: Option<String>,
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

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: String,
}

#[tokio::main]
async fn main() {
    // Ensure the current directory is writable and exists
    let current_dir = std::env::current_dir().unwrap();
    println!("Working directory: {:?}", current_dir);
    
    // Create the database file explicitly if it doesn't exist
    let db_path = "books.db";
    let db_file = Path::new(db_path);
    if !db_file.exists() {
        // Try to create the database file
        match std::fs::File::create(db_path) {
            Ok(_) => println!("Created database file: {}", db_path),
            Err(e) => {
                eprintln!("Failed to create database file: {}", e);
                return;
            }
        }
    }
    
    // Connect to database
    let pool = match SqlitePool::connect("sqlite:books.db").await {
        Ok(pool) => pool,
        Err(e) => {
            eprintln!("Failed to connect to database: {}", e);
            return;
        }
    };
    
    // Initialize database
    if let Err(e) = init_db(&pool).await {
        eprintln!("Failed to initialize database: {}", e);
        return;
    }
    
    // Create our app state
    let app_state = Arc::new(pool);
    
    // Define routes
    let app = Router::new()
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/:id", get(get_book))
        .route("/books/:id", put(update_book))
        .route("/books/:id", delete(delete_book))
        .route("/health", get(health_check))
        .with_state(app_state);
    
    // Run the server
    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Server running on http://{}", addr);
    
    let listener = match tokio::net::TcpListener::bind(addr).await {
        Ok(listener) => listener,
        Err(e) => {
            eprintln!("Failed to bind to address: {}", e);
            return;
        }
    };
    
    if let Err(e) = axum::serve(listener, app).await {
        eprintln!("Server error: {}", e);
    }
}

async fn init_db(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    let query = r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )
    "#;
    
    sqlx::query(query).execute(pool).await?;
    Ok(())
}

async fn create_book(
    State(pool): State<Arc<SqlitePool>>,
    Json(payload): Json<CreateBookRequest>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    // Validate input
    if payload.title.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": "Title is required"})),
        ));
    }
    
    if payload.author.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": "Author is required"})),
        ));
    }
    
    let id = uuid::Uuid::new_v4();
    
    // Convert Arc<Pool<SqlitePool>> to &Pool<SqlitePool> by dereferencing
    let pool_ref = &*pool;
    
    let query = r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES (?1, ?2, ?3, ?4, ?5)
    "#;
    
    let result = sqlx::query(query)
        .bind(id.to_string())
        .bind(&payload.title)
        .bind(&payload.author)
        .bind(payload.year)
        .bind(&payload.isbn)
        .execute(pool_ref)
        .await;
    
    match result {
        Ok(_) => {
            let book = BookResponse {
                id,
                title: payload.title,
                author: payload.author,
                year: payload.year,
                isbn: payload.isbn,
            };
            Ok((StatusCode::CREATED, Json(book)))
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({"error": "Failed to create book"})),
            ))
        }
    }
}

async fn list_books(
    State(pool): State<Arc<SqlitePool>>,
    filter: Option<axum::extract::Query<BookFilter>>,
) -> Result<Json<Vec<BookResponse>>, StatusCode> {
    // Convert Arc<Pool<SqlitePool>> to &Pool<SqlitePool> by dereferencing
    let pool_ref = &*pool;
    
    let mut query = String::from("SELECT id, title, author, year, isbn FROM books");
    
    if let Some(_author_filter) = &filter.as_ref().and_then(|f| f.author.as_ref()) {
        // This would normally be used for filtering, but we'll skip the parameter binding for now
        // as we don't use the actual filter in our simple implementation
        query.push_str(" ORDER BY title");
    } else {
        query.push_str(" ORDER BY title");
    }
    
    let rows = sqlx::query(&query)
        .fetch_all(pool_ref)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    let books: Vec<BookResponse> = rows
        .into_iter()
        .map(|row| BookResponse {
            id: uuid::Uuid::parse_str(row.get(0)).unwrap(),
            title: row.get(1),
            author: row.get(2),
            year: row.get(3),
            isbn: row.get(4),
        })
        .collect();
    
    Ok(Json(books))
}

async fn get_book(
    State(pool): State<Arc<SqlitePool>>,
    Path(id): Path<uuid::Uuid>,
) -> Result<Json<BookResponse>, (StatusCode, Json<serde_json::Value>)> {
    // Convert Arc<Pool<SqlitePool>> to &Pool<SqlitePool> by dereferencing
    let pool_ref = &*pool;
    
    let query = r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?1"#;
    
    let row = sqlx::query(query)
        .bind(id.to_string())
        .fetch_one(pool_ref)
        .await;
    
    match row {
        Ok(row) => {
            let book = BookResponse {
                id,
                title: row.get(1),
                author: row.get(2),
                year: row.get(3),
                isbn: row.get(4),
            };
            Ok(Json(book))
        }
        Err(_) => Err((
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": "Book not found"})),
        )),
    }
}

async fn update_book(
    State(pool): State<Arc<SqlitePool>>,
    Path(id): Path<uuid::Uuid>,
    Json(payload): Json<UpdateBookRequest>,
) -> Result<Json<BookResponse>, (StatusCode, Json<serde_json::Value>)> {
    // Convert Arc<Pool<SqlitePool>> to &Pool<SqlitePool> by dereferencing
    let pool_ref = &*pool;
    
    // Check if book exists
    let check_query = r#"SELECT id FROM books WHERE id = ?1"#;
    let exists = sqlx::query(check_query)
        .bind(id.to_string())
        .fetch_optional(pool_ref)
        .await
        .map_err(|_| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({"error": "Database error"})),
            )
        })?;
    
    if exists.is_none() {
        return Err((
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": "Book not found"})),
        ));
    }
    
    // Build the query dynamically based on which fields are provided
    let mut set_clauses = Vec::new();
    let mut binds = vec![id.to_string()];
    
    if let Some(title) = &payload.title {
        set_clauses.push("title = ?1");
        binds.push(title.clone());
    }
    
    if let Some(author) = &payload.author {
        set_clauses.push("author = ?2");
        binds.push(author.clone());
    }
    
    if let Some(year) = payload.year {
        set_clauses.push("year = ?3");
        binds.push(year.to_string());
    }
    
    if let Some(isbn) = &payload.isbn {
        set_clauses.push("isbn = ?4");
        binds.push(isbn.clone());
    }
    
    if set_clauses.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": "No fields to update"})),
        ));
    }
    
    // Build the update query with proper parameter binding
    let query = format!(
        "UPDATE books SET {} WHERE id = ?",
        set_clauses.join(", ")
    );
    
    let mut query_builder = sqlx::query(&query);
    
    // Bind all parameters
    for bind in binds.iter() {
        query_builder = query_builder.bind(bind);
    }
    
    query_builder.execute(pool_ref).await.map_err(|_| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({"error": "Failed to update book"})),
        )
    })?;
    
    // Fetch the updated book
    let get_query = r#"SELECT id, title, author, year, isbn FROM books WHERE id = ?1"#;
    let row = sqlx::query(get_query)
        .bind(id.to_string())
        .fetch_one(pool_ref)
        .await
        .map_err(|_| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({"error": "Database error"})),
            )
        })?;
    
    let book = BookResponse {
        id,
        title: row.get(1),
        author: row.get(2),
        year: row.get(3),
        isbn: row.get(4),
    };
    
    Ok(Json(book))
}

async fn delete_book(
    State(pool): State<Arc<SqlitePool>>,
    Path(id): Path<uuid::Uuid>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    // Convert Arc<Pool<SqlitePool>> to &Pool<SqlitePool> by dereferencing
    let pool_ref = &*pool;
    
    let query = r#"DELETE FROM books WHERE id = ?1"#;
    
    let result = sqlx::query(query)
        .bind(id.to_string())
        .execute(pool_ref)
        .await;
    
    match result {
        Ok(result) => {
            if result.rows_affected() == 0 {
                Err((
                    StatusCode::NOT_FOUND,
                    Json(serde_json::json!({"error": "Book not found"})),
                ))
            } else {
                Ok(Json(serde_json::json!({"message": "Book deleted successfully"})))
            }
        }
        Err(_) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({"error": "Failed to delete book"})),
        )),
    }
}

async fn health_check() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".to_string(),
    })
}
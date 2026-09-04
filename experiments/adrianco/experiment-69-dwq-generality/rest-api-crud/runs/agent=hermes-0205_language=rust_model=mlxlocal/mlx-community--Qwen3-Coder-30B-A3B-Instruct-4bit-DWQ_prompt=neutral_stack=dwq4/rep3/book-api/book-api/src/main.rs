use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
    routing::{delete, get, post, put},
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePool, Row};
use std::sync::Arc;

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Book {
    id: String,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct HealthResponse {
    status: String,
}

#[derive(Clone)]
struct AppState {
    pool: SqlitePool,
}

async fn init_db(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    let query = r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );
    "#;
    
    sqlx::execute(query).execute(pool).await?;
    Ok(())
}

// Create a new book
async fn create_book(
    State(state): State<Arc<AppState>>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, StatusCode> {
    if input.title.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if input.author.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let id = uuid::Uuid::new_v4().to_string();
    let query = r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES (?, ?, ?, ?, ?)
        RETURNING id, title, author, year, isbn
    "#;

    let book = sqlx::query_as::<_, Book>(query)
        .bind(&id)
        .bind(&input.title)
        .bind(&input.author)
        .bind(input.year)
        .bind(input.isbn.as_deref())
        .fetch_one(&state.pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(book))
}

// Get all books with optional author filter
async fn get_books(
    State(state): State<Arc<AppState>>,
    author: Option<String>,
) -> Result<Json<Vec<Book>>, StatusCode> {
    let query = if let Some(author) = author {
        "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
    } else {
        "SELECT id, title, author, year, isbn FROM books"
    };

    let books = sqlx::query_as::<_, Book>(query)
        .bind(author)
        .fetch_all(&state.pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(books))
}

// Get a single book by ID
async fn get_book_by_id(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<Json<Book>, StatusCode> {
    let query = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
    
    let book = sqlx::query_as::<_, Book>(query)
        .bind(&id)
        .fetch_one(&state.pool)
        .await
        .map_err(|_| StatusCode::NOT_FOUND)?;

    Ok(Json(book))
}

// Update a book
async fn update_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, StatusCode> {
    if input.title.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }
    if input.author.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let query = r#"
        UPDATE books
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
        RETURNING id, title, author, year, isbn
    "#;

    let book = sqlx::query_as::<_, Book>(query)
        .bind(&input.title)
        .bind(&input.author)
        .bind(input.year)
        .bind(input.isbn.as_deref())
        .bind(&id)
        .fetch_one(&state.pool)
        .await
        .map_err(|_| StatusCode::NOT_FOUND)?;

    Ok(Json(book))
}

// Delete a book
async fn delete_book(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> Result<StatusCode, StatusCode> {
    let query = "DELETE FROM books WHERE id = ?";
    
    let result = sqlx::query(query)
        .bind(&id)
        .execute(&state.pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    if result.rows_affected() == 0 {
        return Err(StatusCode::NOT_FOUND);
    }

    Ok(StatusCode::NO_CONTENT)
}

// Health check endpoint
async fn health_check() -> Result<Json<HealthResponse>, StatusCode> {
    Ok(Json(HealthResponse {
        status: "OK".to_string(),
    }))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create a database pool
    let pool = SqlitePool::connect("sqlite:books.db").await?;
    
    // Initialize the database
    init_db(&pool).await?;
    
    // Create the application state
    let app_state = Arc::new(AppState { pool });
    
    // Create the router - fixed route setup
    let app = Router::new()
        .route("/books", post(create_book).get(get_books))
        .route("/books/:id", get(get_book_by_id).put(update_book).delete(delete_book))
        .route("/health", get(health_check))
        .with_state(app_state);
    
    // Start the server
    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080").await?;
    println!("Server running on http://127.0.0.1:8080");
    axum::serve(listener, app).await?;
    
    Ok(())
}
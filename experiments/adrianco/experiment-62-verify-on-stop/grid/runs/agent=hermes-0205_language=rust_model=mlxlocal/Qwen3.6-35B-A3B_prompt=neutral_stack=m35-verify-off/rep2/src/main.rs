use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
    routing::{delete, get, post, put},
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{Row, SqlitePool};

// --- Models ---

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateBookRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpdateBookRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize, Default)]
struct QueryParams {
    #[serde(default)]
    author: Option<String>,
}

// --- State ---

#[derive(Clone)]
struct AppState {
    pool: SqlitePool,
}

// --- Helpers ---

fn not_found() -> (StatusCode, Json<serde_json::Value>) {
    (
        StatusCode::NOT_FOUND,
        Json(serde_json::json!({ "error": "Book not found" })),
    )
}

fn validation_error(msg: &str) -> (StatusCode, Json<serde_json::Value>) {
    (
        StatusCode::BAD_REQUEST,
        Json(serde_json::json!({ "error": msg })),
    )
}

fn row_to_book(row: &sqlx::sqlite::SqliteRow) -> Book {
    Book {
        id: row.get("id"),
        title: row.get("title"),
        author: row.get("author"),
        year: row.get("year"),
        isbn: row.get("isbn"),
    }
}

// --- Database init ---

async fn init_db() -> SqlitePool {
    let pool = SqlitePool::connect("sqlite::memory:")
        .await
        .expect("Failed to create database pool");

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        "#,
    )
    .execute(&pool)
    .await
    .expect("Failed to create books table");

    pool
}

// --- Endpoints ---

async fn create_book(
    State(state): State<AppState>,
    Json(req): Json<CreateBookRequest>,
) -> Result<Json<Book>, (StatusCode, Json<serde_json::Value>)> {
    let title = req
        .title
        .clone()
        .ok_or_else(|| validation_error("title is required"))?;
    let author = req
        .author
        .clone()
        .ok_or_else(|| validation_error("author is required"))?;

    let row = sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind(&title)
        .bind(&author)
        .bind(req.year)
        .bind(req.isbn.clone())
        .execute(&state.pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({ "error": format!("Database error: {}", e) })),
            )
        })?;

    let id = row.last_insert_rowid();

    let book = Book {
        id,
        title,
        author,
        year: req.year,
        isbn: req.isbn,
    };

    Ok(Json(book))
}

async fn list_books(
    State(state): State<AppState>,
    params: Query<QueryParams>,
) -> Json<Vec<Book>> {
    let rows = match &params.author {
        Some(author) => {
            sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE author = ?")
                .bind(author)
                .fetch_all(&state.pool)
                .await
        }
        None => {
            sqlx::query("SELECT id, title, author, year, isbn FROM books")
                .fetch_all(&state.pool)
                .await
        }
    };

    match rows {
        Ok(rows) => {
            let books: Vec<Book> = rows.into_iter().map(|r| row_to_book(&r)).collect();
            Json(books)
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            Json(vec![])
        }
    }
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, (StatusCode, Json<serde_json::Value>)> {
    let result = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&state.pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({ "error": format!("Database error: {}", e) })),
            )
        })?;

    match result {
        Some(row) => Ok(Json(row_to_book(&row))),
        None => Err(not_found()),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(req): Json<UpdateBookRequest>,
) -> Result<Json<Book>, (StatusCode, Json<serde_json::Value>)> {
    // Check if book exists
    let existing = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&state.pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({ "error": format!("Database error: {}", e) })),
            )
        })?;

    let book = match existing {
        Some(row) => row_to_book(&row),
        None => return Err(not_found()),
    };

    // Use the new value if provided, otherwise keep the existing one
    let new_title = match req.title {
        Some(t) => t,
        None => book.title,
    };
    let new_author = match req.author {
        Some(a) => a,
        None => book.author,
    };
    let new_year = match req.year {
        Some(y) => y,
        None => book.year.unwrap_or(0),
    };
    let new_isbn = match req.isbn {
        Some(i) => Some(i),
        None => book.isbn,
    };

    sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&new_title)
    .bind(&new_author)
    .bind(Some(new_year))
    .bind(&new_isbn)
    .bind(id)
    .execute(&state.pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "error": format!("Database error: {}", e) })),
        )
    })?;

    Ok(Json(Book {
        id,
        title: new_title,
        author: new_author,
        year: Some(new_year),
        isbn: new_isbn,
    }))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, (StatusCode, Json<serde_json::Value>)> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&state.pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({ "error": format!("Database error: {}", e) })),
            )
        })?;

    if result.rows_affected() == 0 {
        Err(not_found())
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}

async fn health_check() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "healthy" }))
}

#[tokio::main]
async fn main() {
    let pool = init_db().await;
    let state = AppState { pool };

    let app = Router::new()
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book))
        .route("/books/{id}", put(update_book))
        .route("/books/{id}", delete(delete_book))
        .route("/health", get(health_check))
        .with_state(state);

    let addr = "127.0.0.1:3000";
    println!("Server running at http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests;

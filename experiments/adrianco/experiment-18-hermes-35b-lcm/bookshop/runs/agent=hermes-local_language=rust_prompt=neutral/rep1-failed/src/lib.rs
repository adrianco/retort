use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
    routing::{delete, get, post, put},
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{Row, SqlitePool};
use tower_http::cors::CorsLayer;

// ─── Models ──────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct QueryParams {
    pub author: Option<String>,
}

// ─── DB helpers ──────────────────────────────────────────────────────────────

fn book_from_row(row: sqlx::sqlite::SqliteRow) -> Book {
    Book {
        id: row.get("id"),
        title: row.get("title"),
        author: row.get("author"),
        year: row.get("year"),
        isbn: row.get("isbn"),
    }
}

// ─── Handlers ────────────────────────────────────────────────────────────────

async fn health_check() -> (StatusCode, String) {
    (StatusCode::OK, "OK".to_string())
}

async fn create_book(
    State(pool): State<SqlitePool>,
    Json(req): Json<CreateBookRequest>,
) -> Result<(StatusCode, Json<Book>), (StatusCode, String)> {
    let title = req.title.clone().ok_or_else(|| {
        (StatusCode::BAD_REQUEST, "title is required".to_string())
    })?;
    let author = req.author.clone().ok_or_else(|| {
        (StatusCode::BAD_REQUEST, "author is required".to_string())
    })?;

    let row = sqlx::query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *",
    )
    .bind(title)
    .bind(author)
    .bind(req.year)
    .bind(req.isbn)
    .fetch_one(&pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Database error: {}", e),
        )
    })?;

    Ok((StatusCode::CREATED, Json(book_from_row(row))))
}

async fn list_books(
    State(pool): State<SqlitePool>,
    Query(params): Query<QueryParams>,
) -> Json<Vec<Book>> {
    let books: Vec<Book> = match params.author {
        Some(ref author) => {
            let rows = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE author = ?")
                .bind(author)
                .fetch_all(&pool)
                .await
                .unwrap_or_default();
            rows.into_iter().map(book_from_row).collect()
        }
        None => {
            let rows = sqlx::query("SELECT id, title, author, year, isbn FROM books")
                .fetch_all(&pool)
                .await
                .unwrap_or_default();
            rows.into_iter().map(book_from_row).collect()
        }
    };

    Json(books)
}

async fn get_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, (StatusCode, String)> {
    let book = sqlx::query("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id)
        .fetch_optional(&pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Database error: {}", e),
            )
        })?;

    match book {
        Some(row) => Ok(Json(book_from_row(row))),
        None => Err((StatusCode::NOT_FOUND, "Book not found".to_string())),
    }
}

async fn update_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
    Json(req): Json<UpdateBookRequest>,
) -> Result<Json<Book>, (StatusCode, String)> {
    let existing: Option<sqlx::sqlite::SqliteRow> = sqlx::query(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(id)
    .fetch_optional(&pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Database error: {}", e),
        )
    })?;

    match existing {
        Some(row) => {
            let title: String = row.get("title");
            let author: String = row.get("author");
            let year: Option<i32> = row.get("year");
            let isbn: Option<String> = row.get("isbn");

            let new_title = req.title.unwrap_or(title);
            let new_author = req.author.unwrap_or(author);
            let new_year = req.year.or(year);
            let new_isbn = req.isbn.or(isbn);

            let row = sqlx::query(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING *",
            )
            .bind(new_title)
            .bind(new_author)
            .bind(new_year)
            .bind(new_isbn)
            .bind(id)
            .fetch_one(&pool)
            .await
            .map_err(|e| {
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    format!("Database error: {}", e),
                )
            })?;

            Ok(Json(book_from_row(row)))
        }
        None => Err((StatusCode::NOT_FOUND, "Book not found".to_string())),
    }
}

async fn delete_book(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<StatusCode, (StatusCode, String)> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(id)
        .execute(&pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Database error: {}", e),
            )
        })?;

    if result.rows_affected() == 0 {
        Err((StatusCode::NOT_FOUND, "Book not found".to_string()))
    } else {
        Ok(StatusCode::NO_CONTENT)
    }
}

// ─── DB Init ─────────────────────────────────────────────────────────────────

pub async fn init_db(pool: &SqlitePool) {
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )
    .execute(pool)
    .await
    .expect("Failed to create books table");
}

// ─── Router ──────────────────────────────────────────────────────────────────

pub fn create_router(pool: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book))
        .route("/books/{id}", put(update_book))
        .route("/books/{id}", delete(delete_book))
        .layer(CorsLayer::permissive())
        .with_state(pool)
}

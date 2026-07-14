use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Response,
    routing::{delete, get, post, put, Router},
    Json,
};
use serde::{Deserialize, Serialize};
use sqlx::{SqlitePool, Row};
use tower_http::cors::CorsLayer;

// ─── Models ───────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Book {
    pub id: String,
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
pub struct AuthorFilter {
    pub author: Option<String>,
}

// ─── Database ─────────────────────────────────────────────────────────────────

pub async fn create_pool(db_url: &str) -> SqlitePool {
    let pool = SqlitePool::connect(db_url).await.unwrap();
    sqlx::migrate!().run(&pool).await.unwrap();
    pool
}

#[derive(Clone)]
pub struct AppState {
    pub pool: SqlitePool,
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

async fn health_check() -> Response<String> {
    Response::builder()
        .status(StatusCode::OK)
        .header("content-type", "application/json")
        .body(r#"{"status":"ok"}"#.to_string())
        .unwrap()
}

async fn create_book(
    State(state): State<AppState>,
    Json(req): Json<CreateBookRequest>,
) -> Result<Json<Book>, (StatusCode, Json<serde_json::Value>)> {
    let title = req.title.clone().unwrap_or_default();
    if title.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": "title is required"})),
        ));
    }

    let author = req.author.clone().unwrap_or_default();
    if author.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": "author is required"})),
        ));
    }

    let id = uuid::Uuid::new_v4().to_string();

    sqlx::query(
        r#"
        INSERT INTO books (id, title, author, year, isbn)
        VALUES (?, ?, ?, ?, ?)
        "#,
    )
    .bind(&id)
    .bind(&title)
    .bind(&author)
    .bind(req.year)
    .bind(&req.isbn)
    .execute(&state.pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({"error": e.to_string()})),
        )
    })?;

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
    Query(filter): Query<AuthorFilter>,
) -> Result<Json<Vec<Book>>, (StatusCode, Json<serde_json::Value>)> {
    let books = if let Some(author) = &filter.author {
        sqlx::query(
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?",
        )
        .bind(format!("%{}%", author))
        .fetch_all(&state.pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({"error": e.to_string()})),
            )
        })?
    } else {
        sqlx::query("SELECT id, title, author, year, isbn FROM books")
            .fetch_all(&state.pool)
            .await
            .map_err(|e| {
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(serde_json::json!({"error": e.to_string()})),
                )
            })?
    };

    let books: Vec<Book> = books.iter().map(|row| {
        Book {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        }
    }).collect();

    Ok(Json(books))
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Book>, (StatusCode, Json<serde_json::Value>)> {
    let row = sqlx::query(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_one(&state.pool)
    .await;

    match row {
        Ok(row) => Ok(Json(Book {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        })),
        Err(sqlx::Error::RowNotFound) => Err((
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": "book not found"})),
        )),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({"error": e.to_string()})),
        )),
    }
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(req): Json<UpdateBookRequest>,
) -> Result<Json<Book>, (StatusCode, Json<serde_json::Value>)> {
    let existing = sqlx::query(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    )
    .bind(&id)
    .fetch_one(&state.pool)
    .await;

    let mut book = match existing {
        Ok(row) => Book {
            id: row.get("id"),
            title: row.get("title"),
            author: row.get("author"),
            year: row.get("year"),
            isbn: row.get("isbn"),
        },
        Err(sqlx::Error::RowNotFound) => {
            return Err((
                StatusCode::NOT_FOUND,
                Json(serde_json::json!({"error": "book not found"})),
            ))
        }
        Err(e) => {
            return Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({"error": e.to_string()})),
            ))
        }
    };

    if let Some(title) = &req.title {
        if title.is_empty() {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"error": "title cannot be empty"})),
            ));
        }
        book.title = title.clone();
    }
    if let Some(author) = &req.author {
        if author.is_empty() {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"error": "author cannot be empty"})),
            ));
        }
        book.author = author.clone();
    }
    if let Some(year) = req.year {
        book.year = Some(year);
    }
    if req.isbn.is_some() {
        book.isbn = req.isbn.clone();
    }

    let updated = sqlx::query(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    )
    .bind(&book.title)
    .bind(&book.author)
    .bind(book.year)
    .bind(&book.isbn)
    .bind(&id)
    .execute(&state.pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({"error": e.to_string()})),
        )
    })?;

    if updated.rows_affected() == 0 {
        return Err((
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": "book not found"})),
        ));
    }

    Ok(Json(book))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, Json<serde_json::Value>)> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(&id)
        .execute(&state.pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({"error": e.to_string()})),
            )
        })?;

    if result.rows_affected() == 0 {
        return Err((
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": "book not found"})),
        ));
    }

    Ok(StatusCode::NO_CONTENT)
}

// ─── Router ───────────────────────────────────────────────────────────────────

pub fn create_router(pool: SqlitePool) -> Router {
    let state = AppState { pool };

    Router::new()
        .route("/health", get(health_check))
        .route("/books", post(create_book))
        .route("/books", get(list_books))
        .route("/books/{id}", get(get_book))
        .route("/books/{id}", put(update_book))
        .route("/books/{id}", delete(delete_book))
        .layer(CorsLayer::permissive())
        .with_state(state)
}

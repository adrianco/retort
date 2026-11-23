use axum::{
    Json, Router,
    extract::{
        Path, Query, State,
        rejection::{JsonRejection, PathRejection, QueryRejection},
    },
    http::{StatusCode, header},
    response::{IntoResponse, Response},
    routing::get,
};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sqlx::{
    FromRow, SqlitePool,
    sqlite::{SqliteConnectOptions, SqlitePoolOptions},
};

#[derive(Debug, FromRow, Serialize)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl BookInput {
    fn validate(body: Result<Json<Self>, JsonRejection>) -> Result<Self, ApiError> {
        let Json(book) = body.map_err(|error| ApiError(error.status(), error.body_text()))?;
        if book.title.trim().is_empty() || book.author.trim().is_empty() {
            return Err(ApiError::new(
                StatusCode::UNPROCESSABLE_ENTITY,
                "title and author must be non-blank",
            ));
        }
        Ok(book)
    }
}

#[derive(Deserialize)]
struct BookFilter {
    author: Option<String>,
}

struct ApiError(StatusCode, String);

impl ApiError {
    fn new(status: StatusCode, message: &str) -> Self {
        Self(status, message.to_owned())
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(json!({ "error": self.1 }))).into_response()
    }
}

impl From<sqlx::Error> for ApiError {
    fn from(error: sqlx::Error) -> Self {
        match error {
            sqlx::Error::RowNotFound => Self::new(StatusCode::NOT_FOUND, "book not found"),
            error => {
                eprintln!("Database operation failed: {error}");
                Self::new(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "database operation failed",
                )
            }
        }
    }
}

fn book_id(path: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    path.map(|Path(id)| id)
        .map_err(|error| ApiError(error.status(), error.body_text()))
}

async fn create_book(
    State(db): State<SqlitePool>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<impl IntoResponse, ApiError> {
    let book = BookInput::validate(body)?;
    let book = sqlx::query_as::<_, Book>(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)
         RETURNING id, title, author, year, isbn",
    )
    .bind(book.title)
    .bind(book.author)
    .bind(book.year)
    .bind(book.isbn)
    .fetch_one(&db)
    .await?;
    let location = format!("/books/{}", book.id);
    Ok((
        StatusCode::CREATED,
        [(header::LOCATION, location)],
        Json(book),
    ))
}

async fn list_books(
    State(db): State<SqlitePool>,
    query: Result<Query<BookFilter>, QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let Query(filter) = query.map_err(|error| ApiError(error.status(), error.body_text()))?;
    let books = match filter.author {
        Some(author) => {
            sqlx::query_as::<_, Book>(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
            )
            .bind(author)
            .fetch_all(&db)
            .await?
        }
        None => {
            sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .fetch_all(&db)
                .await?
        }
    };
    Ok(Json(books))
}

async fn get_book(
    State(db): State<SqlitePool>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let book =
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
            .bind(book_id(path)?)
            .fetch_one(&db)
            .await?;
    Ok(Json(book))
}

async fn update_book(
    State(db): State<SqlitePool>,
    path: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = book_id(path)?;
    let book = BookInput::validate(body)?;
    let book = sqlx::query_as::<_, Book>(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?
         RETURNING id, title, author, year, isbn",
    )
    .bind(book.title)
    .bind(book.author)
    .bind(book.year)
    .bind(book.isbn)
    .bind(id)
    .fetch_one(&db)
    .await?;
    Ok(Json(book))
}

async fn delete_book(
    State(db): State<SqlitePool>,
    path: Result<Path<i64>, PathRejection>,
) -> Result<StatusCode, ApiError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?")
        .bind(book_id(path)?)
        .execute(&db)
        .await?;
    if result.rows_affected() == 0 {
        return Err(ApiError::new(StatusCode::NOT_FOUND, "book not found"));
    }
    Ok(StatusCode::NO_CONTENT)
}

async fn health(State(db): State<SqlitePool>) -> Result<Json<serde_json::Value>, ApiError> {
    if let Err(error) = sqlx::query("SELECT 1").execute(&db).await {
        eprintln!("Health check failed: {error}");
        return Err(ApiError::new(
            StatusCode::SERVICE_UNAVAILABLE,
            "database unavailable",
        ));
    }
    Ok(Json(json!({ "status": "ok" })))
}

async fn open_database(options: SqliteConnectOptions) -> Result<SqlitePool, sqlx::Error> {
    let db = SqlitePoolOptions::new()
        .max_connections(1)
        .connect_with(options)
        .await?;
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )
    .execute(&db)
    .await?;
    Ok(db)
}

fn app(db: SqlitePool) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .fallback(|| async { ApiError::new(StatusCode::NOT_FOUND, "route not found") })
        .method_not_allowed_fallback(|| async {
            ApiError::new(StatusCode::METHOD_NOT_ALLOWED, "method not allowed")
        })
        .with_state(db)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database_path = std::env::var_os("BOOKS_DB").unwrap_or_else(|| "books.db".into());
    let db = open_database(
        SqliteConnectOptions::new()
            .filename(database_path)
            .create_if_missing(true),
    )
    .await?;
    let address = std::env::var("BOOKS_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_owned());
    let listener = tokio::net::TcpListener::bind(address).await?;
    eprintln!("Listening on http://{}", listener.local_addr()?);
    axum::serve(listener, app(db)).await?;
    Ok(())
}

#[cfg(test)]
mod tests;

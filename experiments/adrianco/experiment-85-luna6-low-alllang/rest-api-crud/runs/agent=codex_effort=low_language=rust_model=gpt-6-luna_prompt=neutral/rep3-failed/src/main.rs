use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};
use std::{collections::HashMap, net::SocketAddr};

#[derive(Clone)]
struct AppState {
    db: SqlitePool,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow, PartialEq, Eq)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
struct BookFilter {
    author: Option<String>,
}

#[derive(Debug)]
enum ApiError {
    BadRequest(&'static str),
    NotFound,
    Database(sqlx::Error),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            Self::BadRequest(message) => (StatusCode::BAD_REQUEST, message.to_owned()),
            Self::NotFound => (StatusCode::NOT_FOUND, "book not found".to_owned()),
            Self::Database(error) => {
                eprintln!("database error: {error}");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal server error".to_owned())
            }
        };
        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}

impl From<sqlx::Error> for ApiError {
    fn from(error: sqlx::Error) -> Self { Self::Database(error) }
}

fn validate(input: &BookInput) -> Result<(), ApiError> {
    if input.title.trim().is_empty() { return Err(ApiError::BadRequest("title is required")); }
    if input.author.trim().is_empty() { return Err(ApiError::BadRequest("author is required")); }
    Ok(())
}

async fn create_book(State(state): State<AppState>, Json(input): Json<BookInput>) -> Result<(StatusCode, Json<Book>), ApiError> {
    validate(&input)?;
    let result = sqlx::query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .bind(input.title.trim()).bind(input.author.trim()).bind(input.year).bind(input.isbn)
        .execute(&state.db).await?;
    let book = sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(result.last_insert_rowid()).fetch_one(&state.db).await?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(State(state): State<AppState>, Query(filter): Query<BookFilter>) -> Result<Json<Vec<Book>>, ApiError> {
    let books = if let Some(author) = filter.author {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id")
            .bind(author).fetch_all(&state.db).await?
    } else {
        sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books ORDER BY id")
            .fetch_all(&state.db).await?
    };
    Ok(Json(books))
}

async fn get_book(State(state): State<AppState>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    let book = sqlx::query_as::<_, Book>("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
        .bind(id).fetch_optional(&state.db).await?.ok_or(ApiError::NotFound)?;
    Ok(Json(book))
}

async fn update_book(State(state): State<AppState>, Path(id): Path<i64>, Json(input): Json<BookInput>) -> Result<Json<Book>, ApiError> {
    validate(&input)?;
    let result = sqlx::query("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
        .bind(input.title.trim()).bind(input.author.trim()).bind(input.year).bind(input.isbn).bind(id)
        .execute(&state.db).await?;
    if result.rows_affected() == 0 { return Err(ApiError::NotFound); }
    get_book(State(state), Path(id)).await
}

async fn delete_book(State(state): State<AppState>, Path(id): Path<i64>) -> Result<StatusCode, ApiError> {
    let result = sqlx::query("DELETE FROM books WHERE id = ?").bind(id).execute(&state.db).await?;
    if result.rows_affected() == 0 { return Err(ApiError::NotFound); }
    Ok(StatusCode::NO_CONTENT)
}

async fn health() -> Json<HashMap<&'static str, &'static str>> {
    Json(HashMap::from([("status", "ok")]))
}

fn app(state: AppState) -> Router {
    Router::new().route("/health", get(health)).route("/books", post(create_book).get(list_books))
        .route("/books/{id}", get(get_book).put(update_book).delete(delete_book)).with_state(state)
}

async fn database() -> Result<SqlitePool, sqlx::Error> {
    let url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:books.db?mode=rwc".into());
    let pool = SqlitePoolOptions::new().max_connections(5).connect(&url).await?;
    sqlx::query("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)")
        .execute(&pool).await?;
    Ok(pool)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let state = AppState { db: database().await? };
    let address: SocketAddr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".into()).parse()?;
    let listener = tokio::net::TcpListener::bind(address).await?;
    println!("book API listening on {address}");
    axum::serve(listener, app(state)).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::{Request, StatusCode}};
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    async fn test_app() -> Router {
        let db = SqlitePoolOptions::new().max_connections(1).connect("sqlite::memory:").await.unwrap();
        sqlx::query("CREATE TABLE books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)")
            .execute(&db).await.unwrap();
        app(AppState { db })
    }

    async fn send(app: Router, method: &str, uri: &str, body: &str) -> axum::response::Response {
        app.oneshot(Request::builder().method(method).uri(uri).header("content-type", "application/json")
            .body(Body::from(body.to_owned())).unwrap()).await.unwrap()
    }

    #[tokio::test]
    async fn creates_and_reads_book() {
        let app = test_app().await;
        let response = send(app.clone(), "POST", "/books", r#"{"title":"Dune","author":"Frank Herbert","year":1965}"#).await;
        assert_eq!(response.status(), StatusCode::CREATED);
        let book: Book = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(book.title, "Dune");
        assert_eq!(send(app, "GET", &format!("/books/{}", book.id), "").await.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn validates_required_fields_and_filters_by_author() {
        let app = test_app().await;
        assert_eq!(send(app.clone(), "POST", "/books", r#"{"title":" ","author":"A"}"#).await.status(), StatusCode::BAD_REQUEST);
        send(app.clone(), "POST", "/books", r#"{"title":"Dune","author":"Frank Herbert"}"#).await;
        send(app.clone(), "POST", "/books", r#"{"title":"Foundation","author":"Isaac Asimov"}"#).await;
        let response = send(app, "GET", "/books?author=Frank%20Herbert", "").await;
        let books: Vec<Book> = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].author, "Frank Herbert");
    }

    #[tokio::test]
    async fn updates_deletes_and_reports_missing_books() {
        let app = test_app().await;
        let response = send(app.clone(), "POST", "/books", r#"{"title":"Old","author":"Writer"}"#).await;
        let book: Book = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
        assert_eq!(send(app.clone(), "PUT", &format!("/books/{}", book.id), r#"{"title":"New","author":"Writer"}"#).await.status(), StatusCode::OK);
        assert_eq!(send(app.clone(), "DELETE", &format!("/books/{}", book.id), "").await.status(), StatusCode::NO_CONTENT);
        assert_eq!(send(app, "GET", &format!("/books/{}", book.id), "").await.status(), StatusCode::NOT_FOUND);
    }
}

use axum::{
    extract::{
        rejection::{JsonRejection, PathRejection, QueryRejection},
        Path, Query, State,
    },
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::{Arc, Mutex};

type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct BookInput {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

impl BookInput {
    fn validate(mut self) -> Result<Self, ApiError> {
        self.title = self.title.trim().to_owned();
        self.author = self.author.trim().to_owned();
        if self.title.is_empty() || self.author.is_empty() {
            return Err(ApiError(
                StatusCode::BAD_REQUEST,
                "title and author must not be blank".into(),
            ));
        }
        Ok(self)
    }
}

struct ApiError(StatusCode, String);
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(json!({"error": self.1}))).into_response()
    }
}
impl From<rusqlite::Error> for ApiError {
    fn from(error: rusqlite::Error) -> Self {
        eprintln!("database error: {error}");
        Self(
            StatusCode::INTERNAL_SERVER_ERROR,
            "database operation failed".into(),
        )
    }
}
fn internal() -> ApiError {
    ApiError(
        StatusCode::INTERNAL_SERVER_ERROR,
        "internal server error".into(),
    )
}
fn not_found() -> ApiError {
    ApiError(StatusCode::NOT_FOUND, "book not found".into())
}
fn input(value: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    value
        .map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?
        .0
        .validate()
}
fn book_id(value: Result<Path<i64>, PathRejection>) -> Result<i64, ApiError> {
    value
        .map(|v| v.0)
        .map_err(|_| ApiError(StatusCode::BAD_REQUEST, "id must be an integer".into()))
}

// SQLite work runs on the blocking pool rather than blocking async worker threads.
async fn database<T: Send + 'static>(
    db: Db,
    work: impl FnOnce(&Connection) -> Result<T, ApiError> + Send + 'static,
) -> Result<T, ApiError> {
    tokio::task::spawn_blocking(move || {
        let connection = db.lock().map_err(|_| internal())?;
        work(&connection)
    })
    .await
    .map_err(|_| internal())?
}

pub fn app(connection: Connection) -> Result<Router, rusqlite::Error> {
    connection.busy_timeout(std::time::Duration::from_secs(5))?;
    connection.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL CHECK(length(trim(title)) > 0),
        author TEXT NOT NULL CHECK(length(trim(author)) > 0),
        year INTEGER,
        isbn TEXT
    );",
    )?;
    Ok(Router::new()
        .route("/health", get(|| async { Json(json!({"status": "ok"})) }))
        .route("/books", get(list).post(create))
        .route("/books/{id}", get(fetch).put(update).delete(delete))
        .fallback(|| async { ApiError(StatusCode::NOT_FOUND, "route not found".into()) })
        .method_not_allowed_fallback(|| async {
            ApiError(StatusCode::METHOD_NOT_ALLOWED, "method not allowed".into())
        })
        .with_state(Arc::new(Mutex::new(connection))))
}
fn row_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
fn select(connection: &Connection, id: i64) -> Result<Book, ApiError> {
    connection
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
            [id],
            row_book,
        )
        .optional()?
        .ok_or_else(not_found)
}
async fn create(
    State(db): State<Db>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Response, ApiError> {
    let book = input(body)?;
    let result = database(db, move |c| {
        c.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            params![book.title, book.author, book.year, book.isbn],
        )?;
        select(c, c.last_insert_rowid())
    })
    .await?;
    Ok((
        StatusCode::CREATED,
        [(header::LOCATION, format!("/books/{}", result.id))],
        Json(result),
    )
        .into_response())
}
#[derive(Deserialize)]
struct Filter {
    author: Option<String>,
}
async fn list(
    State(db): State<Db>,
    filter: Result<Query<Filter>, QueryRejection>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let filter = filter
        .map_err(|e| ApiError(StatusCode::BAD_REQUEST, e.body_text()))?
        .0;
    database(db, move |c| {
        let mut statement = c.prepare("SELECT id, title, author, year, isbn FROM books WHERE (?1 IS NULL OR author = ?1) ORDER BY id")?;
        let books = statement.query_map([filter.author], row_book)?.collect::<Result<Vec<_>, _>>()?;
        Ok(Json(books))
    }).await
}
async fn fetch(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = book_id(id)?;
    database(db, move |c| select(c, id).map(Json)).await
}
async fn update(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
    body: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let id = book_id(id)?;
    let book = input(body)?;
    database(db, move |c| {
        let count = c.execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![book.title, book.author, book.year, book.isbn, id],
        )?;
        if count == 0 {
            return Err(not_found());
        }
        select(c, id).map(Json)
    })
    .await
}
async fn delete(
    State(db): State<Db>,
    id: Result<Path<i64>, PathRejection>,
) -> Result<Json<serde_json::Value>, ApiError> {
    let id = book_id(id)?;
    database(db, move |c| {
        if c.execute("DELETE FROM books WHERE id = ?1", [id])? == 0 {
            return Err(not_found());
        }
        Ok(Json(json!({"deleted": id})))
    })
    .await
}

#[cfg(test)]
mod tests;

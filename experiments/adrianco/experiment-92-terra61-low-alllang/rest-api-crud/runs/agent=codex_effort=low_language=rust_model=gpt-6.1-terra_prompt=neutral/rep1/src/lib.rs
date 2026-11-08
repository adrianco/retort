use axum::{
    extract::{rejection::JsonRejection, Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct AppState(Arc<Mutex<Connection>>);

impl AppState {
    pub fn new(connection: Connection) -> rusqlite::Result<Self> {
        connection.execute_batch("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER NOT NULL, isbn TEXT NOT NULL);")?;
        Ok(Self(Arc::new(Mutex::new(connection))))
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: i64,
    pub isbn: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    pub year: i64,
    pub isbn: String,
}

#[derive(Deserialize)]
struct Filters {
    author: Option<String>,
}

#[derive(Serialize)]
struct ErrorBody {
    error: String,
}

struct ApiError(StatusCode, String);
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(ErrorBody { error: self.1 })).into_response()
    }
}
impl From<rusqlite::Error> for ApiError {
    fn from(_: rusqlite::Error) -> Self {
        Self(StatusCode::INTERNAL_SERVER_ERROR, "Database error".into())
    }
}
fn internal() -> ApiError {
    ApiError(StatusCode::INTERNAL_SERVER_ERROR, "Database error".into())
}
fn not_found() -> ApiError {
    ApiError(StatusCode::NOT_FOUND, "Book not found".into())
}
fn validate(input: Result<Json<BookInput>, JsonRejection>) -> Result<BookInput, ApiError> {
    let Json(input) = input.map_err(|e| {
        ApiError(
            StatusCode::BAD_REQUEST,
            format!("Invalid request body: {}", e.body_text()),
        )
    })?;
    if input.title.trim().is_empty() || input.author.trim().is_empty() {
        return Err(ApiError(
            StatusCode::BAD_REQUEST,
            "Title and author are required".into(),
        ));
    }
    Ok(input)
}
fn read_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}
fn find_book(db: &Connection, id: i64) -> Result<Book, ApiError> {
    db.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        read_book,
    )
    .optional()?
    .ok_or_else(not_found)
}

pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list).post(create))
        .route("/books/{id}", get(get_book).put(update).delete(delete))
        .with_state(state)
}
async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({"status":"ok"}))
}
async fn create(
    State(state): State<AppState>,
    input: Result<Json<BookInput>, JsonRejection>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let input = validate(input)?;
    let db = state.0.lock().map_err(|_| internal())?;
    db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![input.title, input.author, input.year, input.isbn],
    )?;
    Ok((
        StatusCode::CREATED,
        Json(find_book(&db, db.last_insert_rowid())?),
    ))
}
async fn list(
    State(state): State<AppState>,
    Query(filters): Query<Filters>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let db = state.0.lock().map_err(|_| internal())?;
    let mut statement = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE (?1 IS NULL OR author = ?1) ORDER BY id")?;
    let books = statement
        .query_map([filters.author], read_book)?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    Ok(Json(books))
}
async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let db = state.0.lock().map_err(|_| internal())?;
    Ok(Json(find_book(&db, id)?))
}
async fn update(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    input: Result<Json<BookInput>, JsonRejection>,
) -> Result<Json<Book>, ApiError> {
    let input = validate(input)?;
    let db = state.0.lock().map_err(|_| internal())?;
    let count = db.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![input.title, input.author, input.year, input.isbn, id],
    )?;
    if count == 0 {
        return Err(not_found());
    }
    Ok(Json(find_book(&db, id)?))
}
async fn delete(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<serde_json::Value>, ApiError> {
    let db = state.0.lock().map_err(|_| internal())?;
    if db.execute("DELETE FROM books WHERE id = ?1", [id])? == 0 {
        return Err(not_found());
    }
    Ok(Json(serde_json::json!({"deleted": true})))
}

//! Book API: REST endpoints for managing a book collection, backed by SQLite.

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json, Response},
    routing::get,
    Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};

/// A book in the collection.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub isbn: Option<String>,
}

/// Body for `POST /books`. `title` and `author` are required; `year` and `isbn` are optional.
#[derive(Debug, Deserialize)]
pub struct CreateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Body for `PUT /books/{id}`. Partial update: only fields present in the
/// request overwrite the stored values; omitted fields keep their current value.
/// When `title`/`author` are present they must be non-empty.
#[derive(Debug, Deserialize)]
pub struct UpdateBookRequest {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Query parameters for `GET /books`.
#[derive(Debug, Deserialize)]
pub struct ListBooksQuery {
    pub author: Option<String>,
}

/// Application state shared by all handlers.
#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
}

/// Errors mapped to JSON responses with appropriate status codes.
#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),
    NotFound(String),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m.clone()),
            ApiError::NotFound(m) => (StatusCode::NOT_FOUND, m.clone()),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m.clone()),
        };
        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}

/// Validates that `title` and `author` are present and non-empty (after trimming).
/// Returns a human-readable error message describing every problem found.
pub fn validate_required(title: Option<&str>, author: Option<&str>) -> Result<(), String> {
    let mut errors = Vec::new();
    match title {
        None => errors.push("title is required"),
        Some(t) if t.trim().is_empty() => errors.push("title must not be empty"),
        Some(_) => {}
    }
    match author {
        None => errors.push("author is required"),
        Some(a) if a.trim().is_empty() => errors.push("author must not be empty"),
        Some(_) => {}
    }
    match errors.is_empty() {
        true => Ok(()),
        false => Err(errors.join("; ")),
    }
}

/// Opens (or creates) the SQLite database and ensures the schema exists.
pub fn init_db(path: &str) -> Result<Connection, rusqlite::Error> {
    let conn = Connection::open(path)?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )?;
    Ok(conn)
}

fn map_row(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

fn fetch_book(db: &Connection, id: i64) -> Result<Option<Book>, rusqlite::Error> {
    let mut stmt = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query_map(params![id], map_row)?;
    match rows.next() {
        Some(Ok(row)) => Ok(Some(row)),
        Some(Err(e)) => Err(e),
        None => Ok(None),
    }
}

/// `GET /` — service descriptor; also serves as the readiness probe target.
pub async fn about() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "service": "book-api",
        "status": "ok",
        "health": "/health",
        "endpoints": ["/books", "/books/{id}"]
    }))
}

/// `GET /health` — liveness probe.
pub async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

/// `POST /books` — create a book. Returns 201 with the created book.
pub async fn create_book(
    State(state): State<AppState>,
    Json(req): Json<CreateBookRequest>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let title = req.title.as_deref().map(str::trim).filter(|t| !t.is_empty());
    let author = req.author.as_deref().map(str::trim).filter(|t| !t.is_empty());
    validate_required(title, author).map_err(ApiError::BadRequest)?;
    let title = title.unwrap().to_string();
    let author = author.unwrap().to_string();

    let db = state.db.lock().unwrap();
    db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, req.year, req.isbn],
    )
    .map_err(|e| ApiError::Internal(e.to_string()))?;
    let id = db.last_insert_rowid();

    let book = fetch_book(&db, id)
        .map_err(|e| ApiError::Internal(e.to_string()))?
        .expect("book was just inserted");
    Ok((StatusCode::CREATED, Json(book)))
}

/// `GET /books` — list all books, optionally filtered with `?author=`.
pub async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListBooksQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let db = state.db.lock().unwrap();
    let author = query
        .author
        .as_deref()
        .map(str::trim)
        .filter(|a| !a.is_empty());

    let books = match author {
        Some(author) => {
            let mut stmt = db
                .prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id")
                .map_err(|e| ApiError::Internal(e.to_string()))?;
            let rows = stmt
                .query_map(params![author], map_row)
                .map_err(|e| ApiError::Internal(e.to_string()))?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|e| ApiError::Internal(e.to_string()))?
        }
        None => {
            let mut stmt = db
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .map_err(|e| ApiError::Internal(e.to_string()))?;
            let rows = stmt
                .query_map([], map_row)
                .map_err(|e| ApiError::Internal(e.to_string()))?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|e| ApiError::Internal(e.to_string()))?
        }
    };
    Ok(Json(books))
}

/// `GET /books/{id}` — fetch one book, or 404.
pub async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let db = state.db.lock().unwrap();
    fetch_book(&db, id)
        .map_err(|e| ApiError::Internal(e.to_string()))?
        .map(Json)
        .ok_or_else(|| ApiError::NotFound(format!("book {id} not found")))
}

/// `PUT /books/{id}` — update a book (partial update). Returns 200 with the updated book.
pub async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(req): Json<UpdateBookRequest>,
) -> Result<Json<Book>, ApiError> {
    let db = state.db.lock().unwrap();
    let existing = fetch_book(&db, id)
        .map_err(|e| ApiError::Internal(e.to_string()))?
        .ok_or_else(|| ApiError::NotFound(format!("book {id} not found")))?;

    // Validate provided required fields before touching the database.
    let title = req.title.as_deref().map(str::trim).filter(|t| !t.is_empty());
    let author = req.author.as_deref().map(str::trim).filter(|t| !t.is_empty());
    if req.title.is_some() {
        validate_required(title, Some("placeholder")).map_err(ApiError::BadRequest)?;
    }
    if req.author.is_some() {
        validate_required(Some("placeholder"), author).map_err(ApiError::BadRequest)?;
    }

    let new_title = title.map(str::to_string).unwrap_or(existing.title);
    let new_author = author.map(str::to_string).unwrap_or(existing.author);
    let new_year = req.year.or(existing.year);
    let new_isbn = req.isbn.clone().or(existing.isbn.clone());

    db.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params![new_title, new_author, new_year, new_isbn, id],
    )
    .map_err(|e| ApiError::Internal(e.to_string()))?;

    fetch_book(&db, id)
        .map_err(|e| ApiError::Internal(e.to_string()))?
        .map(Json)
        .ok_or_else(|| ApiError::Internal(format!("book {id} disappeared during update")))
}

/// `DELETE /books/{id}` — delete a book. Returns 204 on success, 404 if missing.
pub async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let db = state.db.lock().unwrap();
    let existing = fetch_book(&db, id)
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    if existing.is_none() {
        return Err(ApiError::NotFound(format!("book {id} not found")));
    }
    db.execute("DELETE FROM books WHERE id = ?1", params![id])
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    Ok(StatusCode::NO_CONTENT)
}

/// Builds the application router.
pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/", get(about))
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_requires_title() {
        assert_eq!(
            validate_required(None, Some("Jane Austen")).unwrap_err(),
            "title is required"
        );
    }

    #[test]
    fn validate_requires_author() {
        assert_eq!(
            validate_required(Some("Pride and Prejudice"), None).unwrap_err(),
            "author is required"
        );
    }

    #[test]
    fn validate_rejects_blank_values() {
        assert_eq!(
            validate_required(Some("   "), Some("")).unwrap_err(),
            "title must not be empty; author must not be empty"
        );
    }

    #[test]
    fn validate_accepts_good_values() {
        assert!(validate_required(Some("Dune"), Some("Frank Herbert")).is_ok());
    }

    #[test]
    fn init_db_creates_schema_and_roundtrips() {
        let conn = init_db(":memory:").unwrap();
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            params!["Neuromancer", "William Gibson", 1984, "0-441-56959-7"],
        )
        .unwrap();
        let book = fetch_book(&conn, 1).unwrap().expect("row exists");
        assert_eq!(book.title, "Neuromancer");
        assert_eq!(book.year, Some(1984));
        assert_eq!(book.isbn, Some("0-441-56959-7".to_string()));
    }
}

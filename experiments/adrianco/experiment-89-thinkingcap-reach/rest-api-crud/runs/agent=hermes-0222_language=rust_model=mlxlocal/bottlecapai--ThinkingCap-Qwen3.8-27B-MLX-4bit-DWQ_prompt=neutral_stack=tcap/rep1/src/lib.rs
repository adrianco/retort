//! Book API: a small REST service for managing a book collection.
//!
//! Endpoints:
//!   GET    /health      — health check
//!   POST   /books       — create a book (title, author, year, isbn)
//!   GET    /books       — list books (optional `?author=` filter)
//!   GET    /books/{id}  — fetch one book
//!   PUT    /books/{id}  — update a book
//!   DELETE /books/{id}  — delete a book

use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json, Response},
    routing::{get, post},
    Router,
};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::json;

/// Shared application state. The SQLite connection is guarded by a mutex
/// because `rusqlite::Connection` is synchronous and not `Sync`; the `Arc`
/// makes `AppState` cheaply `Clone` (required by axum's `State`).
#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Mutex<Connection>>,
}

/// A book as stored and returned by the API.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

/// Payload for POST /books and PUT /books/{id}.
///
/// `title` and `author` are required (validated in [`BookInput::validate`]);
/// `year` and `isbn` are optional.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

impl BookInput {
    /// Validates the input, returning trimmed, non-empty `title`/`author`
    /// and optional `year`/`isbn`.
    pub fn validate(&self) -> Result<(String, String, Option<i32>, Option<String>), String> {
        let title = self
            .title
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(str::to_string)
            .ok_or_else(|| "title is required".to_string())?;
        let author = self
            .author
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(str::to_string)
            .ok_or_else(|| "author is required".to_string())?;
        if let Some(year) = self.year {
            if !(1000..=2100).contains(&year) {
                return Err(format!("year must be between 1000 and 2100, got {year}"));
            }
        }
        let isbn = self
            .isbn
            .as_deref()
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(str::to_string);
        Ok((title, author, self.year, isbn))
    }
}

/// Query parameters for GET /books.
#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

/// Error returned to API clients.
#[derive(Debug)]
pub struct ApiError {
    status: StatusCode,
    message: String,
}

impl ApiError {
    fn new(status: StatusCode, message: impl Into<String>) -> Self {
        Self {
            status,
            message: message.into(),
        }
    }

    fn bad_request(message: impl Into<String>) -> Self {
        Self::new(StatusCode::BAD_REQUEST, message)
    }

    fn not_found(message: impl Into<String>) -> Self {
        Self::new(StatusCode::NOT_FOUND, message)
    }

    fn internal(message: impl Into<String>) -> Self {
        Self::new(StatusCode::INTERNAL_SERVER_ERROR, message)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (
            self.status,
            Json(json!({ "error": self.message })),
        )
            .into_response()
    }
}

/// Creates the schema on an existing connection.
pub fn create_tables(conn: &mut Connection) -> Result<(), rusqlite::Error> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )
}

/// Opens (or creates) a SQLite database at `path` with the schema in place.
pub fn open_db(path: &str) -> Result<Connection, rusqlite::Error> {
    let mut conn = Connection::open(path)?;
    create_tables(&mut conn)?;
    Ok(conn)
}

fn book_from_row(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

const BOOK_COLUMNS: &str = "id, title, author, year, isbn";

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

async fn root() -> Json<serde_json::Value> {
    Json(json!({
        "service": "book-api",
        "endpoints": ["/health", "/books", "/books/{id}"]
    }))
}

async fn create_book(
    State(state): State<AppState>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author, year, isbn) =
        input.validate().map_err(ApiError::bad_request)?;

    let conn = state.db.lock().expect("db lock poisoned");
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params![title, author, year, isbn],
    )
    .map_err(|e| ApiError::internal(e.to_string()))?;

    let id = conn.last_insert_rowid();
    Ok((
        StatusCode::CREATED,
        Json(Book {
            id,
            title,
            author,
            year,
            isbn,
        }),
    ))
}

async fn list_books(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = state.db.lock().expect("db lock poisoned");
    let author = query
        .author
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty());

    let sql = match author {
        Some(_) => format!(
            "SELECT {BOOK_COLUMNS} FROM books WHERE lower(author) = lower(?1) ORDER BY id"
        ),
        None => format!("SELECT {BOOK_COLUMNS} FROM books ORDER BY id"),
    };

    let mut stmt = conn.prepare(&sql).map_err(|e| ApiError::internal(e.to_string()))?;
    let rows = match author {
        Some(a) => stmt
            .query_map(params![a], book_from_row)
            .map_err(|e| ApiError::internal(e.to_string()))?,
        None => stmt
            .query_map([], book_from_row)
            .map_err(|e| ApiError::internal(e.to_string()))?,
    };
    let books = rows
        .collect::<Result<Vec<Book>, _>>()
        .map_err(|e| ApiError::internal(e.to_string()))?;
    Ok(Json(books))
}

async fn get_book(State(state): State<AppState>, Path(id): Path<i64>) -> Result<Json<Book>, ApiError> {
    let conn = state.db.lock().expect("db lock poisoned");
    conn.query_row(
        &format!("SELECT {BOOK_COLUMNS} FROM books WHERE id = ?1"),
        params![id],
        book_from_row,
    )
    .map(Json)
    .map_err(|e| match e {
        rusqlite::Error::QueryReturnedNoRows => {
            ApiError::not_found(format!("book {id} not found"))
        }
        other => ApiError::internal(other.to_string()),
    })
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author, year, isbn) =
        input.validate().map_err(ApiError::bad_request)?;

    let conn = state.db.lock().expect("db lock poisoned");
    let affected = conn
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            params![title, author, year, isbn, id],
        )
        .map_err(|e| ApiError::internal(e.to_string()))?;
    if affected == 0 {
        return Err(ApiError::not_found(format!("book {id} not found")));
    }

    conn.query_row(
        &format!("SELECT {BOOK_COLUMNS} FROM books WHERE id = ?1"),
        params![id],
        book_from_row,
    )
    .map(Json)
    .map_err(|e| ApiError::internal(e.to_string()))
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = state.db.lock().expect("db lock poisoned");
    let affected = conn
        .execute("DELETE FROM books WHERE id = ?1", params![id])
        .map_err(|e| ApiError::internal(e.to_string()))?;
    if affected == 0 {
        return Err(ApiError::not_found(format!("book {id} not found")));
    }
    Ok(StatusCode::NO_CONTENT)
}

/// Builds the application router.
pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/", get(root))
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/{id}",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_accepts_full_input() {
        let input = BookInput {
            title: Some("  The Hobbit  ".into()),
            author: Some("J.R.R. Tolkien".into()),
            year: Some(1937),
            isbn: Some("978-0-261-10240-4".into()),
        };
        let (title, author, year, isbn) = input.validate().unwrap();
        assert_eq!(title, "The Hobbit");
        assert_eq!(author, "J.R.R. Tolkien");
        assert_eq!(year, Some(1937));
        assert_eq!(isbn.as_deref(), Some("978-0-261-10240-4"));
    }

    #[test]
    fn validate_rejects_missing_title() {
        let input = BookInput {
            title: None,
            author: Some("Someone".into()),
            year: None,
            isbn: None,
        };
        assert!(input.validate().is_err());
    }

    #[test]
    fn validate_rejects_blank_author() {
        let input = BookInput {
            title: Some("A Book".into()),
            author: Some("   ".into()),
            year: None,
            isbn: None,
        };
        assert!(input.validate().is_err());
    }

    #[test]
    fn validate_rejects_out_of_range_year() {
        let input = BookInput {
            title: Some("A Book".into()),
            author: Some("Someone".into()),
            year: Some(3000),
            isbn: None,
        };
        assert!(input.validate().is_err());
    }

    #[test]
    fn validate_treats_blank_isbn_as_absent() {
        let input = BookInput {
            title: Some("A Book".into()),
            author: Some("Someone".into()),
            year: None,
            isbn: Some("  ".into()),
        };
        let (_, _, _, isbn) = input.validate().unwrap();
        assert!(isbn.is_none());
    }
}

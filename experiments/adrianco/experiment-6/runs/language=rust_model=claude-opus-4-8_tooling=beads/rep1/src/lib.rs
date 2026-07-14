use std::sync::{Arc, Mutex};

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::json;

/// Shared application state: a single SQLite connection guarded by a mutex.
///
/// rusqlite is synchronous, so we serialize access behind a `Mutex`. For this
/// service's scope that is more than sufficient and keeps the code simple.
pub type Db = Arc<Mutex<Connection>>;

#[derive(Debug, Serialize)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Payload for creating or replacing a book.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ListFilter {
    pub author: Option<String>,
}

/// An API error that serializes to a JSON body with an HTTP status code.
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
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.status, Json(json!({ "error": self.message }))).into_response()
    }
}

/// Initialize the schema on a fresh connection.
pub fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
        [],
    )?;
    Ok(())
}

/// Open a connection at `path` ("`:memory:`" for an in-memory DB) and ensure
/// the schema exists.
pub fn open_db(path: &str) -> rusqlite::Result<Db> {
    let conn = Connection::open(path)?;
    init_schema(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

/// Build the application router around a database handle.
pub fn app(db: Db) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", get(list_books).post(create_book))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(db)
}

async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

fn validate(input: &BookInput) -> Result<(String, String), ApiError> {
    let title = input.title.as_deref().unwrap_or("").trim().to_string();
    let author = input.author.as_deref().unwrap_or("").trim().to_string();
    if title.is_empty() {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            "title is required",
        ));
    }
    if author.is_empty() {
        return Err(ApiError::new(
            StatusCode::BAD_REQUEST,
            "author is required",
        ));
    }
    Ok((title, author))
}

fn row_to_book(row: &rusqlite::Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get(0)?,
        title: row.get(1)?,
        author: row.get(2)?,
        year: row.get(3)?,
        isbn: row.get(4)?,
    })
}

async fn create_book(
    State(db): State<Db>,
    Json(input): Json<BookInput>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![title, author, input.year, input.isbn],
    )
    .map_err(internal)?;
    let id = conn.last_insert_rowid();
    let book = fetch_one(&conn, id)?;
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books(
    State(db): State<Db>,
    Query(filter): Query<ListFilter>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let conn = db.lock().unwrap();
    let books = match filter.author {
        Some(author) => {
            let mut stmt = conn
                .prepare(
                    "SELECT id, title, author, year, isbn FROM books \
                     WHERE author = ?1 ORDER BY id",
                )
                .map_err(internal)?;
            let rows = stmt
                .query_map([author], row_to_book)
                .map_err(internal)?;
            rows.collect::<rusqlite::Result<Vec<_>>>().map_err(internal)?
        }
        None => {
            let mut stmt = conn
                .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
                .map_err(internal)?;
            let rows = stmt.query_map([], row_to_book).map_err(internal)?;
            rows.collect::<rusqlite::Result<Vec<_>>>().map_err(internal)?
        }
    };
    Ok(Json(books))
}

async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let conn = db.lock().unwrap();
    let book = fetch_one(&conn, id)?;
    Ok(Json(book))
}

async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(input): Json<BookInput>,
) -> Result<Json<Book>, ApiError> {
    let (title, author) = validate(&input)?;
    let conn = db.lock().unwrap();
    let affected = conn
        .execute(
            "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
            rusqlite::params![title, author, input.year, input.isbn, id],
        )
        .map_err(internal)?;
    if affected == 0 {
        return Err(not_found(id));
    }
    let book = fetch_one(&conn, id)?;
    Ok(Json(book))
}

async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let conn = db.lock().unwrap();
    let affected = conn
        .execute("DELETE FROM books WHERE id = ?1", [id])
        .map_err(internal)?;
    if affected == 0 {
        return Err(not_found(id));
    }
    Ok(StatusCode::NO_CONTENT)
}

fn fetch_one(conn: &Connection, id: i64) -> Result<Book, ApiError> {
    conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
        [id],
        row_to_book,
    )
    .map_err(|e| match e {
        rusqlite::Error::QueryReturnedNoRows => not_found(id),
        other => internal(other),
    })
}

fn not_found(id: i64) -> ApiError {
    ApiError::new(StatusCode::NOT_FOUND, format!("book {id} not found"))
}

fn internal(e: rusqlite::Error) -> ApiError {
    ApiError::new(StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
}
